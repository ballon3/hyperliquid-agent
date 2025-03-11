import json
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app, execute_trades, trading_loop, hyperliquid

# ✅ Initialize test client
client = TestClient(app)


# ✅ TEST API ENDPOINTS
@pytest.mark.parametrize("endpoint", [
    "/status",
    "/watchlist",
    "/trades",
    "/open-positions",
    "/open-orders"
])
def test_get_endpoints(endpoint):
    """Test GET endpoints return a 200 response and valid JSON."""
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

def test_stop_trading():
    """Test stopping the trading bot."""
    response = client.post("/stop")
    assert response.status_code == 200
    assert response.json()["status"] in ["Trading bot stopped", "Trading bot is not running"]


def test_add_remove_asset():
    """Test adding and removing an asset from the watchlist."""
    asset = "DOGE"
    response = client.post(f"/add-asset/{asset}")
    assert response.status_code == 200

    response = client.post(f"/remove-asset/{asset}")
    assert response.status_code == 200


# ✅ TEST TRADE EXECUTION LOGIC
@pytest.fixture
def mock_hyperliquid():
    """Mock Hyperliquid API client for testing trade execution."""
    with patch("api.main.hyperliquid") as mock:
        mock.exchange.fetch_ticker.return_value = {"last": "100.0"}  # Fake price
        mock.place_order.return_value = {"status": "ok", "order_id": "123"}
        yield mock


def test_execute_trades(mock_hyperliquid):
    """Test the trade execution function."""
    trade_decisions = {"ETH/USDC:USDC": "buy", "BTC/USDC:USDC": "sell"}
    open_positions = {
        "ETH/USDC:USDC": {"side": "long", "contracts": "1.0", "entryPrice": "2000"},
        "BTC/USDC:USDC": {"side": "short", "contracts": "0.5", "entryPrice": "80000"}
    }

    result = execute_trades(trade_decisions, open_positions)
    assert isinstance(result, list)
    assert len(result) > 0


def test_execute_trades_with_no_open_positions(mock_hyperliquid):
    """Test execute_trades when there are no open positions."""
    trade_decisions = {"ETH/USDC:USDC": "buy"}
    open_positions = {}  # No open positions

    result = execute_trades(trade_decisions, open_positions)
    assert isinstance(result, list)
    assert len(result) > 0  # Expect at least one trade to execute

if __name__ == "__main__":
    pytest.main()
