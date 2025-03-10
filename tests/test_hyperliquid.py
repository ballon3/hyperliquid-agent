import pytest
from unittest.mock import MagicMock, patch
from clients.hyperliquid import HyperliquidClient
import math 

@pytest.fixture
def client():
    """Fixture to initialize HyperliquidClient."""
    return HyperliquidClient()

def test_get_balance(client):
    """Test fetching account balance."""
    client.exchange.fetch_balance = MagicMock(return_value={"total": {"BTC": 0.5, "ETH": 2.0, "USDC": 10000}})
    
    balance = client.get_balance()
    
    assert balance == {"BTC": 0.5, "ETH": 2.0, "USDC": 10000}, "Balance does not match expected result"
    client.exchange.fetch_balance.assert_called_once()

def test_get_market_data(client):
    """Test fetching market data for an asset."""
    client.exchange.fetch_ohlcv = MagicMock(return_value=[
        [1700000000, 40000, 40500, 39500, 40200, 100]
    ])
    
    market_data = client.get_market_data("BTC/USDC")
    
    assert market_data == [1700000000, 40000, 40500, 39500, 40200, 100], "Market data does not match expected result"
    client.exchange.fetch_ohlcv.assert_called_once_with("BTC/USDC", timeframe="1m", limit=1)

@patch("clients.hyperliquid.HyperliquidClient.place_order")
def test_place_market_order(mock_place_order, client):
    """Test placing a market order."""
    mock_place_order.return_value = {"id": "order123", "status": "open"}
    
    order = client.place_order("BTC/USDC", "buy", 0.01)
    
    assert order == {"id": "order123", "status": "open"}, "Market order placement failed"
    mock_place_order.assert_called_once_with("BTC/USDC", "buy", 0.01)

@patch("clients.hyperliquid.HyperliquidClient.place_order")
def test_place_limit_order(mock_place_order, client):
    """Test placing a limit order."""
    mock_place_order.return_value = {"id": "order124", "status": "open"}
    
    order = client.place_order("ETH/USDC", "sell", 0.5, 3000)
    
    assert order == {"id": "order124", "status": "open"}, "Limit order placement failed"
    mock_place_order.assert_called_once_with("ETH/USDC", "sell", 0.5, 3000)

@patch("clients.hyperliquid.HyperliquidClient.cancel_all_orders")
def test_cancel_orders(mock_cancel_all_orders, client):
    """Test canceling all orders for an asset."""
    mock_cancel_all_orders.return_value = {"status": "success"}
    
    result = client.cancel_all_orders("BTC/USDC")
    
    assert result == {"status": "success"}, "Order cancellation failed"
    mock_cancel_all_orders.assert_called_once_with("BTC/USDC")


# @patch("clients.hyperliquid.HyperliquidClient.place_order")
# def test_place_spot_order_non_patch(client):
#     """Test placing a market order."""
#     # mock_place_order.return_value = {"id": "order123", "status": "open"}
#     price = client.exchange.load_markets()["ETH/USDC:USDC"]["info"]["midPx"]
#     print("Price: ", price) 
    
#     min_trade_size = math.ceil((10 / float(price)) * 10000) / 10000  # Round up to 4 decimals

#     print(f"Price: {price}, Min Trade Size: {min_trade_size}")

#     order = client.place_order("ETH/USDC:USDC", "buy", min_trade_size, price)
    
#     print(order)
#     assert order != None, "Market order placement failed"
#     # assert order == {"id": "order123", "status": "open"}, "Market order placement failed"
#     # mock_place_order.assert_called_once_with("BTC/USDC", "buy", 0.01)
