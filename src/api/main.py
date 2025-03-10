from fastapi import FastAPI, HTTPException
from clients.agent import TradingAgent
from clients.hyperliquid import HyperliquidClient

app = FastAPI(title="LangChain Trading Agent API with Memory")

agent = TradingAgent()
hyperliquid_client = HyperliquidClient()


@app.get("/")
async def root():
    return {"message": "LangChain Trading Agent API with Persistent Memory Running!"}


@app.get("/coins/")
async def get_all_coins():
    """Fetch all tradable spot tokens from Hyperliquid."""
    return await hyperliquid_client.get_all_coins()


@app.get("/mids/")
async def get_mids():
    """Fetch mid-market prices for all tradable assets."""
    return await hyperliquid_client.get_mids()


@app.get("/assets/")
async def get_assets(min_market_cap: float = 20_000_000):
    return {"tradable_assets": await agent.get_tokens_over_market_cap(min_market_cap)}


@app.post("/assess-risk/")
async def assess_risk():
    tradable_tokens = await agent.get_tokens_over_market_cap(30_000_000)
    return {"risk_assessment": await agent.assess_risk(tradable_tokens)}


@app.post("/trade/")
async def trade(budget: float = 10000):
    tradable_tokens = await agent.get_tokens_over_market_cap(30_000_000)
    risk_scores = await agent.assess_risk(tradable_tokens)
    return {"executed_trades": await agent.execute_trades(risk_scores, budget)}


@app.post("/run-agent/")
async def run_agent(query: str):
    return {"response": await agent.run_agent(query)}


@app.get("/memory/")
async def get_memory():
    """Retrieve trade history and risk assessments from memory."""
    docs = agent.vectorstore.as_retriever().get_relevant_documents("trade")
    return {"memory": [doc.page_content for doc in docs]}


@app.post("/place-order/")
async def place_order(asset: str, is_buy: bool, price: float, size: float):
    """Place a spot order."""
    return hyperliquid_client.place_order(asset, is_buy, price, size)
