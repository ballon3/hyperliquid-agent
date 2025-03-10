import os
import logging
import json
import time
import math
import threading
import coloredlogs
from fastapi import FastAPI, BackgroundTasks
from swarm import Agent, Swarm
from clients.hyperliquid import HyperliquidClient

# Initialize logging
coloredlogs.install()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Hyperliquid Trading Bot API")

# Initialize Hyperliquid client
hyperliquid = HyperliquidClient(testnet=True)

# Initialize Swarm client
swarm_client = Swarm()

# Track running state
running = False
watchlist = set(["BTC/USDC:USDC", "ETH/USDC:USDC", "SOL/USDC:USDC"])
executed_trades_log = []

# Risk Assessment Agent
risk_assessment_agent = Agent(
    name="Risk-Assessor",
    instructions="Analyze risk scores for given crypto assets. Score from 0-100 (lower is better).",
)

# Trade Execution Agent
trade_execution_agent = Agent(
    name="Trade-Executor",
    instructions="Decide trades based on risk scores. Buy if <40, Sell if >60, Hold otherwise.",
)


import decimal
from decimal import Decimal, ROUND_UP


def execute_trades(trade_decisions):
    """Executes trades while ensuring each order meets Hyperliquid's $10 minimum trade requirement."""
    global executed_trades_log
    executed_trades = []

    for asset, decision in trade_decisions.items():
        if asset not in watchlist:
            logger.info(f"Skipping {asset}: Not in watchlist")
            continue

        if decision not in ["buy", "sell"]:
            logger.info(f"Skipping {asset}: No action needed ({decision})")
            continue

        # Fetch latest price
        try:
            ticker = hyperliquid.exchange.fetch_ticker(asset)
            latest_price = Decimal(
                str(ticker["last"])
            )  # Convert to Decimal for precision
        except Exception as e:
            logger.error(f"Error fetching price for {asset}: {e}")
            continue

        # ✅ Ensure minimum trade value of $10
        min_trade_size = (Decimal("10") / latest_price).quantize(
            Decimal("0.000001"), rounding=ROUND_UP
        )
        logger.info(
            f"Calculated min trade size for {asset}: {min_trade_size} (latest price: {latest_price})"
        )

        # Execute trade
        order = hyperliquid.place_order(
            asset, decision, float(min_trade_size), float(latest_price)
        )
        if order:
            logger.info(
                f"Executed {decision.upper()} order for {min_trade_size} {asset} at {latest_price}"
            )
            executed_trades.append(order)
            executed_trades_log.append(order)
        else:
            logger.error(f"Failed to place order for {asset}")

    return executed_trades


def trading_loop():
    """Main trading loop: fetch market data, assess risk, and execute trades every minute."""
    global running
    while running:
        logger.info("\n---- Running Trading Cycle ----")

        # 1️⃣ Fetch Market Data
        market_data = {asset: hyperliquid.get_market_data(asset) for asset in watchlist}
        logger.info(f"Market Data: {market_data}")

        # 2️⃣ Risk Assessment
        risk_response = swarm_client.run(
            agent=risk_assessment_agent,
            messages=[{"role": "user", "content": f"Analyze risk for {market_data}"}],
        )
        risk_scores = risk_response.messages[-1]["content"]
        logger.info(f"Risk Scores: {risk_scores}")

        # 3️⃣ Trade Execution Decision
        trade_response = swarm_client.run(
            agent=trade_execution_agent,
            messages=[
                {
                    "role": "user",
                    "content": f"Make trade decisions for risk: {risk_scores}",
                }
            ],
        )

        # Ensure response is a dictionary (parse JSON if necessary)
        try:
            trade_decisions = json.loads(trade_response.messages[-1]["content"])
        except json.JSONDecodeError:
            logger.warning(
                "⚠️ Model response was not valid JSON. Falling back to manual parsing."
            )

            # Dynamically generate trade decisions for all assets in the watchlist
            trade_decisions = {
                asset: "buy"
                if asset.split("/")[0] in trade_response.messages[-1]["content"]
                else "sell"
                if asset.split("/")[0] in trade_response.messages[-1]["content"]
                else "hold"
                for asset in watchlist
            }

        logger.info(f"Trade Decisions (Parsed): {trade_decisions}")

        # 4️⃣ Execute Trades
        execute_trades(trade_decisions)

        # 5️⃣ Sleep for 1 Minute
        logger.info("Waiting 20 seconds before next cycle...\n")
        time.sleep(20)


@app.post("/start")
def start_trading(background_tasks: BackgroundTasks):
    """Starts the trading bot in a background thread."""
    global running
    if not running:
        running = True
        background_tasks.add_task(trading_loop)
        return {"status": "Trading bot started"}
    return {"status": "Trading bot already running"}


@app.post("/stop")
def stop_trading():
    """Stops the trading bot."""
    global running
    if running:
        running = False
        return {"status": "Trading bot stopped"}
    return {"status": "Trading bot is not running"}


@app.post("/add-asset/{asset}")
async def add_asset(asset: str):
    """Adds an asset to the watchlist if it exists in Hyperliquid."""
    global watchlist

    # Format asset symbol correctly
    formatted_asset = f"{asset.upper()}/USDC:USDC"

    # Check if asset exists on Hyperliquid
    market_data = hyperliquid.get_market_data(formatted_asset)

    if market_data:
        watchlist.add(formatted_asset)
        return {"status": f"Added {formatted_asset} to watchlist"}

    return {"error": f"Asset {formatted_asset} is not tradable on Hyperliquid"}


@app.post("/remove-asset/{asset}")
async def remove_asset(asset: str):
    """Removes an asset from the watchlist."""
    global watchlist
    if asset in watchlist:
        watchlist.remove(asset)
        return {"status": f"Removed {asset} from watchlist"}
    return {"error": "Asset not in watchlist"}


@app.get("/watchlist")
async def get_watchlist():
    """Returns the current watchlist of assets."""
    return {"watchlist": list(watchlist)}


@app.get("/trades")
async def get_trades():
    """Returns executed trades."""
    return {"executed_trades": executed_trades_log}


@app.get("/status")
async def get_status():
    """Returns the current status of the trading bot."""
    return {"running": running, "watchlist": list(watchlist)}
