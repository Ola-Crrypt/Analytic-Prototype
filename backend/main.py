from fastapi import FastAPI, HTTPException
from typing import Optional
import os
import requests
from dotenv import load_dotenv


load_dotenv()

def get_helius_key() -> str:
    """Always fetch Helius API key fresh from environment."""
    key = os.getenv("HELIUS_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="HELIUS_API_KEY missing in .env or environment variables"
        )
    return key


app = FastAPI(title="Analytic Prototype")


@app.get("/")
def home():
    return {"message": "Analytic Prototype backend is working!"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/wallet/{address}/txs_simple")
def get_wallet_txs_simple(address: str, limit: Optional[int] = 3):
    """
    Returns recent transactions for a Solana wallet (via Helius),
    simplified to avoid huge responses.
    Example test address: So11111111111111111111111111111111111111112
    """

    api_key = get_helius_key()
    url = (
        f"https://api.helius.xyz/v0/addresses/{address}/transactions"
        f"?api-key={api_key}&limit={limit}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        txs = resp.json()
    except requests.HTTPError:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    slim = []
    for tx in txs:
        token_changes = []
        for ch in tx.get("balanceChanges", []):
            token_info = ch.get("tokenInfo") or {}
            symbol = token_info.get("symbol")
            if symbol:
                token_changes.append({
                    "symbol": symbol,
                    "amount": ch.get("tokenAmount"),
                    "owner": ch.get("account")
                })

        slim.append({
            "signature": tx.get("signature"),
            "timestamp": tx.get("timestamp"),
            "type": tx.get("type"),
            "token_changes": token_changes
        })

    return slim


