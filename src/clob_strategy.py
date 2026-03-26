import asyncio
import time
import requests
import os
import json
from datetime import datetime
from src.bot import TradingBot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ ${cheap_threshold:.2f}")

    current_slug = None
    up_token = down_token = None

    # Bybit for real BTC context
    bybit_url = "https://api.bybit.com/v5/market/tickers"
    bybit_params = {"category": "spot", "symbol": "BTCUSDT"}

    clob_base = "https://clob.polymarket.com"

    while True:
        try:
            now = int(time.time())
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 Checking current window: {slug}")

                market = fetch_market_by_slug(slug)

                # Try next window if current not ready
                if not market or not get_clob_tokens(market):
                    next_start = window_start + 900
                    next_slug = f"btc-updown-15m-{next_start}"
                    print(f"⚠️ Current not ready → Trying next: {next_slug}")
                    market = fetch_market_by_slug(next_slug)
                    slug = next_slug

                clob_tokens = get_clob_tokens(market)

                if not clob_tokens or len(clob_tokens) < 2:
                    print("⚠️ Not enough valid clobTokenIds yet. Waiting 30s...")
                    await asyncio.sleep(30)
                    continue

                up_token = clob_tokens[0]
                down_token = clob_tokens[1]

                current_slug = slug
                print(f"✅ Ready! Using {slug}")
                print(f"   Up token : {up_token[:20]}...{up_token[-8:]}")
                print(f"   Down token: {down_token[:20]}...{down_token[-8:]}")

            # === Fetch BUY prices from CLOB ===
            up_price = down_price = 0.50

            try:
                up_resp = requests.get(
                    f"{clob_base}/price?token_id={up_token}&side=BUY",
                    timeout=10
                )
                up_resp.raise_for_status()
                up_price = float(up_resp.json().get("price", 0.50))
            except Exception as e:
                print(f"⚠️ Failed to fetch Up price: {e}")

            try:
                down_resp = requests.get(
                    f"{clob_base}/price?token_id={down_token}&side=BUY",
                    timeout=10
                )
                down_resp.raise_for_status()
                down_price = float(down_resp.json().get("price", 0.50))
            except Exception as e:
                print(f"⚠️ Failed to fetch Down price: {e}")

            total = up_price + down_price

            # === Bybit BTC reference ===
            btc_price = 0
            btc_change = "N/A"
            try:
                bybit_resp = requests.get(bybit_url, params=bybit_params, timeout=8)
                bybit_resp.raise_for_status()
                data = bybit_resp.json().get("result", [{}])[0]
                btc_price = float(data.get("lastPrice", 0))
                btc_change = data.get("price24hPcnt", "N/A")
            except Exception:
                pass

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.4f} | Down: {down_price:.4f} | "
                  f"Total: {total:.4f} | BTC: ${btc_price:,.0f} ({btc_change}) | {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP! Total {total:.4f} ≤ ${cheap_threshold:.2f} — Buy both sides now")
                # TODO: Add your buy logic here
                # await bot.buy(up_token, size, up_price)
                # await bot.buy(down_token, size, down_price)
            else:
                print(f"😌 No cheap opportunity (total {total:.4f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"💥 Outer error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)


def get_clob_tokens(market: dict):
    """Safely extract and parse clobTokenIds (handles string or list)"""
    if not market:
        return []

    raw = market.get("clobTokenIds")
    print(f"🔍 Raw clobTokenIds: {raw} (type: {type(raw)})")

    if not raw:
        return []

    try:
        if isinstance(raw, str):
            # Remove any outer quotes if present and parse JSON
            cleaned = raw.strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            parsed = json.loads(cleaned)
        else:
            parsed = raw

        if isinstance(parsed, list):
            # Convert to clean strings
            return [str(t).strip() for t in parsed if str(t).strip()]
        return []
    except Exception as e:
        print(f"⚠️ Failed to parse clobTokenIds: {e}")
        return []


def fetch_market_by_slug(slug: str):
    """Try multiple Gamma endpoints to fetch the market"""
    urls = [
        f"https://gamma-api.polymarket.com/markets?slug={slug}",
        f"https://gamma-api.polymarket.com/markets/slug/{slug}",
    ]

    for url in urls:
        try:
            print(f"🌐 Fetching: {url}")
            resp = requests.get(url, timeout=15)
            print(f"   → Status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    print(f"   → Market data received for {slug}")
                    return data
        except Exception as e:
            print(f"   → Request failed: {e}")

    print(f"❌ Could not fetch market for slug: {slug}")
    return None


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
