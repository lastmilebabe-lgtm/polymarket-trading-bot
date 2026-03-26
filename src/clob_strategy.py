import asyncio
import time
import requests
import os
import json
from datetime import datetime
from src.bot import TradingBot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy (CLOB + Bybit) Started - Threshold ≤ ${cheap_threshold:.2f}")

    current_slug = None
    up_token = down_token = None
    clob_base = "https://clob.polymarket.com"

    # Bybit reference
    bybit_url = "https://api.bybit.com/v5/market/tickers"
    bybit_params = {"category": "spot", "symbol": "BTCUSDT"}

    while True:
        try:
            now = int(time.time())
            # Current 15m window start
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"\n🔄 New window check: {slug}")

                # Try current, then next window
                market = fetch_market(slug)
                if not market or not extract_clob_tokens(market):
                    next_slug = f"btc-updown-15m-{window_start + 900}"
                    print(f"⚠️ Current not ready → Trying next: {next_slug}")
                    market = fetch_market(next_slug)
                    slug = next_slug

                tokens = extract_clob_tokens(market)
                if len(tokens) < 2:
                    print("⚠️ No valid tokens yet. Waiting 30s...")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug

                print(f"✅ Active market ready: {slug}")
                print(f"   Up token   : {up_token[:20]}...{up_token[-10:]}")
                print(f"   Down token : {down_token[:20]}...{down_token[-10:]}")

            # === Get BUY prices from CLOB ===
            up_price = down_price = 0.50

            # Try batch /prices first (more reliable)
            try:
                payload = [
                    {"token_id": up_token, "side": "BUY"},
                    {"token_id": down_token, "side": "BUY"}
                ]
                resp = requests.post(f"{clob_base}/prices", json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    up_price = float(data.get(up_token, {}).get("BUY", 0.50))
                    down_price = float(data.get(down_token, {}).get("BUY", 0.50))
                    print(f"   Batch BUY prices → Up: {up_price:.4f} | Down: {down_price:.4f}")
                else:
                    print(f"   Batch /prices returned {resp.status_code}")
            except Exception as e:
                print(f"   Batch prices failed: {e}")

            total = up_price + down_price

            # Bybit BTC context
            btc_price = 0
            btc_change = "N/A"
            try:
                bybit_resp = requests.get(bybit_url, params=bybit_params, timeout=8)
                if bybit_resp.status_code == 200:
                    data = bybit_resp.json().get("result", [{}])[0]
                    btc_price = float(data.get("lastPrice", 0))
                    btc_change = data.get("price24hPcnt", "N/A")
            except:
                pass

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.4f} | Down: {down_price:.4f} | Total: {total:.4f} | "
                  f"BTC: ${btc_price:,.0f} ({btc_change}) | {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP! Total {total:.4f} — Buy both sides")
                # TODO: Add your buy logic here
                # await bot.buy(up_token, size, up_price)   # example
                # await bot.buy(down_token, size, down_price)
            else:
                print(f"😌 Total {total:.4f} above threshold")

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(45)  # Slightly faster polling


def fetch_market(slug: str):
    """Try multiple reliable endpoints"""
    urls = [
        f"https://gamma-api.polymarket.com/markets?slug={slug}",
        f"https://gamma-api.polymarket.com/markets/slug/{slug}",
        f"https://gamma-api.polymarket.com/events/slug/{slug}",
    ]

    for url in urls:
        try:
            print(f"🌐 Fetching {url}")
            resp = requests.get(url, timeout=12)
            print(f"   → Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    print(f"   → Market data loaded")
                    return data
        except Exception as e:
            print(f"   → Failed: {e}")
    print(f"❌ No market data for {slug}")
    return None


def extract_clob_tokens(market: dict):
    """Most robust parser used by working bots"""
    if not market:
        return []

    raw = market.get("clobTokenIds")
    print(f"🔍 Raw clobTokenIds: {repr(raw)[:200]}... (type: {type(raw)})")

    if not raw:
        return []

    try:
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]

        if isinstance(raw, str):
            # Clean outer quotes and parse JSON
            cleaned = raw.strip().strip('"').strip("'")
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]

        # Fallback regex for long numbers
        import re
        numbers = re.findall(r'\d{30,}', str(raw))
        if len(numbers) >= 2:
            return numbers[:2]
    except Exception as e:
        print(f"⚠️ Parse error: {e}")

    return []


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
