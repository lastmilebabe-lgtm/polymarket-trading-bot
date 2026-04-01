"""
My Flash Crash Simulation Strategy (Safe Dry-Run Only)
- Monitors 15-minute Up/Down markets for any crypto (BTC, ETH, SOL, etc.)
- Detects sudden probability drops via real-time WebSocket
- Logs simulated buys only — NO REAL TRADES
- Shows live TUI status with orderbook, countdown, and "would-trade" events
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from lib.console import Colors, format_countdown
from strategies.base import BaseStrategy, StrategyConfig
from src.bot import TradingBot
from src.websocket_client import OrderbookSnapshot


@dataclass
class MyFlashCrashSimConfig(StrategyConfig):
    """Config for simulation-only flash crash strategy."""
    drop_threshold: float = 0.30   # Probability drop to trigger "signal"
    sim_size: float = 2.0          # Simulated trade size in USDC
    price_lookback_seconds: int = 30


class MyFlashCrashSimStrategy(BaseStrategy):
    """
    Simulation-only Flash Crash Strategy.
    Perfect for testing on Railway without risking money.
    """

    def __init__(self, bot: TradingBot, config: MyFlashCrashSimConfig):
        super().__init__(bot, config)
        self.sim_config = config
        self.simulation_mode = True

        # Ensure price tracker uses our threshold
        if hasattr(self.prices, 'drop_threshold'):
            self.prices.drop_threshold = config.drop_threshold

        print(f"🟡 SIMULATION MODE ENABLED — No real trades will ever be placed")
        print(f"   Monitoring {config.coin.upper()} 15m markets | Drop threshold: {config.drop_threshold:.2f}")

    async def on_book_update(self, snapshot: OrderbookSnapshot) -> None:
        """Handle real-time orderbook updates (price recording happens in base)."""
        pass  # Base class already handles history for detection

    async def on_tick(self, prices: Dict[str, float]) -> None:
        """Check for flash crash signals on each tick — simulate only."""
        if not hasattr(self, 'positions') or not self.positions.can_open_position:
            return

        # Detect potential flash crash (relies on base class logic)
        event = getattr(self.prices, 'detect_flash_crash', lambda: None)()
        if not event:
            return

        side = event.side.upper()
        drop = event.drop
        old_p = event.old_price
        new_p = event.new_price
        current_price = prices.get(event.side, 0.0)

        self.log(
            f"FLASH CRASH DETECTED: {side} dropped {drop:.2f} "
            f"({old_p:.2f} → {new_p:.2f})",
            "trade"
        )

        if current_price > 0:
            self.log(
                f"🟡 SIMULATED BUY: Would BUY {side} @ ~{current_price:.4f} | "
                f"Size: ${self.sim_config.sim_size:.1f} | Time: {datetime.now().strftime('%H:%M:%S')}",
                "trade"
            )

            # Optional: log to a file for later review
            try:
                with open("sim_trades.log", "a") as f:
                    f.write(
                        f"{datetime.now()} | {self.config.coin.upper()} | "
                        f"BUY_{side} | Price:{current_price:.4f} | Size:${self.sim_config.sim_size}\n"
                    )
            except Exception:
                pass  # ignore log file errors

    def render_status(self, prices: Dict[str, float]) -> None:
        """Live TUI display (same style as original, but clearly simulation)."""
        lines = []

        ws_status = f"{Colors.GREEN}WS LIVE{Colors.RESET}" if getattr(self, 'is_connected', False) else f"{Colors.YELLOW}SIM MODE{Colors.RESET}"
        countdown = self._get_countdown_str() if hasattr(self, '_get_countdown_str') else "--:--"
        stats = self.positions.get_stats() if hasattr(self.positions, 'get_stats') else {'trades_closed': 0, 'total_pnl': 0.0}

        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
        lines.append(
            f"{Colors.CYAN}[{self.config.coin.upper()} 15m]{Colors.RESET} [{ws_status}] "
            f"Ends: {countdown} | Sim Trades: {stats['trades_closed']} | Sim PnL: ${stats['total_pnl']:+.2f}"
        )
        lines.append(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        # Orderbook (Up | Down)
        up_ob = self.market.get_orderbook("up") if hasattr(self.market, 'get_orderbook') else None
        down_ob = self.market.get_orderbook("down") if hasattr(self.market, 'get_orderbook') else None

        lines.append(f"{Colors.GREEN}{'UP':^39}{Colors.RESET}|{Colors.RED}{'DOWN':^39}{Colors.RESET}")
        lines.append(f"{'Bid':>9} {'Size':>9} | {'Ask':>9} {'Size':>9}|{'Bid':>9} {'Size':>9} | {'Ask':>9} {'Size':>9}")
        lines.append("-" * 80)

        # Show top 5 levels (simplified)
        for i in range(5):
            up_bid = f"{up_ob.bids[i].price:>9.4f} {up_ob.bids[i].size:>9.1f}" if up_ob and i < len(up_ob.bids) else f"{'--':>9} {'--':>9}"
            up_ask = f"{up_ob.asks[i].price:>9.4f} {up_ob.asks[i].size:>9.1f}" if up_ob and i < len(up_ob.asks) else f"{'--':>9} {'--':>9}"
            down_bid = f"{down_ob.bids[i].price:>9.4f} {down_ob.bids[i].size:>9.1f}" if down_ob and i < len(down_ob.bids) else f"{'--':>9} {'--':>9}"
            down_ask = f"{down_ob.asks[i].price:>9.4f} {down_ob.asks[i].size:>9.1f}" if down_ob and i < len(down_ob.asks) else f"{'--':>9} {'--':>9}"
            lines.append(f"{up_bid} | {up_ask}|{down_bid} | {down_ask}")

        lines.append("-" * 80)

        # Summary
        up_mid = up_ob.mid_price if up_ob else prices.get("up", 0)
        down_mid = down_ob.mid_price if down_ob else prices.get("down", 0)
        lines.append(
            f"Mid UP: {Colors.GREEN}{up_mid:.4f}{Colors.RESET}   |   "
            f"Mid DOWN: {Colors.RED}{down_mid:.4f}{Colors.RESET}"
        )
        lines.append(f"Drop threshold: {self.sim_config.drop_threshold:.2f} | Simulation only — no real money at risk")

        # Recent simulated events
        if hasattr(self, '_log_buffer') and self._log_buffer.messages:
            lines.append("-" * 80)
            lines.append(f"{Colors.BOLD}Recent Simulated Events:{Colors.RESET}")
            for msg in list(self._log_buffer.get_messages())[-5:]:  # last 5
                lines.append(f"  {msg}")

        # Render
        output = "\033[H\033[J" + "\n".join(lines)
        print(output, flush=True)

    def _get_countdown_str(self) -> str:
        """Helper for market countdown."""
        if hasattr(self, 'current_market') and self.current_market:
            mins, secs = self.current_market.get_countdown()
            return format_countdown(mins, secs)
        return "--:--"

    def on_market_change(self, old_slug: str, new_slug: str) -> None:
        """Clear history when market rolls to next 15m window."""
        if hasattr(self.prices, 'clear'):
            self.prices.clear()
        self.log(f"New 15m market window started: {new_slug}", "info")


# =============== Easy Runner (for Railway) ===============
async def run_sim_strategy():
    from src.bot import TradingBot
    import asyncio
    import os

    bot = TradingBot()  # or pass config_path if your repo needs it

    config = MyFlashCrashSimConfig(
        coin=os.getenv("COIN", "BTC").upper(),
        size=float(os.getenv("TRADE_SIZE", "2.0")),  # ignored in sim
        drop_threshold=float(os.getenv("DROP_THRESHOLD", "0.30")),
        sim_size=float(os.getenv("SIM_SIZE", "2.0")),
    )

    strategy = MyFlashCrashSimStrategy(bot, config)
    await strategy.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_sim_strategy())
