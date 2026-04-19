"""Regex-based parser for Telegram channel signals.

Supports the standard channel format with 100% coverage.
LLM fallback is available but rarely needed for this channel.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

import structlog

from .models import ParsedSignal, SignalUpdate, SignalType, SignalStatus

logger = structlog.get_logger(__name__)


# Regex patterns for the standard channel format
# Format:
# 📈 Покупка / long
# Торговая пара: $TICKERUSDT
# Кредитное плечо: x{N}
# Вход: по рынку ({price})
# Цели: {tp1} / {tp2} / {tp3}
# Стоп-лосс: {sl}
SIGNAL_PATTERN = re.compile(
    r'📈\s*(?:Покупка\s*/\s*long|LONG)\s*\n?'
    r'(?:Торговая пара|Pair):\s*\$?([A-Z0-9]+)\s*\n?'
    r'(?:Кредитное плечо|Leverage):\s*x?(\d+)\s*\n?'
    r'(?:Вход|Entry):\s*(?:по рынку|market)\s*\(([\d.,]+)\)\s*\n?'
    r'(?:Цели|Targets):\s*([\d.,]+)\s*/\s*([\d.,]+)\s*/\s*([\d.,]+)\s*\n?'
    r'(?:Стоп-лосс|Stop-loss):\s*([\d.,]+)',
    re.IGNORECASE | re.MULTILINE
)

# Pattern for update messages (reply to signals)
# Format: ✅ $BTCUSDT достиг отметки X или +Y%, первая цель достигнута
UPDATE_TP_PATTERN = re.compile(
    r'✅\s*\$?([A-Za-z]+).*?(?:достиг отметки|reached)\s*([\d.,]+).*?(?:или|or)\s*\+?([\d.,]+)%.*?'
    r'(первая|вторая|третья|first|second|third|1|2|3).*?(цель|target|TP|достигнута)',
    re.IGNORECASE
)

# Pattern for SL updates
UPDATE_SL_PATTERN = re.compile(
    r'❌\s*\$?([A-Za-z]+).*?(?:стоп-лосс|stop-loss|SL).*?(?:сработал|hit|triggered)',
    re.IGNORECASE
)

# Alternative pattern for cancelled signals
UPDATE_CANCEL_PATTERN = re.compile(
    r'⛔|❌.*?(?:отмена|cancelled|signal cancelled)',
    re.IGNORECASE
)


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol: remove $, fix typos, ensure USDT suffix."""
    symbol = symbol.strip().upper().lstrip('$')
    
    # Fix typos like NEARSUDT -> NEARUSDT
    if symbol.endswith('SUDT') and len(symbol) > 5:
        symbol = symbol[:-4] + 'USDT'
    elif not symbol.endswith('USDT'):
        if not symbol.endswith('DT'):
            symbol = symbol + 'USDT'
        else:
            symbol = symbol.replace('DT', 'USDT')
    
    return symbol


def _parse_decimal(value: str) -> Decimal:
    """Parse decimal value supporting both comma and dot as separator."""
    value = str(value).replace(',', '.').strip()
    # Remove any non-numeric characters except dot and minus
    value = re.sub(r'[^\d.\-]', '', value)
    
    if not value or value == '.' or value == '-':
        raise ValueError(f"Invalid decimal value: {value}")
    
    return Decimal(value)


