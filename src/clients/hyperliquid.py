import ccxt
import time
import math
import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class HyperliquidClient:
    """Handles spot trading for BTC, ETH, and SOL using CCXT with Hyperliquid."""

    def __init__(self, testnet=True):
        self.wallet = settings.HYPERLIQUID_ADDRESS
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

    def get_market_data(self, asset):
        """Retrieve latest OHLCV data (Open, High, Low, Close, Volume)."""
        try:
            data = self.exchange.fetch_ohlcv(asset, timeframe="1m", limit=1)
            logger.info(f"Fetched market data for {asset}: {data}")
            return data  # Latest candle
        except Exception as e:
            logger.error(f"Error fetching market data for {asset}: {e}")
            return None

    def place_order(self, asset, side, amount, price=None):
        """Place a spot limit or market order."""
        try:
            order_type = "limit" if price else "market"

            if order_type == "market":
                # Fetch latest price to set slippage-based price
                latest_price = float(self.exchange.fetch_ticker(asset)["last"])
                slippage = 0.05  # Default 5% slippage
                price = latest_price * (1 + slippage if side == "buy" else 1 - slippage)
                price = round(price, 2)  # Round to 2 decimal places

            elif order_type == "limit":
                # If limit order, ensure price is correctly fetched
                price = self.exchange.load_markets()[asset]["info"]["midPx"]

            # Ensure trade amount is at least $10 worth
            min_trade_size = (
                math.ceil((10 / float(price)) * 10000) / 10000
            )  # Round up to 4 decimals

            order = self.exchange.create_order(
                asset, order_type, side, min_trade_size, price
            )
            logger.info(
                f"Placed {side.upper()} order for {min_trade_size} {asset} at {price}"
            )
            return order

        except Exception as e:
            logger.error(f"Error placing order for {asset}: {e}")
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
