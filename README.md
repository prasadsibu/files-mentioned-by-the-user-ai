# 📈 AI Stock Intelligence Platform

An intelligent stock analysis platform that combines AI-powered insights with fundamental analysis to help investors make data-driven decisions. This platform provides real-time stock recommendations, valuation metrics, and comprehensive analysis powered by FastAPI backend and Next.js frontend.

## 🎯 What is This Project?

A comprehensive stock intelligence system that analyzes stocks using:
- **Fundamental Analysis**: ROE, ROCE, debt ratios, cash flow metrics
- **Valuation Metrics**: P/E ratio, P/B ratio, PEG ratio comparisons
- **Market Trends**: Historical price trends and shareholding patterns
- **Sentiment Analysis**: News sentiment and conference call transcripts
- **Risk Assessment**: Automated risk flag detection

## 🏗️ Project Architecture

This is a **full-stack application** with:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python, FastAPI | Stock analysis engine & API |
| **Frontend** | TypeScript, Next.js 15 | Interactive dashboard & visualization |
| **Analysis** | Python (72.3%) | Core AI algorithms and data processing |
| **UI** | TypeScript (26.8%) | Modern web interface |

## 📦 Project Structure

```
files-mentioned-by-the-user-ai/
├── outputs/
│   ├── stock-intelligence-backend/      # FastAPI backend service
│   │   ├── app/
│   │   ├── requirements.txt
│   │   └── README.md
│   └── stock-intelligence-frontend/     # Next.js dashboard
│       ├── src/
│       ├── package.json
│       └── README.md
└── README.md (this file)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (for backend)
- Node.js 18+ (for frontend)
- pip and npm package managers

### Setup Backend

```bash
cd outputs/stock-intelligence-backend
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at: `http://localhost:8000`

### Setup Frontend

```bash
cd outputs/stock-intelligence-frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:3000`

**Configure Backend URL** in `.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 🔌 API Overview

### Analyze Stock
```http
POST /analyze
Content-Type: application/json

{
  "stock": "TCS"
}
```

### Response Example
```json
{
  "symbol": "TCS",
  "recommendation": "BUY",
  "score": 87,
  "fundamentals": {
    "roe": 42.5,
    "roce": 55.2,
    "debt_equity": 0.08,
    "operating_cash_flow": 45200,
    "free_cash_flow": 39800,
    "eps": 120.4
  },
  "valuation": {
    "pe": 28.1,
    "pb": 12.2,
    "peg": 1.4,
    "industry_pe": 31.0,
    "price": 4200
  },
  "trend_history": [],
  "shareholding_history": [],
  "risk_flags": [],
  "news_sentiment": {
    "positive": 0,
    "neutral": 100,
    "negative": 0,
    "sentiment_score": 50
  },
  "concall_summary": {
    "final_view": "Neutral",
    "confidence": 50,
    "reasoning": "No transcript analyzed."
  },
  "score_breakdown": []
}
```

## 📊 Key Features

✅ **Stock Analysis Engine** - Comprehensive fundamental and technical analysis  
✅ **AI-Powered Recommendations** - BUY/HOLD/SELL signals with confidence scores  
✅ **Real-time Dashboard** - Interactive charts and metrics visualization  
✅ **News Sentiment Analysis** - Automatic market sentiment tracking  
✅ **Conference Call Summary** - AI analysis of earnings calls  
✅ **Risk Detection** - Automated alerts for potential risks  
✅ **Valuation Metrics** - Compare stocks against industry benchmarks  

## 🔧 Tech Stack

**Backend**
- FastAPI - Modern Python web framework
- Python - Data processing & AI algorithms
- Uvicorn - ASGI server

**Frontend**
- Next.js 15 - React framework with SSR
- TypeScript - Type-safe JavaScript
- React - UI components

## 📚 Detailed Documentation

- [Backend Documentation](./outputs/stock-intelligence-backend/README.md)
- [Frontend Documentation](./outputs/stock-intelligence-frontend/README.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

**Prasad Sibu** - [GitHub Profile](https://github.com/prasadsibu)

---

**Last Updated**: June 2026

For questions or suggestions, please open an issue on GitHub.
