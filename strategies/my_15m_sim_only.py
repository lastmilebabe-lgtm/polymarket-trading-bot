import asyncio
import os
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

async def run_15m_simulator():
    coin = os.getenv("COIN", "BTC").upper()
    drop_threshold = float(os.getenv("DROP_THRESHOLD", "0.12"))
    sim_size = float(os.getenv("SIM_SIZE", "2.0"))

    print("=" * 60)
    print("🟡 15m BTC Flash-Crash SIMULATOR (PURE SIMULATION MODE)")
    print("   NO REAL TRADES — Only monitoring & logging signals")
    print(f"   Drop threshold: {drop_threshold:.2f} | Sim size: ${sim_size}")
    print("=" * 60 + "\n")

    price_history = {"up": [], "down": []}
    clob = "https://clob.polymarket.com"
    last_print_time = 0
    last_banner_time = time.time()

    while True:
        try:
            now = int(time.time())
            window = (now // 900) * 900
            slug = f"{coin.lower()}-updown-15m-{window}"

            market_resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=10)
            if market_resp.status_code != 200:
                slug = f"{coin.lower()}-updown-15m-{window + 900}"
                market_resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=10)

            if market_resp.status_code != 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for new {coin} 15m market...")
                await asyncio.sleep(30)
                continue

            market = market_resp.json()
            if isinstance(market, list) and market:
                market = market[0]

            tokens = market.get("clobTokenIds", [])
            if len(tokens) < 2:
                await asyncio.sleep(30)
                continue

            up_token = tokens[0]
            down_token = tokens[1]

            up_price = float(requests.get(f"{clob}/price?token_id={up_token}&side=BUY", timeout=8).json().get("price", 0.5))
            down_price = float(requests.get(f"{clob}/price?token_id={down_token}&side=BUY", timeout=8).json().get("price", 0.5))
            total = up_price + down_price

            # Update history
            price_history["up"].append(up_price)
            price_history["down"].append(down_price)
            if len(price_history["up"]) > 20:
                price_history["up"].pop(0)
                price_history["down"].pop(0)

            # Print price only if it changed or every 60 seconds
            current_time = time.time()
            if abs(up_price - 0.5) > 0.005 or abs(down_price - 0.5) > 0.005 or (current_time - last_print_time > 60):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {coin} 15m | "
                      f"UP: {up_price:.4f} | DOWN: {down_price:.4f} | Sum: {total:.4f}")
                last_print_time = current_time

            # Flash-crash detection
            if len(price_history["up"]) >= 6:
                up_avg = sum(price_history["up"][-6:-1]) / 5
                down_avg = sum(price_history["down"][-6:-1]) / 5

                up_drop = up_avg - up_price
                down_drop = down_avg - down_price

                if up_drop > drop_threshold and down_drop < -0.02:
                    print(f"🚨 FLASH CRASH DETECTED on UP!")
                    print(f"   Drop: {up_drop:.4f} | Avg: {up_avg:.4f} → Now: {up_price:.4f}")
                    print(f"   🟡 SIMULATED BUY UP @ ~{up_price:.4f} | Size ${sim_size}\n")

                elif down_drop > drop_threshold and up_drop < -0.02:
                    print(f"🚨 FLASH CRASH DETECTED on DOWN!")
                    print(f"   Drop: {down_drop:.4f} | Avg: {down_avg:.4f} → Now: {down_price:.4f}")
                    print(f"   🟡 SIMULATED BUY DOWN @ ~{down_price:.4f} | Size ${sim_size}\n")

                elif max(up_drop, down_drop) > drop_threshold * 1.5:
                    side = "UP" if up_drop > down_drop else "DOWN"
                    price = up_price if side == "UP" else down_price
                    print(f"⚠️ STRONG MOVE on {side}")
                    print(f"   Drop: {max(up_drop, down_drop):.4f} | Price: {price:.4f}")
                    print(f"   🟡 SIMULATED consider BUY {side} @ ~{price:.4f}\n")

            # Show simulation reminder every 5 minutes
            if current_time - last_banner_time > 300:
                print("   [SIMULATION MODE] — No real trades are being executed\n")
                last_banner_time = current_time

            await asyncio.sleep(20)

        except Exception as e:
            print(f"💥 Error: {e}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run_15m_simulator())
