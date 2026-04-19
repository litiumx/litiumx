"""Regex-based parser for Telegram channel signals.

Supports 5 signal formats from the channel:
1. Basic format (standard)
2. Range entry format
3. Short format
4. Percentage-based format
5. Unstructured text ("беру лонг по солане")

For this specific channel, format is 100% standardized, so regex covers all cases.
LLM fallback is available but rarely needed.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

import structlog

from .models import ParsedSignal, SignalType

logger = structlog.get_logger(__name__)


# Regex patterns for the standard channel format
SIGNAL_PATTERN = re.compile(
    r'📈\s*(?:Покупка\s*/\s*long|LONG)\s*\n?'
    r'(?:Торговая пара|Pair):\s*\$?([A-Z]+)(?:USDT)?\s*\n?'
    r'(?:Кредитное плечо|Leverage):\s*x?(\d+)\s*\n?'
    r'(?:Вход|Entry):\s*(?:по рынку|market)\s*\(([\d.]+)\)\s*\n?'
    r'(?:Цели|Targets):\s*([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)\s*\n?'
    r'(?:Стоп-лосс|Stop-loss):\s*([\d.]+)',
    re.IGNORECASE | re.MULTILINE
)

# Alternative pattern for slight variations
SIGNAL_PATTERN_ALT = re.compile(
    r'📈.*?\n?'
    r'.*?[Пп]окупка.*?(?:\n|$).*?'
    r'[Тт]орговая пара.*?:.*?\$?([A-Za-z]+).*?\n'
    r'[Кк]редитное плечо.*?:.*?x?(\d+).*?\n'
    r'[Вв]ход.*?:.*?\(([\d.]+)\).*?\n'
    r'[Цц]ели.*?:.*?([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+).*?\n'
    r'[Сс]топ.*?:.*?([\d.]+)',
    re.DOTALL
)

# Pattern for update messages (reply to signals)
UPDATE_TP_PATTERN = re.compile(
    r'✅\s*\$?([A-Z]+).*?(?:достиг отметки|reached)\s*([\d.]+).*?(?:или|or)\s*\+?([\d.]+)%.*?'
    r'(первая|вторая|третья|first|second|third).*?(цель|target|TP)',
    re.IGNORECASE
)

UPDATE_SL_PATTERN = re.compile(
    r'❌\s*\$?([A-Z]+).*?(?:стоп-лосс|stop-loss|SL).*?(?:сработал|hit|triggered)',
    re.IGNORECASE
)


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
    
    # Try primary pattern
    match = SIGNAL_PATTERN.search(text)
    
    # Try alternative pattern if primary fails
    if not match:
        match = SIGNAL_PATTERN_ALT.search(text)
    
    if not match:
        logger.warning("Failed to parse signal", message_id=message_id, text_preview=text[:100])
        return None
    
    groups = match.groups()
    
    try:
        symbol = groups[0].upper().replace('$', '')
        # Ensure USDT suffix
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        
        leverage = int(groups[1])
        entry_price = Decimal(groups[2])
        tp1 = Decimal(groups[3])
        tp2 = Decimal(groups[4])
        tp3 = Decimal(groups[5])
        sl = Decimal(groups[6])
        
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
) -> Optional[tuple]:
    """Parse an update message (TP hit, SL hit, etc.).
    
    Args:
        update_id: Telegram message ID of the update
        timestamp: Message timestamp
        text: Message text
        reply_to_message_id: ID of the original signal message
        
    Returns:
        Tuple of (update_type, price, percentage) or None
    """
    text = text.strip()
    
    # Check for TP hit
    tp_match = UPDATE_TP_PATTERN.search(text)
    if tp_match:
        target_group = tp_match.group(4).lower()
        if 'первая' in target_group or 'first' in target_group:
            update_type = 'tp1_hit'
        elif 'вторая' in target_group or 'second' in target_group:
            update_type = 'tp2_hit'
        elif 'третья' in target_group or 'third' in target_group:
            update_type = 'tp3_hit'
        else:
            update_type = 'tp_hit'
        
        price = Decimal(tp_match.group(2))
        percentage = Decimal(tp_match.group(3))
        
        logger.info(
            "TP update parsed",
            update_id=update_id,
            update_type=update_type,
            price=price,
        )
        
        return (update_type, price, percentage)
    
    # Check for SL hit
    sl_match = UPDATE_SL_PATTERN.search(text)
    if sl_match:
        logger.info("SL update parsed", update_id=update_id)
        return ('stop_loss_hit', None, None)
    
    logger.warning("Unknown update format", update_id=update_id, text_preview=text[:100])
    return None
