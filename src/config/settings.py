import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralized settings management."""

    HYPERLIQUID_API_KEY = os.getenv("HYPERLIQUID_API_KEY")
    HYPERLIQUID_ADDRESS = os.getenv("HYPERLIQUID_ADDRESS")
    HYPERLIQUID_WALLET_ADDRESS = os.getenv("HYPERLIQUID_WALLET_ADDRESS")
    HYPERLIQUID_PRIVATE_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY")
    DATABASE_URL = "postgresql://vox@localhost:5432/postgres"
    ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
    OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")


settings = Settings()
