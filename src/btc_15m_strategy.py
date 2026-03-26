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
            # Start with current aligned window
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 Trying window: {slug} (start: {window_start})")
                
                # Try current window first
                market = await fetch_market_by_slug(slug)
                
                # If current window has no tokens or bad prices, try NEXT window
                if not market or len(market.get("clobTokenIds", [])) < 2:
                    next_window = window_start + 900
                    next_slug = f"btc-updown-15m-{next_window}"
                    print(f"⚠️ Current window not ready — trying next: {next_slug}")
                    market = await fetch_market_by_slug(next_slug)
                    slug = next_slug

                if not market:
                    print("⚠️ No active BTC 15m market found. Waiting...")
                    await asyncio.sleep(30)
                    continue

                tokens = market.get("clobTokenIds", [])
                print(f"🔍 Tokens found: {len(tokens)} → {[t[:12] + '...' for t in tokens[:2]] if tokens else 'NONE'}")

                if len(tokens) < 2:
                    print(f"⚠️ Insufficient tokens for {slug}. Waiting...")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug
                print(f"✅ Tokens saved for {slug}!")

            # Fetch BUY prices from CLOB
            clob_base = "https://clob.polymarket.com"
            up_resp = requests.get(f"{clob_base}/price?token_id={up_token}&side=BUY", timeout=10)
            down_resp = requests.get(f"{clob_base}/price?token_id={down_token}&side=BUY", timeout=10)

            up_resp.raise_for_status()
            down_resp.raise_for_status()

            up_price = float(up_resp.json().get("price", 0.50))
            down_price = float(down_resp.json().get("price", 0.50))
            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Total: {total:.3f} | Window: {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total:.3f} ≤ ${cheap_threshold:.2f} — Buy both sides")
                # TODO: Add buy logic here later using bot
            else:
                print(f"😌 No cheap opportunities (total {total:.3f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)


async def fetch_market_by_slug(slug: str):
    """Helper to fetch market data by slug with logging"""
    gamma_url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
    print(f"🌐 Fetching: {gamma_url}")
    
    resp = requests.get(gamma_url, timeout=15)
    if resp.status_code != 200:
        print(f"💥 Slug {slug} returned {resp.status_code}")
        return None
    
    market = resp.json()
    if isinstance(market, list) and market:
        market = market[0]
    
    print(f"✅ Market data received for {slug}")
    return market


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
