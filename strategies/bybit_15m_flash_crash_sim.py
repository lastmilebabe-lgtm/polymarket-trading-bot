import asyncio
import os
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

async def run_bybit_flash_simulator():
    coin = os.getenv("COIN", "BTC").upper()
    drop_threshold_pct = float(os.getenv("DROP_THRESHOLD_PCT", "0.8"))  # % drop from recent avg (e.g. 0.8 = 0.8%)
    sim_size = float(os.getenv("SIM_SIZE", "2.0"))

    print("=" * 80)
    print("⚡ BYBIT FAST FLASH-CRASH SIMULATOR — PURE SIMULATION MODE")
    print(f"   Coin: {coin} | Drop threshold: {drop_threshold_pct}% from recent avg")
    print("   NO REAL TRADES — Only logging potential buy signals on sharp drops")
    print("   Pulling real-time price from Bybit (much faster than Polymarket)")
    print("=" * 80 + "\n")

    # Price history (in USD)
    price_history = []
    bybit_url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={coin}USDT"
    last_print_time = 0
    last_banner_time = time.time()

    while True:
        try:
            # Get current BTC price from Bybit
            resp = requests.get(bybit_url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                    ticker = data["result"]["list"][0]
                    current_price = float(ticker["lastPrice"])
                else:
                    current_price = None
            else:
                current_price = None

            if current_price is None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to fetch Bybit price, retrying...")
                await asyncio.sleep(10)
                continue

            # Update history
            price_history.append(current_price)
            if len(price_history) > 30:  # ~last 5-10 minutes depending on poll rate
                price_history.pop(0)

            current_time = time.time()

            # Print price regularly
            if current_time - last_print_time > 15:  # More frequent updates
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Bybit {coin} | Price: ${current_price:,.2f} "
                      f"({'↑' if len(price_history) > 1 and current_price > price_history[-2] else '↓' if len(price_history) > 1 and current_price < price_history[-2] else '→'})")

                last_print_time = current_time

            # Flash-crash detection (sharp drop from recent average)
            if len(price_history) >= 8:
                recent_avg = sum(price_history[-8:-1]) / 7   # average of previous ticks
                drop_pct = ((recent_avg - current_price) / recent_avg) * 100

                if drop_pct > drop_threshold_pct:
                    print(f"🚨 FLASH CRASH DETECTED on {coin}!")
                    print(f"   Drop: {drop_pct:.2f}% | Avg was ${recent_avg:,.2f} → Now ${current_price:,.2f}")
                    print(f"   🟡 SIMULATED: Would BUY {coin} @ ~${current_price:,.2f} | Size ${sim_size}\n")

            # Reminder every 5 min
            if current_time - last_banner_time > 300:
                print(f"   [SIMULATION MODE ONLY — {datetime.now().strftime('%H:%M')}] No real trades executed\n")
                last_banner_time = current_time

            await asyncio.sleep(8)  # Fast polling — every 8 seconds

        except Exception as e:
            print(f"💥 Error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_bybit_flash_simulator())
