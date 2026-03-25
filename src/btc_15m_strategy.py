import asyncio
import time
import requests
import os
from datetime import datetime
from src.bot import TradingBot


async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ ${cheap_threshold:.2f} (size={size})")

    while True:
        try:
            # Current 15-minute window
            now = int(time.time())
            window_start = now - (now % 900)
            slug = f"btc-updown-15m-{window_start}"

            # Get market data from Gamma
            gamma_url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
            resp = requests.get(gamma_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and data:
                market = data[0]
            else:
                market = data

            clob_tokens = market.get("clobTokenIds", [])
            if len(clob_tokens) < 2:
                print(f"⚠️ No clobTokenIds for {slug}")
                await asyncio.sleep(30)
                continue

            up_token = clob_tokens[0]
            down_token = clob_tokens[1]

            # === REAL PRICE FETCHING (this fixes the 0.500 issue) ===
            # First try Gamma outcomePrices (fast & reliable for 15m markets)
            outcome_prices = market.get("outcomePrices", ["0.5", "0.5"])
            up_price = float(outcome_prices[0])
            down_price = float(outcome_prices[1])

            # Optional: Try CLOB for more accurate BUY prices
            try:
                clob_url = "https://clob.polymarket.com"
                up_r = requests.get(f"{clob_url}/price?token_id={up_token}&side=BUY", timeout=6)
                down_r = requests.get(f"{clob_url}/price?token_id={down_token}&side=BUY", timeout=6)
                up_price = float(up_r.json().get("price", up_price))
                down_price = float(down_r.json().get("price", down_price))
            except Exception:
                pass  # fallback to Gamma prices is fine

            total_cost = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Total: {total_cost:.3f} | Window: {slug}")

            # Buy both sides only if combined cost is cheap
            if total_cost <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total_cost:.3f} ≤ ${cheap_threshold:.2f} → Buying both sides")

                orders = [
                    {"token_id": up_token,   "price": min(up_price, cheap_threshold),   "size": size, "side": "BUY"},
                    {"token_id": down_token, "price": min(down_price, cheap_threshold), "size": size, "side": "BUY"}
                ]

                results = await bot.place_orders(orders, order_type="GTC")
                for r in results:
                    status = "🎉 Success" if getattr(r, 'success', False) else "❌ Failed"
                    print(f"{status}: {getattr(r, 'message', 'No message')}")
            else:
                print(f"😌 No cheap opportunities right now (total {total_cost:.3f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"Error in strategy loop: {e}")

        await asyncio.sleep(60)


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size=size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
