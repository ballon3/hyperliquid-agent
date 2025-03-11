import os
import logging
import json
import time
import math
import threading
import coloredlogs

import decimal
from decimal import Decimal, ROUND_UP, ROUND_DOWN

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

def execute_trades(trade_decisions, open_positions):
    """Executes trades while ensuring orders meet Hyperliquid's $20 minimum, managing TP/SL, and shorting when needed."""
    global executed_trades_log
    executed_trades = []

    for asset, decision in trade_decisions.items():
        if asset not in watchlist:
            logger.info(f"Skipping {asset}: Not in watchlist")
            continue

        if decision not in ["buy", "sell"]:
            logger.info(f"Skipping {asset}: No action needed ({decision})")
            continue

        # ✅ Fetch latest price
        try:
            ticker = hyperliquid.exchange.fetch_ticker(asset)
            latest_price = Decimal(str(ticker["last"]))  # Ensure Decimal precision
        except Exception as e:
            logger.error(f"❌ Error fetching price for {asset}: {e}")
            continue

        # ✅ Ensure minimum trade value of $20
        min_trade_size = (Decimal("20") / latest_price).quantize(Decimal("0.000001"), rounding=ROUND_UP)
        logger.info(f"ℹ️ Calculated min trade size for {asset}: {min_trade_size} (latest price: {latest_price})")

        # ✅ Initialize TP & SL correctly
        if asset in open_positions:
            position = open_positions[asset]
            position_side = position["side"]
            position_size = Decimal(str(position["contracts"]))
            entry_price = Decimal(str(position["entryPrice"]))
        else:
            # If no open position, set entry price to latest price
            position_side = "none"
            position_size = min_trade_size
            entry_price = latest_price

        # **Fix TP & SL Calculation to avoid exceeding 80% limit**
        take_profit_price = (entry_price * Decimal("1.20")).quantize(Decimal("0.01"), rounding=ROUND_UP)
        stop_loss_price = (entry_price * Decimal("0.80")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        logger.info(f"📊 Setting TP: {take_profit_price}, SL: {stop_loss_price} for {asset}")

        # ✅ Close Long Position on Sell
        if decision == "sell" and position_side == "long":
            logger.info(f"⚠️ Closing long position on {asset}.")
            order = hyperliquid.place_order(
                asset, "sell", float(position_size), float(latest_price),
                take_profit_price, stop_loss_price
            )
            executed_trades.append(order)
            continue  # Skip new trade if closing position

        # ✅ Close Short Position on Buy
        if decision == "buy" and position_side == "short":
            logger.info(f"⚠️ Closing short position on {asset}.")
            order = hyperliquid.place_order(
                asset, "buy", float(position_size), float(latest_price),
                take_profit_price, stop_loss_price
            )
            executed_trades.append(order)
            continue  # Skip new trade if closing position

        # ✅ Open New Short Position if Selling
        if decision == "sell" and position_side == "none":
            logger.info(f"🛑 Opening new SHORT position on {asset}.")
            order = hyperliquid.place_order(
                asset, "sell", float(min_trade_size), float(latest_price),
                take_profit_price, stop_loss_price
            )
            executed_trades.append(order)
            continue

        # ✅ Open New Long Position if Buying
        if decision == "buy" and position_side == "none":
            logger.info(f"📈 Opening new LONG position on {asset}.")
            order = hyperliquid.place_order(
                asset, "buy", float(min_trade_size), float(latest_price),
                take_profit_price, stop_loss_price
            )
            executed_trades.append(order)
            continue

        # ✅ Place New Orders if No Existing Position
        order = hyperliquid.place_order(
            asset, decision, float(min_trade_size), float(latest_price),
            take_profit_price, stop_loss_price
        )
        if order:
            logger.info(f"✅ Executed {decision.upper()} order for {min_trade_size} {asset} at {latest_price}")
            executed_trades.append(order)
            executed_trades_log.append(order)
        else:
            logger.error(f"❌ Failed to place order for {asset}")

    return executed_trades

def trading_loop():
    """Main trading loop: fetch market data, assess risk (including open positions), and execute trades."""
    global running
    while running:
        logger.info("\n---- Running Trading Cycle ----")

        # 1️⃣ Fetch Market Data & Open Positions
        market_data = {asset: hyperliquid.get_market_data(asset) for asset in watchlist}
        open_positions = hyperliquid.get_open_positions()

        # 2️⃣ Merge Market Data & Open Positions for Risk Assessment
        risk_input = {"market_data": market_data, "open_positions": open_positions}
        # logger.info(f"Risk Assessment Input: {json.dumps(risk_input, indent=4)}")
        # 3️⃣ Send Data to Risk Assessment Agent
        risk_response = swarm_client.run(
            agent=risk_assessment_agent,
            messages=[{"role": "user", "content": f"Analyze risk for {json.dumps(risk_input)}"}],
        )
        risk_scores = risk_response.messages[-1]["content"]
        logger.info(f"Risk Scores: {risk_scores}")

        # 4️⃣ Trade Execution Decision
        trade_response = swarm_client.run(
            agent=trade_execution_agent,
            messages=[{"role": "user", "content": f"Make trade decisions for risk: {risk_scores}"}],
        )

        # Ensure response is a dictionary (parse JSON if necessary)
        try:
            trade_decisions = json.loads(trade_response.messages[-1]["content"])
        except json.JSONDecodeError:
            logger.warning("⚠️ Model response was not valid JSON. Falling back to manual parsing.")
            trade_decisions = {
                asset: "buy" if asset.split("/")[0] in trade_response.messages[-1]["content"] else "hold"
                for asset in watchlist
            }

        logger.info(f"Trade Decisions (Parsed): {trade_decisions}")

        # 5️⃣ Execute Trades (Now Considering Open Positions)
        execute_trades(trade_decisions, open_positions)

        # 6️⃣ Sleep for Next Cycle
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

### ✅ FETCH OPEN POSITIONS
@app.get("/open-positions")
def get_open_positions():
    """Fetches open positions from Hyperliquid."""
    try:
        positions = hyperliquid.exchange.fetch_positions()
        formatted_positions = {p["symbol"]: p for p in positions if p["contracts"] > 0}
        return {"open_positions": formatted_positions}
    except Exception as e:
        logger.error(f"Error fetching open positions: {e}")
        return {"error": "Failed to fetch open positions"}


### ✅ FETCH OPEN ORDERS
@app.get("/open-orders")
def get_open_orders():
    """Fetches open orders from Hyperliquid."""
    try:
        orders = hyperliquid.exchange.fetch_open_orders()
        return {"open_orders": orders}
    except Exception as e:
        logger.error(f"Error fetching open orders: {e}")
        return {"error": "Failed to fetch open orders"}