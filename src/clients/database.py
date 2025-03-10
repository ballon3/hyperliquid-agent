import asyncpg
from config.settings import settings


class DatabaseManager:
    """Handles PostgreSQL database interactions."""

    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.pool = None

    async def connect(self):
        """Establish a connection pool."""
        self.pool = await asyncpg.create_pool(self.db_url)

    async def store_trade(self, trade_data: dict):
        """Store executed trade details in the database."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO trades (symbol, option_type, strike_price, entry_price, status)
                VALUES ($1, $2, $3, $4, $5)
                """,
                trade_data["symbol"],
                trade_data["option_type"],
                trade_data["strike_price"],
                trade_data["entry_price"],
                "open",
            )
