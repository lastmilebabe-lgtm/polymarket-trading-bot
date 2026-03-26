import asyncio
import time
import requests
import os
from datetime import datetime
from src.bot import TradingBot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Strategy Started - Cheap entry ≤ ${cheap_threshold:.2f}")
    print("   Exit weak side when one dominates | Handle previous window leftovers")

    current_slug = None
    up_token = down_token = None
    previous_tokens = None

    while True:
        try:
            now = int(time.time())
            # Target the NEXT window to avoid closed markets
            window_start = ((now // 900) * 900) + 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"\n🔄 Targeting next window: {slug}")
                market = fetch_market(slug)

                if not market or len(market.get("clobTokenIds", [])) < 2:
                    print("⚠️ Market not ready yet...")
                    await asyncio.sleep(30)
                    continue

                tokens = market.get("clobTokenIds", [])
                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug

                print(f"✅ New market ready: {slug}")
                print(f"   Up: {up_token[:20]}... | Down: {down_token[:20]}...")

                # Cleanup leftovers from previous window
                if previous_tokens:
                    print("🧹 Cleaning leftovers from previous market...")
                    # TODO: bot.sell_remaining(previous_tokens)
                previous_tokens = (up_token, down_token)

                # Give the order book a moment to populate
                print("⏳ Waiting 15s for order book to build...")
                await asyncio.sleep(15)

            # Fetch BUY prices with better error visibility
            clob = "https://clob.polymarket.com"
            up_resp = requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=10)
            down_resp = requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=10)

            up_price = float(up_resp.json().get("price", 0.5))
            down_price = float(down_resp.json().get("price", 0.5))
            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | Up: {up_price:.3f} | Down: {down_price:.3f} | Total: {total:.3f} | {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP! Total {total:.3f} — Buy BOTH sides")
                # TODO: bot.buy both

            # Exit logic when one side is obviously winning
            if up_price >= 0.85:
                print(f"🔄 UP dominating ({up_price:.3f}) → Exit/sell remaining DOWN")
                # TODO: bot.sell(down_token)
            elif down_price >= 0.85:
                print(f"🔄 DOWN dominating ({down_price:.3f}) → Exit/sell remaining UP")
                # TODO: bot.sell(up_token)

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")

        await asyncio.sleep(50)


def fetch_market(slug: str):
    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
    print(f"🌐 Fetching {url}")
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            print(f"   → Status {resp.status_code}")
            return None
        data = resp.json()
        if isinstance(data, list) and data:
            data = data[0]
        print(f"   → Market data received")
        return data
    except Exception as e:
        print(f"   → Fetch failed: {e}")
        return None


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
