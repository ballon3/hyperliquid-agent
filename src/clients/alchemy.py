import aiohttp
import os
from config.settings import settings


class AlchemyClient:
    """Handles API interactions with Alchemy for token metadata."""

    def __init__(self):
        self.api_key = settings.ALCHEMY_API_KEY
        self.base_url = f"https://eth-mainnet.g.alchemy.com/v2/{self.api_key}"

    async def get_token_metadata(self, token_address: str):
        """Fetch token metadata from Alchemy."""
        url = self.base_url
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenMetadata",
            "params": [token_address],
        }
        headers = {"accept": "application/json", "content-type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                return await response.json()
