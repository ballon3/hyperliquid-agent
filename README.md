# **Hyperliquid Trading Bot 🚀**

## **📌 Overview**
This is an **automated trading bot** that executes **spot and/or perp trades** on **Hyperliquid** for **multiple assets**, leveraging:
- **FastAPI** for an API interface  
- **Swarm AI Agents** for **risk assessment & trade execution**  
- **CCXT** to interact with **Hyperliquid's exchange**  
- **Dynamic Asset Tracking** (Add/remove assets dynamically to a watchlist)  
- **Automated Trade Execution** (Buy/Sell based on **risk scores**)  
- **Precision Rounding for Hyperliquid Orders** (Avoids **decimal & min-trade-size errors**)  
- **Dev Branch includes additional LLM Agent architectures** a naive (no agent framework implementation), Langchain and pgvector rag based one and a more complex Langgraph non directed acyclic graph architecture
- Used the swarm agent setup for general demo simplicity and conciseness and due to time constraints

---

<img src="demo.gif" alt="Demo preview" width="600" />


## **🛠️ Setup**
### **1️⃣ Clone the repository**
```sh
git clone https://github.com/ballon3/spectral-rnd2.git
cd spectral-rnd2
```

### **2️⃣ Create and Activate Virtual Environment**
```sh
uv venv .venv
source .venv/bin/activate  # On Mac/Linux
# OR
.venv\Scripts\activate  # On Windows
```

### **3️⃣ Install Dependencies**
```sh
uv pip install -r requirements.txt
```

### **4️⃣ Configure Environment Variables**
Create a `.env` file in the root directory:
```ini
HYPERLIQUID_PRIVATE_KEY=your_secret
HYPERLIQUID_WALLET_ADDRESS=your_wallet_address
HYPERLIQUID_API_URL="https://api.hyperliquid-testnet.xyz"
OPENAI_API_KEY=your_openai_key
```

### **5️⃣ Start FastAPI Server**
```sh
PYTHONPATH=src uvicorn src.api.main:app --reload
```

---

## **🚀 Features**
### ✅ **Automated Trading Loop**
- Fetches market data every **minute** 📈  
- Runs **risk assessments** via **Swarm AI** 🤖  
- Decides whether to **Buy, Sell, or Hold** ⚖️  
- **Executes trades** dynamically using **CCXT**  
- **Start trading bot** via API:  
  ```sh
  curl -X POST "http://127.0.0.1:8000/start"
  ```

### ✅ **Dynamic Asset Tracking**
- **Add new assets** via API:  
  ```sh
  curl -X POST "http://127.0.0.1:8000/add-asset/PURR"
  ```
- **Remove assets** from the watchlist:
  ```sh
  curl -X POST "http://127.0.0.1:8000/remove-asset/PURR/USDC:USDC"
  ```

### ✅ **Swarm AI Agents**
- **Risk Assessment Agent** evaluates **volatility, volume & liquidity**  
- **Trade Execution Agent** determines **buy/sell strategy**  

### ✅ **Hyperliquid-Compatible Trade Execution**
- **Ensures minimum trade value ($10) moved to min $20 positions** 💰  
- **Automatically adjusts decimal precision (`szDecimals`)** ✅  
- **Prevents order failures due to incorrect rounding**  

---

## **📡 API Endpoints**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/start` | Starts trading loop |
| `POST` | `/stop` | Stops trading loop |
| `POST` | `/add-asset/{symbol}` | Adds an asset to the watchlist |
| `POST` | `/remove-asset/{symbol}` | Removes an asset from the watchlist |
| `GET` | `/watchlist` | Returns current watchlist |
| `GET` | `/trades` | Returns executed trades |
| `GET` | `/status` | Returns trading bot status |

---

## **🛠 Next Steps: Advanced Features**
### **1️⃣ Context Memory with `pgvector` (RAG)**
📌 **Purpose:** Store **risk assessments & trade history** in a **PostgreSQL vector database** to enhance **decision-making**.
- ✅ **Memory of past trades & risk assessments**  
- ✅ **Retrieve past risk data for trend analysis**  
- ✅ **Use `pgvector` embeddings for trade pattern recognition**  

🚀 **Implementation Plan:**
1. **Store each risk assessment & trade in `pgvector`**  
2. **Retrieve past assessments for a given asset**  
3. **Compare historical data to current market trends**  

---

### **2️⃣ Sentiment Analysis Agent 🧠**
📌 **Purpose:** Analyze **crypto news sentiment** to **adjust trade strategy** dynamically.  
- ✅ Fetch **real-time news & tweets**  
- ✅ AI-powered **sentiment scoring**  
- ✅ Adjust **risk models based on market sentiment**  

🚀 **Implementation Plan:**
1. **Fetch news from APIs (e.g., CoinGecko, Twitter, Reddit, NewsAPI)**  
2. **Use OpenAI's LLM to extract sentiment (positive/neutral/negative)**  
3. **Modify risk scoring based on sentiment trends**  

---

### **3️⃣ More Robust Trading Strategy 📈**
📌 **Purpose:** Move beyond **simple buy/sell triggers** and add **more factors**:
- ✅ **Volatility tracking**
- ✅ **Moving average strategy (SMA, EMA)**
- ✅ **Trade volume analysis**
- ✅ **Multi-layered AI models (Price prediction + Risk assessment)**  

🚀 **Implementation Plan:**
1. **Implement SMA & EMA crossover strategies**  
2. **Detect volume spikes for trade signals**  
3. **Use AI models to forecast price movement**  

---

## **🚀 Ready to Trade?**
```sh
PYTHONPATH=src uvicorn src.api.main:app --reload
```
✅ Start trading, track performance, and integrate **next-gen AI trading strategies!** 🚀