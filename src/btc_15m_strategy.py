import asyncio
import time
import requests
import os
from datetime import datetime
from src.bot import TradingBot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ ${cheap_threshold:.2f}")

    current_slug = None
    up_token = down_token = None

    while True:
        try:
            now = int(time.time())
            # Align to the current 15-minute window start (Unix timestamp)
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 New window detected: {slug} (start: {window_start})")
                
                # Use the reliable slug endpoint (confirmed working)
                gamma_url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
                print(f"🌐 Fetching market data: {gamma_url}")
                
                gamma_resp = requests.get(gamma_url, timeout=15)
                gamma_resp.raise_for_status()
                market = gamma_resp.json()

                # Some responses may be wrapped in a list
                if isinstance(market, list) and market:
                    market = market[0]

                tokens = market.get("clobTokenIds", [])
                print(f"🔍 Tokens found: {len(tokens)} → {[t[:12] + '...' for t in tokens[:2]] if tokens else 'NONE'}")

                if len(tokens) < 2:
                    print(f"⚠️ Market {slug} not active yet or missing tokens. Waiting...")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]   # Usually the "Up" / Yes token
                down_token = tokens[1] # Usually the "Down" / No token
                current_slug = slug
                print(f"✅ Tokens saved successfully! Up: {up_token[:15]}... | Down: {down_token[:15]}...")

            # === Fetch current BUY prices from CLOB ===
            clob_base = "https://clob.polymarket.com"
            
            up_resp =
