import asyncio
import time
import requests
import os
from datetime import datetime
from src.bot import TradingBot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Strategy - Cheap entry ≤ ${cheap_threshold:.2f} | Multiple price methods + exit logic")

    current_slug = None
    up_token = down_token = None

    while True:
        try:
            now = int(time.time())
            # Target next window to avoid closed markets
            window_start = ((now // 900) * 900) + 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"\n🔄 Targeting window: {slug}")
                market = fetch_market(slug)
                if not market or len(market.get("clobTokenIds", [])) < 2:
                    print("⚠️ Market not ready yet...")
                    await asyncio.sleep(30)
                    continue

                tokens = market.get("clobTokenIds", [])
                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug
                print(f"✅ Market ready: {slug}")
                print(f"   Up token: {up_token[:20]}... | Down: {down_token[:20]}...")

                print("⏳ Waiting 20s for liquidity to build...")
                await asyncio.sleep(20)

            # === Try multiple ways to get realistic BUY prices ===
            clob = "https://clob.polymarket.com"
            prices = {}

            # Method 1: /price (your original)
            for side_token, name in [(up_token, "Up"), (down_token, "Down")]:
                resp = requests.get(f"{clob}/price?token_id={side_token}&side=BUY", timeout=10)
                prices[name] = float(resp.json().get("price", 0.5))

            up_price = prices["Up"]
            down_price = prices["Down"]

            # Optional: Try midpoint as backup (uncomment if needed)
            # mid_resp = requests.get(f"{clob}/midpoint?token_id={up_token}", timeout=8)
            # ...

            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | Up: {up_price:.3f} | Down: {down_price:.3f} | Total: {total:.3f} | {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP ENTRY! Total {total:.3f} — Buy BOTH sides (size ~${size})")
                # TODO: await bot.buy(up_token, size) and bot.buy(down_token, size)

            # === Exit logic when one side is almost certain to win ===
            if up_price >= 0.85:
                print(f"🔄 UP strongly favored ({up_price:.3f}) → Exit/sell remaining DOWN side")
                # TODO: bot.sell(down_token, remaining_amount)
            elif down_price >= 0.85:
                print(f"🔄 DOWN strongly favored ({down_price:.3f}) → Exit/sell remaining UP side")
                # TODO: bot.sell(up_token, remaining_amount)

            # Leftover handling note: When new window starts, sell any remaining from previous

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")

        await asyncio.sleep(50)


def fetch_market(slug: str):
    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
    print(f"🌐 Fetching Gamma: {url}")
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
        print(f"   → Failed: {e}")
        return None


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
