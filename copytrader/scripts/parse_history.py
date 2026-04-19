#!/usr/bin/env python3
"""Parse all historical signals from the Telegram export.

Runs the regex parser on all 107 signals and reports success/failure.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.regex_parser import parse_signal, parse_update
import structlog
import logging

structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(colors=False, exception_formatter=structlog.dev.plain_traceback)
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
)

logger = structlog.get_logger(__name__)


def load_messages(filepath: str) -> list:
    """Load messages from JSON export."""
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)
    # Handle both formats: list of messages or dict with 'messages' key
    if isinstance(data, list):
        return data
    return data.get('messages', [])


def extract_text(message: dict) -> str:
    """Extract text from message (handles both string and list formats)."""
    # Handle our simplified format where text is a string
    if 'text' in message and isinstance(message['text'], str):
        return message['text'].strip()
    
    # Handle Telegram JSON export format where text can be array of parts
    text = message.get('text', '')
    if isinstance(text, list):
        # Handle Telegram JSON format where text is array of parts
        text_parts = []
        for part in text:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
        text = ''.join(text_parts)
    return str(text).strip()


def main():
    """Run parser on all historical signals."""
    data_path = Path(__file__).parent.parent / 'data' / 'signals_sample.json'
    
    if not data_path.exists():
        print(f"ERROR: {data_path} not found")
        sys.exit(1)
    
    messages = load_messages(str(data_path))
    print(f"Loaded {len(messages)} messages from export")
    
    signals_ok = 0
    signals_fail = 0
    signal_errors = []
    
    updates_ok = 0
    updates_fail = 0
    update_errors = []
    
    # Build a map of signal_id -> signal for reply matching
    signal_map = {}
    
    # First pass: parse all signals
    for msg in messages:
        text = extract_text(msg)
        
        # Check if this looks like a signal
        if 'Покупка' not in text and 'LONG' not in text.upper() and 'Торговая пара' not in text:
            continue
        
        # Handle both timestamp formats
        if 'timestamp' in msg:
            ts_str = msg['timestamp']
        elif 'date' in msg:
            ts_str = msg['date']
        else:
            logger.warning("Message without timestamp", message_id=msg.get('id', 'unknown'))
            continue
        
        timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        
        # Handle both id and message_id fields
        msg_id = msg.get('id') or msg.get('message_id')
        if msg_id is None:
            logger.warning("Message without ID")
            continue
        
        result = parse_signal(msg_id, timestamp, text)
        
        if result:
            signals_ok += 1
            signal_map[msg_id] = result
            print(f"✓ Signal #{msg_id}: {result.symbol} x{result.leverage}")
        else:
            signals_fail += 1
            signal_errors.append({
                'id': msg_id,
                'date': ts_str,
                'text_preview': text[:80].replace('\n', ' ')
            })
            print(f"✗ Signal #{msg_id}: FAILED")
    
    # Second pass: parse all updates (reply messages)
    for msg in messages:
        reply_to = msg.get('reply_to_message_id')
        if reply_to is None:
            continue
        
        text = extract_text(msg)
        
        # Handle both timestamp formats
        if 'timestamp' in msg:
            ts_str = msg['timestamp']
        elif 'date' in msg:
            ts_str = msg['date']
        else:
            continue
        
        timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        
        # Handle both id and message_id fields
        msg_id = msg.get('id') or msg.get('message_id')
        if msg_id is None:
            continue
        
        result = parse_update(msg_id, timestamp, text, reply_to_message_id=reply_to)
        
        if result:
            updates_ok += 1
            print(f"  → Update #{msg_id} (reply to #{reply_to}): {result.update_type.value}")
        else:
            updates_fail += 1
            update_errors.append({
                'id': msg_id,
                'reply_to': reply_to,
                'date': ts_str,
                'text_preview': text[:80].replace('\n', ' ')
            })
    
    # Print summary
    print("\n" + "="*60)
    print("PARSER RESULTS")
    print("="*60)
    print(f"Signals: {signals_ok} parsed, {signals_fail} failed")
    print(f"Updates: {updates_ok} parsed, {updates_fail} failed")
    
    if signals_fail > 0:
        print("\nFailed signals:")
        for err in signal_errors:
            print(f"  ID {err['id']} ({err['date']}): {err['text_preview']}...")
    
    if updates_fail > 0:
        print("\nFailed updates:")
        for err in update_errors:
            print(f"  ID {err['id']} (reply to {err['reply_to']}): {err['text_preview']}...")
    
    # Exit with error code if any failures
    if signals_fail > 0 or updates_fail > 0:
        print(f"\n❌ PARSER TEST FAILED: {signals_fail + updates_fail} errors")
        sys.exit(1)
    else:
        print(f"\n✅ PARSER TEST PASSED: {signals_ok} signals + {updates_ok} updates")
        sys.exit(0)


if __name__ == '__main__':
    main()
