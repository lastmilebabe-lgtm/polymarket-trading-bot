import asyncio
import time
import requests
import os
from datetime import datetime

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ ${cheap_threshold:.2f}")

    current_slug = None
    up_token = down_token = None

    while True:
        try:
            now = int(time.time())
            # Better window calculation: align to current 15-min boundary (UTC)
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 New window detected: {slug} (timestamp {window_start})")
                
                # Improved: use the more reliable /markets/slug/ endpoint
                gamma_url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
                print(f"🌐 Fetching from: {gamma_url}")
                
                gamma_resp = requests.get(gamma_url, timeout=12)
                gamma_resp.raise_for_status()
                market = gamma_resp.json()

                # Some responses wrap in a list, some don't
                if isinstance(market, list) and market:
                    market = market[0]

                tokens = market.get("clobTokenIds", [])
                print(f"🔍 Market found → Tokens: {tokens[:2] if tokens else 'NONE'}")

                if len(tokens) < 2:
                    print("⚠️ Not enough tokens (market may not be active yet). Waiting...")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]   # Usually "Yes" / Up
                down_token = tokens[1] # Usually "No" / Down
                current_slug = slug
                print(f"✅ Tokens saved → Up: {up_token[:12]}... | Down: {down_token[:12]}...")

            # === Fetch current BUY prices from CLOB ===
            clob = "https://clob.polymarket.com"
            
            up_resp = requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=10)
            down_resp = requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=10)

            up_resp.raise_for_status()
            down_resp.raise_for_status()

            up_price = float(up_resp.json().get("price", 0.50))
            down_price = float(down_resp.json().get("price", 0.50))
            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Total: {total:.3f} | Window: {slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total:.3f} ≤ ${cheap_threshold:.2f} — Buying both sides")
                # TODO: Add your actual buy order logic here using the bot
                # e.g. await bot.place_order(up_token, size, up_price) etc.
            else:
                print(f"😌 No cheap opportunities right now (total {total:.3f} > ${cheap_threshold:.2f})")

        except requests.exceptions.HTTPError as e:
            print(f"💥 HTTP Error {e.response.status_code if e.response else '??'}: {e}")
            if "404" in str(e):
                print("   → Market not found yet (try next window)")
        except requests.exceptions.Timeout:
            print("💥 Timeout fetching Polymarket API — network slow?")
        except Exception as e:
            print(f"💥 Unexpected error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)  # Check every 60 seconds (you had 10s before — 60s is plenty)
