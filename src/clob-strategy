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

    # Bybit public API base
    bybit_url = "https://api.bybit.com/v5/market/tickers"
    bybit_params = {"category": "spot", "symbol": "BTCUSDT"}

    while True:
        try:
            now = int(time.time())
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 Checking current window: {slug}")

                # Try current window first
                market = fetch_market_by_slug(slug)

                # If not ready, try next window
                if not market or len(market.get("clobTokenIds", [])) < 2:
                    next_start = window_start + 900
                    next_slug = f"btc-updown-15m-{next_start}"
                    print(f"⚠️ Current not ready → Trying next window: {next_slug}")
                    market = fetch_market_by_slug(next_slug)
                    slug = next_slug

                if not market or len(market.get("clobTokenIds", [])) < 2:
                    print("⚠️ No active market found. Waiting 30s...")
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
                print(f"✅ Ready! Using {slug} | Up token: {up_token[:12]}... | Down token: {down_token[:12]}...")

            # === Fetch BUY prices from CLOB ===
            clob_base = "https://clob.polymarket.com"
            up_resp = requests.get(f"{clob_base}/price?token_id={up_token}&side=BUY", timeout=10)
            down_resp = requests.get(f"{clob_base}/price?token_id={down_token}&side=BUY", timeout=10)

            up_resp.raise_for_status()
            down_resp.raise_for_status()

            up_price = float(up_resp.json().get("price", 0.50))
            down_price = float(down_resp.json().get("price", 0.50))
            total = up_price + down_price

            # === Bybit BTC price check ===
            try:
                bybit_resp = requests.get(bybit_url, params=bybit_params, timeout=8)
                bybit_resp.raise_for_status()
                bybit_data = bybit_resp.json().get("result", [{}])[0]
                btc_price = float(bybit_data.get("lastPrice", 0))
                btc_change = bybit_data.get("price24hPcnt", "N/A")
            except Exception:
                btc_price = 0
                btc_change = "N/A"

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Total: {total:.3f} | BTC: ${btc_price:,.0f} ({btc_change}) | Window: {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP! Total {total:.3f} — Buy both sides now")
                # TODO: Add your buy code here using bot.buy(...) or similar
                # Example placeholder:
                # await bot.buy(up_token, size, up_price)
                # await bot.buy(down_token, size, down_price)
            else:
                print(f"😌 No cheap opportunities (total {total:.3f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)


def fetch_market_by_slug(slug: str):
    """Fetch market data (now using a more reliable endpoint; fallback to gamma if needed)"""
    # Primary: Try Polymarket markets search/filter (more reliable for slug-based 15m markets)
    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"  # or use /markets with filter
        print(f"🌐 Fetching market for slug: {slug}")
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"   → Slug fetch failed: {e}")

    # Fallback to original gamma endpoint
    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
    print(f"🌐 Fallback fetching {url}")
    resp = requests.get(url, timeout=15)
    
    if resp.status_code != 200:
        print(f"   → Got status {resp.status_code}")
        return None
    
    data = resp.json()
    if isinstance(data, list) and data:
        data = data[0]
    
    print(f"   → Market data received for {slug}")
    return data


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