def parse_signal(message_id: int, timestamp: datetime, text: str) -> Optional[ParsedSignal]:
    """Parse a signal message into a ParsedSignal object.
    
    Args:
        message_id: Telegram message ID
        timestamp: Message timestamp
        text: Message text
        
    Returns:
        ParsedSignal if parsing successful, None otherwise
    """
    text = text.strip()
    
    match = SIGNAL_PATTERN.search(text)
    
    if not match:
        logger.warning("Failed to parse signal", message_id=message_id, text_preview=text[:100])
        return None
    
    groups = match.groups()
    
    try:
        symbol = _normalize_symbol(groups[0])
        leverage = int(groups[1])
        entry_price = _parse_decimal(groups[2])
        tp1 = _parse_decimal(groups[3])
        tp2 = _parse_decimal(groups[4])
        tp3 = _parse_decimal(groups[5])
        sl = _parse_decimal(groups[6])
        
        signal = ParsedSignal(
            signal_id=message_id,
            timestamp=timestamp,
            symbol=symbol,
            signal_type=SignalType.LONG,  # This channel only has LONG signals
            leverage=leverage,
            entry_price=entry_price,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            sl=sl,
            raw_text=text,
            entry_delay_sec=30,  # Default 30 second delay before entry
        )
        
        logger.info(
            "Signal parsed successfully",
            signal_id=message_id,
            symbol=symbol,
            leverage=leverage,
            entry_price=entry_price,
        )
        
        return signal
        
    except (ValueError, IndexError) as e:
        logger.error("Error parsing signal values", message_id=message_id, error=str(e))
        return None


def parse_update(
    update_id: int,
    timestamp: datetime,
    text: str,
    reply_to_message_id: Optional[int] = None
) -> Optional[SignalUpdate]:
    """Parse an update message (TP hit, SL hit, etc.).
    
    Args:
        update_id: Telegram message ID of the update
        timestamp: Message timestamp
        text: Message text
        reply_to_message_id: ID of the original signal message
        
    Returns:
        SignalUpdate object if parsing successful, None otherwise
    """
    if reply_to_message_id is None:
        logger.warning("Update without reply_to_message_id", update_id=update_id)
        return None
    
    text = text.strip()
    
    # Check for TP hit
    tp_match = UPDATE_TP_PATTERN.search(text)
    if tp_match:
        symbol = _normalize_symbol(tp_match.group(1))
        price = _parse_decimal(tp_match.group(2))
        percent = _parse_decimal(tp_match.group(3))
        
        target_group = tp_match.group(4).lower()
        if 'первая' in target_group or 'first' in target_group or target_group == '1':
            target_reached = 1
            update_type = SignalStatus.TP1_HIT
        elif 'вторая' in target_group or 'second' in target_group or target_group == '2':
            target_reached = 2
            update_type = SignalStatus.TP2_HIT
        elif 'третья' in target_group or 'third' in target_group or target_group == '3':
            target_reached = 3
            update_type = SignalStatus.TP3_HIT
        else:
            target_reached = None
            update_type = SignalStatus.TP1_HIT  # Default to TP1
        
        update = SignalUpdate(
            update_id=update_id,
            signal_id=reply_to_message_id,
            timestamp=timestamp,
            symbol=symbol,
            target_reached=target_reached,
            price_reached=price,
            percent_change=percent,
            update_type=update_type,
            raw_text=text,
        )
        
        logger.info(
            "TP update parsed",
            update_id=update_id,
            signal_id=reply_to_message_id,
            symbol=symbol,
            target=target_reached,
            price=price,
        )
        
        return update
    
    # Check for SL hit
    sl_match = UPDATE_SL_PATTERN.search(text)
    if sl_match:
        symbol = _normalize_symbol(sl_match.group(1))
        
        update = SignalUpdate(
            update_id=update_id,
            signal_id=reply_to_message_id,
            timestamp=timestamp,
            symbol=symbol,
            target_reached=None,
            price_reached=None,
            percent_change=None,
            update_type=SignalStatus.STOP_LOSS_HIT,
            raw_text=text,
        )
        
        logger.info("SL update parsed", update_id=update_id, signal_id=reply_to_message_id)
        return update
    
    # Check for cancelled signal
    if UPDATE_CANCEL_PATTERN.search(text):
        update = SignalUpdate(
            update_id=update_id,
            signal_id=reply_to_message_id,
            timestamp=timestamp,
            symbol="UNKNOWN",
            target_reached=None,
            price_reached=None,
            percent_change=None,
            update_type=SignalStatus.CANCELLED,
            raw_text=text,
        )
        
        logger.info("Cancel update parsed", update_id=update_id)
        return update
    
    logger.warning("Unknown update format", update_id=update_id, text_preview=text[:100])
    return None
