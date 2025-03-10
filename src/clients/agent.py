import asyncpg
import json
import openai
import numpy as np
from langgraph.graph import StateGraph
from langchain.tools import Tool
from langchain_openai import OpenAI
from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings import OpenAIEmbeddings
from clients.alchemy import AlchemyClient
from clients.hyperliquid_v1 import HyperliquidClient
from config.settings import settings

class TradingAgent:
    """Langraph-powered trading agent for Hyperliquid with memory and autonomous execution."""

    def __init__(self):
        self.alchemy = AlchemyClient()
        self.hyperliquid = HyperliquidClient()
        self.db_url = settings.DATABASE_URL
        self.openai_api_key = settings.OPENAI_API_KEY

        # Setup LangChain memory with pgvector
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
        self.vectorstore = PGVector(
            connection=self.db_url,
            embeddings=self.embeddings,
            collection_name="risk_trade_memory",
            use_jsonb=True,
        )

        # Initialize Langraph workflow
        self.graph = self._setup_graph()

    def _setup_graph(self):
        """Set up the Langraph workflow for trading decisions."""
        graph = StateGraph({})

        @graph.step()
        async def fetch_assets(state):
            """Fetch tradable assets with market cap over $20M."""
            tradable_assets = await self.get_tokens_over_market_cap(20_000_000)
            state["tradable_assets"] = tradable_assets
            return state

        @graph.step()
        async def assess_risk(state):
            """Perform risk assessment using OpenAI and stored embeddings."""
            tradable_assets = state["tradable_assets"]
            risk_assessment = await self.assess_risk(tradable_assets)
            state["risk_assessment"] = risk_assessment
            return state

        @graph.step()
        async def decide_trade(state):
            """Decide whether to execute trades based on risk assessment."""
            risk_assessment = state["risk_assessment"]
            trades = {token: score for token, score in risk_assessment.items() if score < 40}
            state["trades"] = trades
            return state

        @graph.step()
        async def execute_trade(state):
            """Execute trades based on risk assessment."""
            trades = state["trades"]
            executed_trades = await self.execute_trades(trades, budget=10000)
            state["executed_trades"] = executed_trades
            return state

        @graph.step()
        async def store_trade_memory(state):
            """Store trade decisions and risk assessments in pgvector for future reference."""
            await self.store_embeddings(state["risk_assessment"], state["executed_trades"])
            return state

        # Define workflow connections
        graph.add_edge(fetch_assets, assess_risk)
        graph.add_edge(assess_risk, decide_trade)
        graph.add_edge(decide_trade, execute_trade)
        graph.add_edge(execute_trade, store_trade_memory)

        return graph

    async def get_tokens_over_market_cap(self, min_market_cap: float):
        """Fetch tradable assets over a given market cap."""
        all_tokens = ["ETH", "BTC", "USDC", "MATIC", "SOL", "ARB"]
        tradable_tokens = {}

        for token in all_tokens:
            metadata = await self.alchemy.get_token_metadata(token)
            market_cap = float(metadata["result"].get("marketCap", 0))

            if market_cap >= min_market_cap:
                tradable_tokens[token] = market_cap

        return tradable_tokens

    async def assess_risk(self, tokens):
        """Assess risk using OpenAI and retrieve past risk embeddings from pgvector."""
        conn = await asyncpg.connect(self.db_url)

        past_risks = await conn.fetch("SELECT token, risk_score, embedding FROM risk_assessments WHERE token = ANY($1)", list(tokens.keys()))
        risk_memory = {record["token"]: (record["risk_score"], np.array(record["embedding"])) for record in past_risks}

        openai.api_key = self.openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Analyze risk scores based on past embeddings and market trends."},
                {"role": "user", "content": f"Past risk data: {risk_memory}"},
                {"role": "user", "content": f"Assess risk for these tokens: {tokens}"}
            ]
        )

        risk_data = json.loads(response["choices"][0]["message"]["content"])
        risk_assessment = {token["name"]: token["risk_score"] for token in risk_data["tokens"]}

        await conn.close()
        return risk_assessment

    async def execute_trades(self, tokens_with_risk, budget):
        """Execute trades based on risk assessment."""
        executed_trades = []
        for token, risk_score in tokens_with_risk.items():
            size = budget * 0.1  # Allocate 10% per trade
            price = 100  # Placeholder price
            result = self.hyperliquid.place_order(token, is_buy=True, price=price, size=size)
            executed_trades.append({"token": token, "risk_score": risk_score, "result": result})

        return executed_trades

    async def store_embeddings(self, risk_assessment, trades):
        """Store risk assessment & trade history embeddings in pgvector."""
        conn = await asyncpg.connect(self.db_url)

        async with conn.transaction():
            for token, risk_score in risk_assessment.items():
                embedding = self.embeddings.embed_query(json.dumps({"token": token, "risk_score": risk_score}))
                await conn.execute(
                    "INSERT INTO risk_assessments (token, risk_score, embedding) VALUES ($1, $2, $3) ON CONFLICT (token) DO UPDATE SET risk_score = EXCLUDED.risk_score, embedding = EXCLUDED.embedding",
                    token, risk_score, embedding
                )

                # Store in LangChain Memory (pgvector)
                self.vectorstore.add_texts(
                    texts=[f"Risk assessment for {token}: {risk_score}"],
                    metadatas=[{"token": token, "risk_score": risk_score}]
                )

        await conn.close()

    async def run_graph(self):
        """Execute the entire Langraph trading workflow."""
        return await self.graph.run()

