import asyncpg
import json
import openai
import numpy as np
from langchain.agents import initialize_agent, AgentType
from langchain.memory import VectorStoreRetrieverMemory
from langchain.tools import Tool
from langchain_openai import OpenAI
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from clients.alchemy import AlchemyClient
from clients.hyperliquid_v1 import HyperliquidClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

TOKEN_CONTRACTS = {
    "ETH": "0xC02aaA39b223FE8D0A0E5C4F27eAD9083C756Cc2",  # WETH (wrapped ETH)
    "BTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC (wrapped BTC)
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "MATIC": "0x7D1Afa7B718fb893dB30A3aBc0Cfc608aACfeBB0",
}


class TradingAgent:
    """AI-powered trading agent using LangChain with persistent memory (pgvector)."""

    def __init__(self):
        self.alchemy = AlchemyClient()
        self.hyperliquid = HyperliquidClient()
        self.db_url = settings.DATABASE_URL
        self.openai_api_key = settings.OPENAI_API_KEY

        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

        self.vectorstore = PGVector(
            connection=self.db_url,
            embeddings=self.embeddings,
            collection_name="risk_trade_memory",
            use_jsonb=True,
        )

        self.memory = VectorStoreRetrieverMemory(
            retriever=self.vectorstore.as_retriever()
        )

        # Define LangChain tools
        self.tools = [
            Tool(
                name="Risk Assessment",
                func=self.assess_risk,
                description="Analyzes cryptocurrency risk and returns a score (0-100).",
            ),
            Tool(
                name="Trade Execution",
                func=self.execute_trades,
                description="Executes trades based on risk assessment and budget allocation.",
            ),
        ]

        # Initialize LangChain Agent
        self.llm = OpenAI(openai_api_key=self.openai_api_key)
        self.agent = initialize_agent(
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            tools=self.tools,
            llm=self.llm,
            memory=self.memory,
            verbose=True,
        )

    async def assess_risk(self, tokens):
        """Assess risk and store embeddings in pgvector for future retrieval."""
        conn = await asyncpg.connect(self.db_url)

        past_risks = await conn.fetch(
            "SELECT token, risk_score, embedding FROM risk_assessments WHERE token = ANY($1)",
            list(tokens.keys()),
        )
        risk_memory = {
            record["token"]: (record["risk_score"], np.array(record["embedding"]))
            for record in past_risks
        }

        openai.api_key = self.openai_api_key

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Analyze risk scores based on past embeddings and market trends.",
                },
                {"role": "user", "content": f"Past risk data: {risk_memory}"},
                {"role": "user", "content": f"Assess risk for these tokens: {tokens}"},
            ],
        )

        risk_data = json.loads(response["choices"][0]["message"]["content"])
        risk_assessment = {
            token["name"]: token["risk_score"] for token in risk_data["tokens"]
        }

        async with conn.transaction():
            for token, risk_score in risk_assessment.items():
                embedding = self.embeddings.embed_query(
                    json.dumps({"token": token, "risk_score": risk_score})
                )
                await conn.execute(
                    """
                    INSERT INTO risk_assessments (token, risk_score, embedding)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (token) DO UPDATE 
                    SET risk_score = EXCLUDED.risk_score, embedding = EXCLUDED.embedding
                    """,
                    token,
                    risk_score,
                    embedding,
                )

                # Store in LangChain Memory (pgvector)
                self.vectorstore.add_texts(
                    texts=[f"Risk assessment for {token}: {risk_score}"],
                    metadatas=[{"token": token, "risk_score": risk_score}],
                )

        await conn.close()
        return risk_assessment

    async def get_tokens_over_market_cap(self, min_market_cap: float):
        """Fetch tradable assets over a given market cap."""
        tradable_tokens = {}

        for token, contract in TOKEN_CONTRACTS.items():
            metadata = await self.alchemy.get_token_metadata(
                contract
            )  # ✅ Use contract address

            # Log the response for debugging
            logger.info(f"Metadata response for {token}: {metadata}")

            if "result" in metadata and "marketCap" in metadata["result"]:
                market_cap = float(metadata["result"]["marketCap"])
            else:
                logger.warning(f"Unexpected metadata format for {token}: {metadata}")
                continue  # Skip this token

            if market_cap >= min_market_cap:
                tradable_tokens[token] = market_cap

        return tradable_tokens

    async def execute_trades(self, tokens_with_risk, budget):
        """Decide and execute trades based on risk assessment and memory retrieval."""
        past_trades = self.vectorstore.as_retriever().get_relevant_documents(
            "past trade"
        )

        executed_trades = []
        for token, risk_score in tokens_with_risk.items():
            if risk_score < 40:  # Low-risk tokens
                size = budget * 0.1  # Allocate 10% per trade
                price = 100  # Placeholder price
                result = self.hyperliquid.place_order(
                    token, is_buy=True, price=price, size=size
                )

                executed_trades.append(
                    {"token": token, "risk_score": risk_score, "result": result}
                )

                # Store trade decision as an embedding
                self.vectorstore.add_texts(
                    texts=[f"Trade executed for {token} at {price} with size {size}"],
                    metadatas=[
                        {
                            "token": token,
                            "risk_score": risk_score,
                            "trade_result": result,
                        }
                    ],
                )

        return executed_trades
