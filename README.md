# Analytic Prototype

Analytic Prototype is a Solana analytics backend (FastAPI + Helius).
Got inspired from GMGN.ai
This prototype fetches live wallet transactions and returns simplified JSON.

## Run locally
venv\Scripts\activate
python -m uvicorn backend.main:app --reload

## Example
GET /wallet/{address}/txs_simple?limit=3
