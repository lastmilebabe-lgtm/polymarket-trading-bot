import asyncio
import os
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

async def run_15m_simulator():
    coin = os.getenv("COIN", "BTC").upper()
    drop_threshold = float(os.getenv("DROP_THRESHOLD", "0.12"))   # Lowered default - more realistic
    sim_size = float(os.getenv("SIM_SIZE", "2.0"))

    print(f"🟡 15m {coin} Flash-Crash SIMULATOR Started")
    print(f"   Drop threshold: {drop_threshold:.2f} | Sim size: ${sim_size}")
    print(f"   NO REAL TRADES — only watching and logging signals\n")

    # Price history for both sides (longer history = smoother detection)
    price_history = {"up": [], "down": []}

    clob = "https://clob.polymarket.com"

    while True:
        try:
            now = int(time.time())
            # Polymarket 15m markets are usually aligned to 15-minute windows
            window = (now // 900) * 900
            slug = f"{coin.lower()}-updown-15m-{window}"

            # Try current window, then next one if not active yet
            market_resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=10)
            if market_resp.status_code != 200:
                slug = f"{coin.lower()}-updown-15m-{window + 900}"
                market_resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=10)

            if market_resp.status_code != 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No active {coin} 15m market yet... retrying")
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

            # Get best BUY prices
            up_resp = requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=8)
            down_resp = requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=8)

            up_price = float(up_resp.json().get("price", 0.5))
            down_price = float(down_resp.json().get("price", 0.5))
            total = up_price + down_price

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {coin} 15m | "
                  f"UP: {up_price:.4f} | DOWN: {down_price:.4f} | Sum: {total:.4f}")

            # Update history
            price_history["up"].append(up_price)
            price_history["down"].append(down_price)
            if len(price_history["up"]) > 20:
                price_history["up"].pop(0)
                price_history["down"].pop(0)

            # Improved flash-crash detection
            if len(price_history["up"]) >= 6:
                # Average of previous 5 ticks (exclude current to avoid noise)
                up_avg = sum(price_history["up"][-6:-1]) / 5
                down_avg = sum(price_history["down"][-6:-1]) / 5

                up_drop = up_avg - up_price
                down_drop = down_avg - down_price

                # Strong flash crash: one side drops sharply while the opposite moves the other way
                if up_drop > drop_threshold and down_drop < -0.02:   # UP crashed, DOWN rose
                    print(f"🚨 FLASH CRASH DETECTED on UP!")
                    print(f"   Drop from avg: {up_drop:.4f} | Avg was {up_avg:.4f} → Now {up_price:.4f}")
                    print(f"   🟡 SIMULATED: Would BUY UP @ ~{up_price:.4f} | Size ${sim_size}\n")

                elif down_drop > drop_threshold and up_drop < -0.02:  # DOWN crashed, UP rose
                    print(f"🚨 FLASH CRASH DETECTED on DOWN!")
                    print(f"   Drop from avg: {down_drop:.4f} | Avg was {down_avg:.4f} → Now {down_price:.4f}")
                    print(f"   🟡 SIMULATED: Would BUY DOWN @ ~{down_price:.4f} | Size ${sim_size}\n")

                # Bonus: very large move even if opposite isn't perfect
                elif max(up_drop, down_drop) > drop_threshold * 1.5:
                    side = "UP" if up_drop > down_drop else "DOWN"
                    price = up_price if side == "UP" else down_price
                    drop = max(up_drop, down_drop)
                    print(f"⚠️  STRONG MOVE on {side} (possible flash crash)")
                    print(f"   Drop: {drop:.4f} | Price now: {price:.4f}")
                    print(f"   🟡 SIMULATED: Would consider BUY {side} @ ~{price:.4f} | Size ${sim_size}\n")

            await asyncio.sleep(20)  # Check every ~20 seconds

        except Exception as e:
            print(f"💥 Error: {e}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run_15m_simulator())
