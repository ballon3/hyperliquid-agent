import ccxt
import time
import math
import logging
import json
from config.settings import settings
from decimal import Decimal, ROUND_UP, ROUND_DOWN

logger = logging.getLogger(__name__)


class HyperliquidClient:
    """Handles spot trading for BTC, ETH, and SOL using CCXT with Hyperliquid."""

    def __init__(self, testnet=True):
        self.wallet = settings.HYPERLIQUID_WALLET_ADDRESS
        self.secret = settings.HYPERLIQUID_PRIVATE_KEY
        self.testnet = testnet
        self.exchange = ccxt.hyperliquid(
            {
                "walletAddress": self.wallet,
                "privateKey": self.secret,
            }
        )

        if self.testnet:
            self.exchange.set_sandbox_mode(True)
            # self.exchange.urls["api"] = "https://api.hyperliquid-testnet.xyz"

        self.assets = ["BTC/USDC:USDC", "ETH/USDC:USDC", "SOL/USDC:USDC"]

    def get_open_positions(self):
        """Fetch open positions for all assets."""
        try:
            positions = self.exchange.fetch_positions()
            open_positions = {pos["symbol"]: pos for pos in positions if float(pos["contracts"]) != 0}
            logger.info(f"Fetched open positions: {json.dumps(open_positions, indent=4)}")
            return open_positions
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
            return {}

    def get_market_data(self, asset):
        """Retrieve latest OHLCV data (Open, High, Low, Close, Volume)."""
        try:
            data = self.exchange.fetch_ohlcv(asset, timeframe="1m", limit=1)
            logger.info(f"Fetched market data for {asset}: {data}")
            return data  # Latest candle
        except Exception as e:
            logger.error(f"Error fetching market data for {asset}: {e}")
            return None

    def place_order(self, asset, side, amount, price=None, take_profit=None, stop_loss=None):
        """Places a spot limit or market order with TP/SL settings."""
        try:
            order_type = "limit" if price else "market"

            if order_type == "market":
                # Fetch latest price to set slippage-based price
                latest_price = float(self.exchange.fetch_ticker(asset)["last"])
                slippage = 0.02  # ✅ Reduce slippage to 2% for better accuracy
                price = latest_price * (1 + slippage if side == "buy" else 1 - slippage)
                price = round(price, 2)  # ✅ Ensure correct decimal places

            elif order_type == "limit":
                # If limit order, ensure price is correctly fetched
                price = self.exchange.load_markets()[asset]["info"]["midPx"]

            # ✅ Ensure trade amount is at least $20 worth
            min_trade_size = (Decimal("20") / Decimal(str(price))).quantize(Decimal("0.000001"), rounding=ROUND_UP)

            # ✅ Construct order params with TP/SL
            order_params = {
                "symbol": asset,
                "type": order_type,
                "side": side,
                "amount": float(min_trade_size),
                "price": float(price),
                "params": {}
            }

            if take_profit:
                order_params["params"]["triggerPrice"] = float(take_profit)
                order_params["params"]["tpsl"] = "tp"

            if stop_loss:
                order_params["params"]["triggerPrice"] = float(stop_loss)
                order_params["params"]["tpsl"] = "sl"

            logger.info(f"🛠️ Placing order with TP: {take_profit}, SL: {stop_loss} for {asset}")
            order = self.exchange.create_order(**order_params)
            
            logger.info(f"✅ Placed {side.upper()} order for {min_trade_size} {asset} at {price} with TP {take_profit} and SL {stop_loss}")
            return order

        except Exception as e:
            logger.error(f"❌ Error placing order for {asset}: {e}")
            return None

    def cancel_all_orders(self, asset):
        """Cancel all open orders for a specific asset."""
        try:
            orders = self.exchange.fetch_open_orders(asset)
            for order in orders:
                self.exchange.cancel_order(order["id"], asset)
            logger.info(f"Canceled all orders for {asset}")
        except Exception as e:
            logger.error(f"Error canceling orders for {asset}: {e}")
