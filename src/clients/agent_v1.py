import asyncpg
import json
import openai
import numpy as np
from pgvector.asyncpg import register_vector
from src.clients.alchemy import AlchemyClient
from clients.hyperliquid_v1 import HyperliquidClient
from src.config.settings import settings

# NAIVE No Agent framework

class TradingAgent:
    """Automated trading agent with memory for risk assessments and trade decisions."""

    def __init__(self):
        self.alchemy = AlchemyClient()
        self.hyperliquid = HyperliquidClient()
        self.db_url = settings.DATABASE_URL
        self.openai_api_key = settings.OPENAI_API_KEY

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
        await register_vector(conn)

        # Retrieve previous risk assessments
        past_risks = await conn.fetch("SELECT token, risk_score, embedding FROM risk_assessments WHERE token = ANY($1)", list(tokens.keys()))
        risk_memory = {record["token"]: (record["risk_score"], np.array(record["embedding"])) for record in past_risks}

        openai.api_key = self.openai_api_key
        function_definitions = [
            {
                "name": "get_risk_assessment",
                "description": "Returns a risk score (0-100) for each crypto token based on volatility, liquidity, and market trends.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tokens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "risk_score": {"type": "integer"}
                                },
                                "required": ["name", "risk_score"]
                            }
                        }
                    },
                    "required": ["tokens"]
                }
            }
        ]

        messages = [{"role": "system", "content": "Analyze risk scores based on past embeddings and market trends."}]
        if risk_memory:
            messages.append({"role": "user", "content": f"Past risk data: {risk_memory}"})
        
        messages.append({"role": "user", "content": f"Assess the risk for these tokens: {tokens}"})

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=messages,
            functions=function_definitions,
            function_call={"name": "get_risk_assessment"}
        )

        risk_data = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])
        risk_assessment = {token["name"]: token["risk_score"] for token in risk_data["tokens"]}

        # Store embeddings for future memory
        async with conn.transaction():
            for token, risk_score in risk_assessment.items():
                embedding = np.random.rand(768).tolist()  # Placeholder, replace with OpenAI embedding
                await conn.execute(
                    "INSERT INTO risk_assessments (token, risk_score, embedding) VALUES ($1, $2, $3) ON CONFLICT (token) DO UPDATE SET risk_score = EXCLUDED.risk_score, embedding = EXCLUDED.embedding",
                    token, risk_score, embedding
                )

        await conn.close()
        return risk_assessment

    async def execute_trades(self, tokens_with_risk, budget):
        """Decide and execute trades based on risk assessment and past decisions."""
        executed_trades = []
        
        for token, risk_score in tokens_with_risk.items():
            if risk_score < 40:  # Low-risk tokens
                size = budget * 0.1  # Allocate 10% of budget per trade
                price = 100  # Placeholder price
                result = self.hyperliquid.place_order(token, is_buy=True, price=price, size=size)
                executed_trades.append({"token": token, "risk_score": risk_score, "result": result})

        return executed_trades

    async def retrieve_trade_history(self):
        """Retrieve past trade decisions and risk assessments from database."""
        conn = await asyncpg.connect(self.db_url)
        records = await conn.fetch("SELECT token, risk_score, embedding FROM risk_assessments")
        await conn.close()

        return [{"token": record["token"], "risk_score": record["risk_score"], "embedding": json.loads(record["embedding"])} for record in records]
