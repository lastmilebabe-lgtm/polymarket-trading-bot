import asyncio
import json
import os
import time
import requests
from datetime import datetime
import websockets
from src.bot import TradingBot

async def run_btc_15m_cheap_buy_strategy(bot: TradingBot, size: float = 5.0):
    cheap_threshold = float(os.environ.get("CHEAP_THRESHOLD", "0.40"))
    print(f"🚀 BTC 15m Cheap Buy Strategy Started - Buying both sides ≤ ${cheap_threshold:.2f} (size={size})")

    # WebSocket variables
    ws = None
    current_slug = None
    up_token = down_token = None
    live_up_buy_price = 0.5
    live_down_buy_price = 0.5

    async def connect_and_subscribe():
        nonlocal ws
        try:
            ws = await websockets.connect("wss://ws-subscriptions-clob.polymarket.com/ws/market", ping_interval=20)
            print("✅ Connected to Polymarket CLOB WebSocket")

            if up_token and down_token:
                sub_msg = {
                    "assets_ids": [up_token, down_token],
                    "type": "market",
                    "custom_feature_enabled": True
                }
                await ws.send(json.dumps(sub_msg))
                print(f"📡 Subscribed to tokens: {up_token[:8]}... and {down_token[:8]}...")
        except Exception as e:
            print(f"WebSocket connect error: {e}")
            ws = None

    while True:
        try:
            now = int(time.time())
            window_start = now - (now % 900)
            slug = f"btc-updown-15m-{window_start}"

            # Refresh tokens + resubscribe when window changes
            if slug != current_slug:
                print(f"🔄 New window: {slug}")
                resp = requests.get(f"https://gamma-api.polymarket.com/markets?slug={slug}", timeout=10)
                resp.raise_for_status()
                data = resp.json()
                market = data[0] if isinstance(data, list) and data else data

                tokens = market.get("clobTokenIds", [])
                if len(tokens) < 2:
                    print("⚠️ No tokens found")
                    await asyncio.sleep(30)
                    continue

                up_token = tokens[0]
                down_token = tokens[1]
                current_slug = slug

                if ws:
                    await ws.close()
                await connect_and_subscribe()

            # Process any incoming WebSocket messages (non-blocking)
            if ws:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    msg = json.loads(message)

                    # Update live buy prices from best_ask (what you pay to BUY)
                    if msg.get("type") == "best_bid_ask" or "best_ask" in str(msg):
                        # The exact structure varies — print first few to see
                        print("📥 WS update:", msg)  # Remove after debugging

                        # Typical fields: best_ask_price, asset_id, etc.
                        asset = msg.get("asset_id") or msg.get("token_id")
                        if asset == up_token:
                            live_up_buy_price = float(msg.get("best_ask_price", live_up_buy_price))
                        elif asset == down_token:
                            live_down_buy_price = float(msg.get("best_ask_price", live_down_buy_price))

                except asyncio.TimeoutError:
                    pass  # No message this tick — normal

            total_cost = live_up_buy_price + live_down_buy_price

            print(f"📊 {datetime.now().strftime('%H:%M:%S')} | "
                  f"Up: {live_up_buy_price:.3f} | Down: {live_down_buy_price:.3f} | "
                  f"Total: {total_cost:.3f} | Window: {slug}")

            if total_cost <= cheap_threshold:
                print(f"🚀 CHEAP OPPORTUNITY! Total {total_cost:.3f} ≤ ${cheap_threshold:.2f} → Buying both!")

                orders = [
                    {"token_id": up_token, "price": min(live_up_buy_price, cheap_threshold), "size": size, "side": "BUY"},
                    {"token_id": down_token, "price": min(live_down_buy_price, cheap_threshold), "size": size, "side": "BUY"}
                ]
                results = await bot.place_orders(orders, order_type="GTC")
                for r in results:
                    status = "🎉 Success" if getattr(r, 'success', False) else "❌ Failed"
                    print(f"{status}: {getattr(r, 'message', '')}")

            else:
                print(f"😌 No cheap opportunities right now (total {total_cost:.3f} > ${cheap_threshold:.2f})")

        except Exception as e:
            print(f"Error: {e}")
            if ws:
                await ws.close()
                ws = None

        await asyncio.sleep(5)  # Check logic every 5s, WebSocket runs in background


async def start_strategy():
    bot = TradingBot(config_path="config.yaml")
    size = float(os.environ.get("POLY_DEFAULT_SIZE", 5.0))
    await run_btc_15m_cheap_buy_strategy(bot, size=size)


if __name__ == "__main__":
    asyncio.run(start_strategy())
