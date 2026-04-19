"""Signal validator - validates parsed signals before execution.

Checks:
- Symbol is tradeable on BingX
- Leverage is within limits
- TP/SL levels are reasonable (not too close/far)
- No conflicting positions open
- Risk parameters are met
"""

from decimal import Decimal
from typing import Optional, List

import structlog

from .models import ParsedSignal, SignalType

logger = structlog.get_logger(__name__)


# Major coins for correlation check
MAJOR_COINS = {'BTCUSDT', 'ETHUSDT', 'SOLUSDT'}


class ValidationError(Exception):
    """Raised when signal validation fails."""
    pass


def validate_signal(
    signal: ParsedSignal,
    account_balance: Decimal,
    open_positions: List[dict],
    max_leverage: int = 20,
    risk_per_trade_pct: Decimal = Decimal('5.0'),
    max_daily_loss_pct: Decimal = Decimal('15.0'),
    daily_pnl: Decimal = Decimal('0'),
    max_major_positions: int = 2,
) -> tuple[bool, Optional[str]]:
    """Validate a parsed signal before execution.
    
    Args:
        signal: The parsed signal to validate
        account_balance: Current account balance in USDT
        open_positions: List of currently open positions
        max_leverage: Maximum allowed leverage
        risk_per_trade_pct: Risk percentage per trade
        max_daily_loss_pct: Maximum daily loss percentage
        daily_pnl: Current daily PnL
        max_major_positions: Maximum concurrent positions in major coins
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # 1. Check leverage clamp
    if signal.leverage > max_leverage:
        return False, f"Leverage {signal.leverage} exceeds max {max_leverage}"
    
    # 2. Check symbol is valid (basic check)
    if not signal.symbol.endswith('USDT'):
        return False, f"Invalid symbol format: {signal.symbol}"
    
    # 3. Check TP/SL levels are logical for LONG position
    if signal.signal_type == SignalType.LONG:
        if signal.sl >= signal.entry_price:
            return False, f"SL {signal.sl} must be below entry {signal.entry_price} for LONG"
        if signal.tp1 <= signal.entry_price:
            return False, f"TP1 {signal.tp1} must be above entry for LONG"
        if signal.tp2 <= signal.tp1:
            return False, f"TP2 {signal.tp2} must be above TP1 {signal.tp1}"
        if signal.tp3 <= signal.tp2:
            return False, f"TP3 {signal.tp3} must be above TP2 {signal.tp2}"
    
    # 4. Check SL distance is reasonable (not too tight)
    sl_distance_pct = abs(signal.entry_price - signal.sl) / signal.entry_price * 100
    if sl_distance_pct < Decimal('0.5'):
        return False, f"SL too tight: {sl_distance_pct:.2f}% (min 0.5%)"
    if sl_distance_pct > Decimal('15'):
        return False, f"SL too wide: {sl_distance_pct:.2f}% (max 15%)"
    
    # 5. Check TP distances are reasonable
    tp1_distance_pct = (signal.tp1 - signal.entry_price) / signal.entry_price * 100
    if tp1_distance_pct < Decimal('0.3'):
        return False, f"TP1 too close: {tp1_distance_pct:.2f}% (min 0.3%)"
    
    # 6. Check max open positions
    if len(open_positions) >= 3:
        return False, f"Max open positions (3) reached"
    
    # 7. Check correlation cap for major coins
    major_count = sum(1 for pos in open_positions if pos.get('symbol') in MAJOR_COINS)
    if signal.symbol in MAJOR_COINS and major_count >= max_major_positions:
        return False, f"Max major coin positions ({max_major_positions}) reached"
    
    # 8. Check daily loss limit
    if daily_pnl < 0:
        daily_loss_pct = abs(daily_pnl) / account_balance * 100
        if daily_loss_pct >= max_daily_loss_pct:
            return False, f"Daily loss limit reached: {daily_loss_pct:.2f}% >= {max_daily_loss_pct}%"
    
    # 9. Calculate position size and check min notional
    risk_amount = account_balance * risk_per_trade_pct / 100
    sl_distance = abs(signal.entry_price - signal.sl)
    
    if sl_distance == 0:
        return False, "SL distance is zero"
    
    # Position size = risk_amount / sl_distance
    position_size_usdt = risk_amount * signal.leverage
    
    # BingX min notional is typically $5 for BTC, $1-2 for others
    min_notional = Decimal('5') if signal.symbol in {'BTCUSDT', 'ETHUSDT'} else Decimal('2')
    
    if position_size_usdt < min_notional:
        return False, f"Position size ${position_size_usdt:.2f} below min notional ${min_notional}"
    
    logger.info(
        "Signal validation passed",
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        leverage=signal.leverage,
        position_size_usdt=position_size_usdt,
        sl_distance_pct=sl_distance_pct,
    )
    
    return True, None


def calculate_position_size(
    account_balance: Decimal,
    entry_price: Decimal,
    sl_price: Decimal,
    leverage: int,
    risk_per_trade_pct: Decimal = Decimal('5.0'),
) -> Decimal:
    """Calculate position size based on risk parameters.
    
    Args:
        account_balance: Account balance in USDT
        entry_price: Entry price
        sl_price: Stop-loss price
        leverage: Leverage to use
        risk_per_trade_pct: Risk percentage per trade
        
    Returns:
        Quantity in base currency (e.g., BTC for BTCUSDT)
    """
    risk_amount = account_balance * risk_per_trade_pct / 100
    sl_distance = abs(entry_price - sl_price)
    
    if sl_distance == 0:
        raise ValueError("SL distance cannot be zero")
    
    # Quantity = risk_amount / sl_distance
    quantity = risk_amount / sl_distance
    
    return quantity
