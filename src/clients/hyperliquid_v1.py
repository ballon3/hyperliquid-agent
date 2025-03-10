import aiohttp
from config.settings import settings
import logging
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
import eth_account
from eth_account.signers.local import LocalAccount

logger = logging.getLogger(__name__)

class HyperliquidClient:
    """Handles API interactions with Hyperliquid for Spot Trading."""

    def __init__(self):
        self.api_key = settings.HYPERLIQUID_API_KEY
        self.base_url = "https://api.hyperliquid-testnet.xyz/info"

        # Agent-based trading setup
        self.api_url = constants.TESTNET_API_URL  # Use mainnet for live trading
        self.account_address, self.wallet_info, self.exchange = self._setup_exchange()
        self.agent_account = self._approve_agent()

    async def _post_request(self, payload: dict):
        """Helper function to send async POST requests."""
        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                text_response = await response.text()
                logger.info(f"Response ({response.status}): {text_response}")

                if response.status != 200:
                    logger.error(f"API error {response.status}: {text_response}")
                    return None

                return await response.json()

    async def get_all_coins(self):
        """Fetch all tradable spot tokens from Hyperliquid."""
        payload = {"type": "meta"}
        response = await self._post_request(payload)

        if not response or "tokens" not in response:
            logger.error("Failed to fetch tokens from Hyperliquid.")
            return {}

        coins = {token["name"]: token for token in response["tokens"]}

        logger.info(f"Retrieved {len(coins)} tokens from Hyperliquid.")
        return coins

    async def get_mids(self):
        """Retrieve mid-market prices for all tradable assets."""
        payload = {"type": "allMids"}
        response = await self._post_request(payload)

        if not response or "mids" not in response:
            logger.error("Failed to fetch mids from Hyperliquid.")
            return {}

        return response["mids"]
        
    def _setup_exchange(self):
        """Initialize the exchange connection using the provided private key and account address."""
        try:
            # Load private key & account address from environment variables
            secret_key = settings.HYPERLIQUID_PRIVATE_KEY
            account_address = settings.HYPERLIQUID_ADDRESS

            # Create an eth_account instance
            account: LocalAccount = eth_account.Account.from_key(secret_key)
            
            # Ensure correct address
            if account_address != account.address:
                logger.warning(f"Using agent address: {account.address} instead of account address: {account_address}")

            # Initialize Hyperliquid SDK Info & Exchange objects
            info = Info(self.base_url, skip_ws=True)
            exchange = Exchange(account, self.base_url, account_address=account_address)

            # Check account state (ensure it has balance)
            user_state = info.user_state(account_address)
            spot_user_state = info.spot_user_state(account_address)
            margin_summary = user_state["marginSummary"]

            if float(margin_summary["accountValue"]) == 0 and len(spot_user_state["balances"]) == 0:
                raise Exception(f"No balance found for account {account_address}.")

            logger.info(f"Running with account address: {account_address}")

            return account_address, account, info, exchange
        except Exception as e:
            logger.error(f"Error setting up exchange: {e}")
            raise

    def _approve_agent(self):
        """Approve and create an agent account."""
        try:
            approve_result, agent_key = self.exchange.approve_agent()
            if approve_result["status"] != "ok":
                logger.error(f"Agent approval failed: {approve_result}")
                raise Exception("Agent approval failed.")
            
            agent_account = eth_account.Account.from_key(agent_key)
            logger.info(f"Agent approved successfully: {agent_account.address}")
            return agent_account
        except Exception as e:
            logger.error(f"Error approving agent: {e}")
            raise

    def place_order(self, asset: str, is_buy: bool, price: float, size: float):
        """Place an order using the approved agent."""
        try:
            agent_exchange = Exchange(self.agent_account, self.api_url, account_address=self.account_address)
            order_result = agent_exchange.order(asset, is_buy, size, price, {"limit": {"tif": "Gtc"}})
            
            if order_result["status"] == "ok":
                logger.info(f"Order placed successfully: {order_result}")
                return order_result
            else:
                logger.error(f"Order failed: {order_result}")
                return None
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def cancel_order(self, asset: str, order_id: int):
        """Cancel a resting order."""
        try:
            agent_exchange = Exchange(self.agent_account, self.api_url, account_address=self.account_address)
            cancel_result = agent_exchange.cancel(asset, order_id)
            logger.info(f"Order cancellation result: {cancel_result}")
            return cancel_result
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return None