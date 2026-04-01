"""
Standalone 15m Crypto Flash-Crash Simulator (NO REAL TRADES)
- Works with your existing discountry repo setup
- Monitors any 15m Up/Down market (BTC/ETH/SOL etc.)
- Detects big probability drops
- Logs "would buy" only — zero risk
- Simple live console output (no fancy TUI)
"""

import asyncio
import os
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# Try to import TradingBot from your repo (fallback to basic if needed)
try:
    from src.bot import TradingBot
    print("✅ Using repo's TradingBot")
except ImportError:
    print("⚠️ TradingBot import failed — using basic mode")
    TradingBot = None

load_dotenv()

async def run_15m_simulator():
    coin = os.getenv("COIN", "BTC").upper()
    drop_threshold = float(os.getenv("DROP_THRESHOLD", "0.30"))
    sim_size = float(os.getenv("SIM_SIZE", "2.0"))

    print(f"🟡 15m {coin} Flash-Crash SIMULATOR Started")
    print(f"   Drop threshold: {drop_threshold:.2f} | Sim size: ${sim_size}")
    print(f"   NO REAL TRADES — only watching and logging signals\n")

    # Basic price history for drop detection (last 10 ticks)
    price_history = {"up": [], "down": []}

    while True:
        try:
            # Find current 15m market
            now = int(time.time())
            window = (now // 900) * 900
            slug = f"{coin.lower()}-updown-15m-{window}"

            market_resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=10)
            if market_resp.status_code != 200:
                # Try next window
                slug = f"{coin.lower()}-updown-15m-{window + 900}"
                market_resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=10)

            if market_resp.status_code != 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No active {coin} 15m market yet...")
                await asyncio.sleep(30)
                continue

            market = market_resp.json()
            if isinstance(market, list) and market:
                market = market[0]

            tokens = market.get("clobTokenIds", [])
            if len(tokens) < 2:
                await asyncio.sleep(30)
                continue

            up_token, down_token = tokens[0], tokens[1]

            # Get current BUY prices (best ask to buy)
            clob = "https://clob.polymarket.com"
            up_price = float(requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=8).json().get("price", 0.5))
            down_price = float(requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=8).json().get("price", 0.5))

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {coin} 15m | "
                  f"UP: {up_price:.4f} | DOWN: {down_price:.4f} | Total: {up_price + down_price:.4f}")

            # Simple flash-crash detection (big drop from recent average)
            for side, price, token in [("up", up_price, up_token), ("down", down_price, down_token)]:
                history = price_history[side]
                history.append(price)
                if len(history) > 10:
                    history.pop(0)

                if len(history) >= 5:
                    avg_recent = sum(history[-5:]) / 5
                    if price < avg_recent - drop_threshold:
                        print(f"🚨 FLASH CRASH DETECTED on {side.upper()}!")
                        print(f"   Drop: {avg_recent - price:.4f} | Price now: {price:.4f}")
                        print(f"   🟡 SIMULATED: Would BUY {side.upper()} @ ~{price:.4f} | Size ${sim_size}\n")

            await asyncio.sleep(20)  # Check every ~20 seconds

        except Exception as e:
            print(f"💥 Error: {e}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run_15m_simulator())
