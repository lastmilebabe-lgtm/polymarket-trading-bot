import asyncio
import time
import requests
from datetime import datetime
from src.bot import TradingBot   # This is your main bot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0, max_price: float = 0.40):
    """
    Strategy: Every ~1 minute, check the current BTC 15m market.
    Buy BOTH Up and Down if they are trading at $0.40 or cheaper.
    """
    print("🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ $0.40")

    while True:
        try:
            # Calculate current 15-minute window start (Unix timestamp)
            now = int(time.time())
            window_start = now - (now % 900)  # 900 = 15 minutes

            slug = f"btc-updown-15m-{window_start}"
            url = f"https://gamma-api.polymarket.com/markets?slug={slug}"

            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                await asyncio.sleep(30)
                continue

            data = resp.json()
            if isinstance(data, list) and data:
                market = data[0]
            else:
                market = data

            token_ids = market.get("clobTokenIds", [])
            if len(token_ids) < 2:
                print("⚠️ No token IDs found, waiting...")
                await asyncio.sleep(30)
                continue

            up_token = token_ids[0]
            down_token = token_ids[1]

            # Get current prices to decide if we buy
            tokens_info = market.get("tokens", [])
            up_price = float(tokens_info[0].get("price", 0.5)) if tokens_info else 0.5
            down_price = float(tokens_info[1].get("price", 0.5)) if len(tokens_info) > 1 else 0.5

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {up_price:.3f} | Down: {down_price:.3f} | "
                  f"Window: {slug}")

            orders_to_place = []

            # Buy Up if cheap
            if up_price <= max_price:
                orders_to_place.append({
                    "token_id": up_token,
                    "price": max_price,   # Limit buy at 0.40
                    "size": size,
                    "side": "BUY"
                })
                print(f"✅ Placing BUY Up at ≤ ${max_price}")

            # Buy Down if cheap
            if down_price <= max_price:
                orders_to_place.append({
                    "token_id": down_token,
                    "price": max_price,
                    "size": size,
                    "side": "BUY"
                })
                print(f"✅ Placing BUY Down at ≤ ${max_price}")

            if orders_to_place:
                results = await bot.place_orders(orders_to_place, order_type="GTC")
                for r in results:
                    if r.success:
                        print(f"🎉 Order placed successfully: {r.message}")
                    else:
                        print(f"❌ Order failed: {r.message}")
            else:
                print("😌 No cheap opportunities right now (both > $0.40)")

        except Exception as e:
            print(f"Error in strategy loop: {e}")

        # Check again in ~60 seconds (adjust as needed)
        await asyncio.sleep(60)


# Helper to start the strategy
async def start_strategy():
    bot = TradingBot(config_path="config.yaml")   # Uses your config.yaml
    # Optional: bot = create_bot(...) if you prefer

    await run_btc_15m_cheap_buy_strategy(bot, size=5.0, max_price=0.40)


if __name__ == "__main__":
    asyncio.run(start_strategy())
