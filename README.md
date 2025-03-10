# Spectral RnD 2

## ✅ Stack

1. Hyperliquid API → Fetch options, execute trades.
2. Alchemy API (optional) → On-chain analytics (whale movements, token flows).
3. Python + FastAPI → Async server & execution.
4. PostgreSQL + pgvector → Store past trades, embed LLM insights.
5. OpenAI API → Future LLM-driven trade suggestions.

## Agent Architecture

1. check assets over 20m market cap
2. determine risk assesments for list of tokens of 30m market cap
3. make decision for trade options with allocated budget
4. If make trade save to db embeddings

## Agent Methods

1. function calling
2. structured output (each coin has a risk assesment)
3. RAG Database embeddings of risk assesment and trade decisions
