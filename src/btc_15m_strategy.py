import asyncio
import time
import requests
from datetime import datetime
from src.bot import TradingBot


async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0, max_price: float = 0.40):
    """
    BTC 15m Cheap Buy Strategy
    - Fetches REAL live BUY prices from Polymarket CLOB
    - Buys BOTH Up and Down only if their combined cost <= max_price (default 0.40)
    """
    print("🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ $0.40")

    # Load threshold from env (so you can change it on Railway without code edit)
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", max_price))

    while True:
        try:
            now = int(time.time())
            window_start = now - (now % 900)          # Current 15-min window
            slug = f"btc-updown-15m-{window_start}"

            # 1. Get market info + clobTokenIds from Gamma
            gamma_url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
            resp = requests.get(gamma_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and data:
                market = data[0]
            else:
                market = data

            token_ids = market.get("clobTokenIds", [])
            if len(token_ids) < 2:
                print(f"⚠️ No token IDs found for {slug}")
                await asyncio.sleep(30)
                continue

            up_token = token_ids[0]
            down_token = token_ids[1]

            # 2. Fetch REAL current BUY prices from CLOB (this was the broken part)
            clob_url = "https://clob.polymarket.com"

            up_resp = requests.get(f"{clob_url}/price?token_id={up_token}&side=BUY", timeout=8)
            down_resp = requests.get(f"{clob_url}/price?token_id={down_token}&side=BUY", timeout=8)

            up_price = float(up_resp.json().get("price", 0.5))
            down_price = float(down_resp.json().get("price", 0.5))

            total_cost = up_price + down_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Total: {total_cost:.3f} | Window: {slug}")

            # === Decision logic: Buy BOTH only if combined cost is cheap ===
            if total_cost <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total_cost:.3f} ≤ ${cheap_threshold:.2f} → Buying both sides")

                orders_to_place = [
                    {
                        "token_id": up_token,
                        "price": up_price,      # or use cheap_threshold if you want to cap it
                        "size": size,
                        "side": "BUY"
                    },
                    {
                        "token_id": down_token,
                        "price": down_price,
                        "size": size,
                        "side": "BUY"
                    }
                ]

                results = await bot.place_orders(orders_to_place, order_type="GTC")
                for r in results:
                    if r.success:
                        print(f"🎉 Order placed: {r.message}")
                    else:
                        print(f"❌ Order failed: {r.message}")

            else:
                print(f"😌 No cheap opportunities right now (total {total_cost:.3f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"Error in strategy loop: {e}")

        await asyncio.sleep(60)   # Check every 60 seconds


# Helper to start the strategy
async def start_strategy():
    import os
    bot = TradingBot(config_path="config.yaml")

    # You can override size and threshold here if you want
    await run_btc_15m_cheap_buy_strategy(
        bot,
        size=float(os.environ.get("POLY_DEFAULT_SIZE", 5.0)),
        max_price=0.40
    )


if __name__ == "__main__":
    asyncio.run(start_strategy())
