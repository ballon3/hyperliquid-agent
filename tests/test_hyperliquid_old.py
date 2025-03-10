# import asyncio
# import pytest
# from clients.hyperliquid import HyperliquidClient
# from config.settings import settings


# @pytest.mark.asyncio
# async def test_get_spot_metadata():
#     """Test fetching tradable spot tokens and pairs."""
#     client = HyperliquidClient()
#     response = await client.get_spot_metadata()

#     assert response is not None, "Response should not be None"
#     assert "tokens" in response, "Expected 'tokens' in response"


# @pytest.mark.asyncio
# async def test_get_spot_market_data():
#     """Test fetching market price and volume data."""
#     client = HyperliquidClient()
#     response = await client.get_spot_market_data()

#     assert response is not None, "Response should not be None"
#     assert isinstance(response, list), "Expected a list of market data"


# @pytest.mark.asyncio
# async def test_get_account_balance():
#     """Test fetching user wallet balance"""
#     client = HyperliquidClient()
#     response = await client.get_user_balances(user_address=settings.HYPERLIQUID_ADDRESS)

#     print(response)

#     assert response is not None, "Response should not be None"
#     assert isinstance(response, dict), "Expected a list of market data"


# if __name__ == "__main__":
#     asyncio.run(test_get_spot_metadata())
#     asyncio.run(test_get_spot_market_data())
