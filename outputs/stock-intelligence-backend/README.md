# AI Stock Intelligence Backend

Local FastAPI backend for stock analysis.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

```http
POST /analyze
Content-Type: application/json

{
  "stock": "TCS"
}
```

Response includes the recommendation plus the data used by the frontend dashboard:

```json
{
  "symbol": "TCS",
  "recommendation": "BUY",
  "score": 87,
  "fundamentals": { "roe": 42.5, "roce": 55.2, "debt_equity": 0.08, "operating_cash_flow": 45200, "free_cash_flow": 39800, "eps": 120.4 },
  "valuation": { "pe": 28.1, "pb": 12.2, "peg": 1.4, "industry_pe": 31.0, "price": 4200 },
  "trend_history": [],
  "shareholding_history": [],
  "risk_flags": [],
  "news_sentiment": { "positive": 0, "neutral": 100, "negative": 0, "sentiment_score": 50, "articles": [] },
  "concall_summary": { "final_view": "Neutral", "confidence": 50, "reasoning": "No transcript analyzed.", "signals": [] },
  "score_breakdown": []
}
```
