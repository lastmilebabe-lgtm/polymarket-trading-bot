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
            window_start = (now // 900) * 900
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 Checking window: {slug} (start: {window_start})")

                # Try direct slug first (fastest when it works)
                gamma_url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
                print(f"🌐 Trying direct slug: {gamma_url}")

                gamma_resp = requests.get(gamma_url, timeout=12)
                
                if gamma_resp.status_code == 200:
                    market = gamma_resp.json()
                else:
                    print(f"⚠️ Direct slug {gamma_resp.status_code} — falling back to search")
                    # Fallback: search all markets for BTC 15m
                    search_url = "https://gamma-api.polymarket.com/markets?limit=50&active=true"
                    search_resp = requests.get(search_url, timeout=12)
                    search_resp.raise_for_status()
                    markets = search_resp.json() if isinstance(search_resp.json(), list) else []
                    
                    market = None
                    for m in markets:
                        m_slug = m.get("slug", "")
                        if m_slug.startswith("btc-updown-15m-"):
                            market = m
                            slug = m_slug  # update to the actual active one
                            print(f"✅ Found active BTC 15m market via search: {slug}")
                            break
                    
                    if not market:
                        print("⚠️ No active BTC 15m market found yet. Waiting...")
                        await asyncio.sleep(30)
                        continue

                # Handle list wrapper if any
                if isinstance(market, list) and market:
                    market = market[0]

                tokens = market.get("clobTokenIds", [])
                print(f"🔍 Tokens found: {len(tokens)} → {[t[:12] + '...' for t in tokens[:2]] if tokens else 'NONE'}")

                if len(tokens) < 2:
                    print(f"⚠️ Market {slug} has insufficient tokens. Waiting for next cycle...")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug
                print(f"✅ SUCCESS! Tokens saved for {slug}")

            # Fetch BUY prices
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
                print(f"🚀 CHEAP OPPORTUNITY! Total {total:.3f} ≤ ${cheap_threshold:.2f} — Buy both")
                # TODO: place orders here with bot
            else:
                print(f"😌 No cheap opportunities (total {total:.3f} > ${cheap_threshold:.2f})")

        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, 'status_code', '??')
            print(f"💥 HTTP {status} — Market not ready or endpoint issue")
        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
