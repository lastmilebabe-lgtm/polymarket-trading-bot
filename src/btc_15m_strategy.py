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
            window_start = now - (now % 900)
            slug = f"btc-updown-15m-{window_start}"

            if slug != current_slug:
                print(f"🔄 Fetching tokens for new window: {slug}")
                gamma_resp = requests.get(f"https://gamma-api.polymarket.com/markets?slug={slug}", timeout=10)
                gamma_resp.raise_for_status()
                data = gamma_resp.json()
                market = data[0] if isinstance(data, list) and data else data

                tokens = market.get("clobTokenIds", [])
                print(f"🔍 Found {len(tokens)} tokens: {tokens[:2] if tokens else 'NONE'}")

                if len(tokens) < 2:
                    print("⚠️ Not enough tokens — waiting")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug

            # Real CLOB calls
            clob = "https://clob.polymarket.com"
            up_resp = requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=8)
            down_resp = requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=8)

            up_price = float(up_resp.json().get("price", 0.5))
            down_price = float(down_resp.json().get("price", 0.5))
            total = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | Up: {up_price:.3f} | Down: {down_price:.3f} | Total: {total:.3f} | Window: {slug}")

            if total <= cheap_threshold:
                print(f"🚀 CHEAP! Buying both at total {total:.3f}")
                # your order code here
            else:
                print(f"😌 No cheap opportunities (total {total:.3f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"💥 Error: {type(e).__name__}: {e}")

        await asyncio.sleep(10)

async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size)

if __name__ == "__main__":
    asyncio.run(start_strategy())
