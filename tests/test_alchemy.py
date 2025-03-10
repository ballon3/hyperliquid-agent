import asyncio
import pytest
from clients.alchemy import AlchemyClient


@pytest.mark.asyncio
async def test_get_token_metadata():
    """Test fetching token metadata from Alchemy."""
    client = AlchemyClient()
    token_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC example
    metadata = await client.get_token_metadata(token_address)

    assert metadata is not None, "Metadata should not be None"
    assert "result" in metadata, "Expected 'result' key in response"
    assert "name" in metadata["result"], "Expected 'name' in token metadata"


if __name__ == "__main__":
    asyncio.run(test_get_token_metadata())
