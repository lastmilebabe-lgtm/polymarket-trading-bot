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

            # Get market from Gamma
            url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                await asyncio.sleep(30)
                continue

            data = resp.json()
            market = data[0] if isinstance(data, list) and data else data

            token_ids = market.get("clobTokenIds", [])
            if len(token_ids) < 2:
                print(f"⚠️ No token IDs found for {slug}")
                await asyncio.sleep(30)
                continue

            up_token = token_ids[0]
            down_token = token_ids[1]

            # === FIXED: Use real prices from outcomePrices ===
            outcome_prices = market.get("outcomePrices", ["0.5", "0.5"])
            up_price = float(outcome_prices[0])
            down_price = float(outcome_prices[1])

            total_cost = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Total: {total_cost:.3f} | Window: {slug}")

            # Buy BOTH only when combined cost is cheap
            if total_cost <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total_cost:.3f} ≤ ${cheap_threshold:.2f} → Buying both sides")

                orders_to_place = [
                    {
                        "token_id": up_token,
                        "price": min(up_price, cheap_threshold),   # limit at threshold
                        "size": size,
                        "side": "BUY"
                    },
                    {
                        "token_id": down_token,
                        "price": min(down_price, cheap_threshold),
                        "size": size,
                        "side": "BUY"
                    }
                ]

                results = await bot.place_orders(orders_to_place, order_type="GTC")
                for r in results:
                    if getattr(r, 'success', False):
                        print(f"🎉 Order placed: {getattr(r, 'message', '')}")
                    else:
                        print(f"❌ Order failed: {getattr(r, 'message', '')}")
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
