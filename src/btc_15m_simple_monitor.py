import asyncio
import time
import requests
import os
from datetime import datetime

async def main():
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.98"))
    print(f"🚀 Simple BTC 15m Monitor Started - Cheap if total BUY price ≤ ${cheap_threshold:.2f}")
    print("Goal: Buy both sides when cheap | Exit weak side when one dominates")

    current_slug = None

    while True:
        try:
            now = int(time.time())
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"\n🔄 Checking slug: {slug} (window start: {window_start})")
                market = fetch_market(slug)

                # Fallback to next window if current not ready (very common)
                if not market or len(market.get("clobTokenIds", [])) < 2:
                    next_start = window_start + 900
                    next_slug = f"btc-updown-15m-{next_start}"
                    print(f"⚠️ Current not active → Trying next: {next_slug}")
                    market = fetch_market(next_slug)
                    slug = next_slug

                if not market or len(market.get("clobTokenIds", [])) < 2:
                    print("⚠️ No valid market yet. Waiting...")
                    await asyncio.sleep(30)
                    continue

                tokens = market.get("clobTokenIds", [])
                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug
                print(f"✅ Market ready: {slug}")
                print(f"   Up token: {up_token[:20]}... | Down token: {down_token[:20]}...")

            # Fetch real BUY prices
            clob = "https://clob.polymarket.com"
            up_price = float(requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=10).json().get("price", 0.5))
            down_price = float(requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=10).json().get("price", 0.5))
            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | Up: {up_price:.3f} | Down: {down_price:.3f} | Total: {total:.3f} | {current_slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total:.3f} — Buy both sides here")
                # TODO: Add your TradingBot buy calls

            # Dynamic exit hint (what you wanted)
            if up_price >= 0.85:
                print(f"🔄 UP strongly favored ({up_price:.3f}) → Consider exiting/selling Down side")
            elif down_price >= 0.85:
                print(f"🔄 DOWN strongly favored ({down_price:.3f}) → Consider exiting/selling Up side")

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")

        await asyncio.sleep(50)  # Balanced polling speed


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
        print(f"   → Success for {slug}")
        return data
    except Exception as e:
        print(f"   → Fetch failed: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
