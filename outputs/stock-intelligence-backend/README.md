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
  "stock": "VOLTAMP"
}
```

Response:

```json
{
  "recommendation": "BUY",
  "score": 87
}
```
