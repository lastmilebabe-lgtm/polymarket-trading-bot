import asyncio
import time
import os
from datetime import datetime

import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON  # or 137 directly

from src.bot import TradingBot  # keep your existing bot if it has extra logic

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ ${cheap_threshold:.2f}")

    # === Initialize official CLOB client (do this once) ===
    host = "https://clob.polymarket.com"
    chain_id = 137  # Polygon

    private_key = os.getenv("POLY_PRIVATE_KEY")
    if not private_key:
        raise ValueError("POLY_PRIVATE_KEY env var is required")

    # Derive API creds (L2 auth) - do this at startup
    temp_client = ClobClient(host, key=private_key, chain_id=chain_id)
    api_creds = temp_client.create_or_derive_api_creds()

    client = ClobClient(
        host=host,
        key=private_key,
        chain_id=chain_id,
        creds=api_creds,
        signature_type=0,  # 0 = EOA, adjust if using Gnosis Safe
        # funder=os.getenv("FUNDER_ADDRESS")  # uncomment if needed
    )

    print("✅ CLOB client initialized with L2 auth")

    current_slug = None
    up_token = down_token = None

    while True:
        try:
            now = int(time.time())
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 New window detected: {slug}")
                
                # Try current, then next window (very common for these markets)
                market = fetch_market(slug)
                if not market or len(market.get("clobTokenIds", [])) < 2:
                    next_start = window_start + 900
                    next_slug = f"btc-updown-15m-{next_start}"
                    print(f"⚠️ Current not ready → Trying next: {next_slug}")
                    market = fetch_market(next_slug)
                    slug = next_slug

                if not market:
                    print("⚠️ No active market. Waiting 30s...")
                    await asyncio.sleep(30)
                    continue

                tokens = market.get("clobTokenIds", [])
                if len(tokens) < 2:
                    print("⚠️ Not enough tokens yet. Waiting...")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug
                print(f"✅ Ready! {slug} | Up: {up_token[:12]}... | Down: {down_token[:12]}...")

            # === Fetch BUY prices (mid or best ask) ===
            clob = "https://clob.polymarket.com"
            up_resp = requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=8)
            down_resp = requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=8)

            up_resp.raise_for_status()
            down_resp.raise_for_status()

            up_price = float(up_resp.json().get("price", 0.50))
            down_price = float(down_resp.json().get("price", 0.50))
            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up BUY: {up_price:.4f} | Down BUY: {down_price:.4f} | "
                  f"Total: {total:.4f} | {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP! Total {total:.4f} — Executing buys...")

                # === ACTUAL TRADES using official client ===
                try:
                    # Buy UP
                    order_up = client.create_and_post_order({
                        "token_id": up_token,
                        "price": up_price,      # or slightly worse for fill probability
                        "size": size,
                        "side": "BUY",
                    })
                    print(f"✅ UP order posted: {order_up}")

                    # Buy DOWN
                    order_down = client.create_and_post_order({
                        "token_id": down_token,
                        "price": down_price,
                        "size": size,
                        "side": "BUY",
                    })
                    print(f"✅ DOWN order posted: {order_down}")

                    # Optional: wait a bit and check user channel / fills if you add WS later

                except Exception as trade_err:
                    print(f"💥 Trade failed: {trade_err}")
                    # Add retry logic or smaller size here if desired

            else:
                print(f"😌 No opportunity (total {total:.4f} > {cheap_threshold})")

        except Exception as e:
            print(f"💥 Loop error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)  # check every minute (or 30s for tighter monitoring)


def fetch_market(slug: str):
    """Fetch market by slug from Gamma API"""
    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
    print(f"🌐 Fetching market: {slug}")
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            print(f"   → Status {resp.status_code}")
            return None
        
        data = resp.json()
        if isinstance(data, list) and data:
            data = data[0]
        
        print(f"   → Market fetched successfully")
        return data
    except Exception as e:
        print(f"   → Fetch failed: {e}")
        return None


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")  # keep if it does extra setup
    size = float(os.environ.get("POLY_DEFAULT_SIZE", "5.0"))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
