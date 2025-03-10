CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    option_type TEXT NOT NULL,  -- "call" or "put"
    strike_price FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    status TEXT DEFAULT 'open', -- "open", "closed"
    created_at TIMESTAMP DEFAULT NOW()
);


CREATE TABLE risk_trade_memory (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    risk_score FLOAT NOT NULL,
    embedding VECTOR(1536) NOT NULL -- OpenAI Embedding Dimension
);

