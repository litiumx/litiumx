#!/usr/bin/env python3
"""Test parser on all historical signals from the channel export.

Usage:
    python scripts/parse_history.py

Output:
    - parsed: X/107
    - failed: Y
    - errors: [...]
    - Detailed report by ticker
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.regex_parser import parse_signal, parse_update
from src.parser.models import ParsedSignal, SignalUpdate


def load_export_data(filepath: str) -> List[Dict[str, Any]]:
    """Load Telegram export JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both formats: list or dict with 'messages' key
    if isinstance(data, list):
        return data
    return data.get('messages', [])


def test_parser(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test parser on all messages."""
    
    results = {
        'total_messages': len(messages),
        'signals_found': 0,
        'signals_parsed': 0,
        'updates_found': 0,
        'updates_parsed': 0,
        'failed_signals': [],
        'failed_updates': [],
        'by_ticker': {},
    }
    
    # First pass: find all signals and updates
    signal_messages = []
    update_messages = []
    
    for msg in messages:
        if msg.get('type') != 'message':
            continue
        
        text = msg.get('text', '')
        if isinstance(text, list):
            # Telegram export sometimes splits text into array
            text = ' '.join(str(t) for t in text)
        
        if not text.strip():
            continue
        
        # Check if it's a signal (starts with 📈)
        if '📈' in text and ('Покупка' in text or 'LONG' in text):
            signal_messages.append(msg)
        # Check if it's an update (starts with ✅ or ❌)
        elif text.strip().startswith('✅') or text.strip().startswith('❌') or '⛔' in text:
            update_messages.append(msg)
    
    results['signals_found'] = len(signal_messages)
    results['updates_found'] = len(update_messages)
    
    # Parse signals
    print(f"\n{'='*60}")
    print(f"ПАРСИНГ СИГНАЛОВ")
    print(f"{'='*60}\n")
    
    for msg in signal_messages:
        message_id = msg.get('id', 0)
        timestamp_str = msg.get('date', '')
        text = msg.get('text', '')
        
        if isinstance(text, list):
            text = ' '.join(str(t) for t in text)
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            timestamp = datetime.utcnow()
        
        signal = parse_signal(message_id, timestamp, text)
        
        if signal:
            results['signals_parsed'] += 1
            
            # Track by ticker
            ticker = signal.symbol
            if ticker not in results['by_ticker']:
                results['by_ticker'][ticker] = {'parsed': 0, 'failed': 0}
            results['by_ticker'][ticker]['parsed'] += 1
            
            print(f"✓ #{message_id} {ticker} x{signal.leverage} Entry: {signal.entry_price} SL: {signal.sl}")
        else:
            results['failed_signals'].append({
                'message_id': message_id,
                'text_preview': text[:100],
            })
            print(f"✗ #{message_id} FAILED: {text[:80]}...")
    
    # Parse updates
    print(f"\n{'='*60}")
    print(f"ПАРСИНГ ОБНОВЛЕНИЙ")
    print(f"{'='*60}\n")
    
    # Build signal_id map for reply_to lookup
    signal_ids = {msg.get('id'): msg for msg in signal_messages}
    
    for msg in update_messages:
        message_id = msg.get('id', 0)
        timestamp_str = msg.get('date', '')
        text = msg.get('text', '')
        reply_to_id = msg.get('reply_to_message_id')
        
        if isinstance(text, list):
            text = ' '.join(str(t) for t in text)
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            timestamp = datetime.utcnow()
        
        update = parse_update(message_id, timestamp, text, reply_to_id)
        
        if update:
            results['updates_parsed'] += 1
            status_icon = '✅' if 'TP' in update.update_type.value else '❌' if 'SL' in update.update_type.value else '⛔'
            target = f"TP{update.target_reached}" if update.target_reached else update.update_type.value
            print(f"{status_icon} #{message_id} → Signal #{reply_to_id}: {update.symbol} {target} @ {update.price_reached or 'N/A'}")
        else:
            results['failed_updates'].append({
                'message_id': message_id,
                'text_preview': text[:100],
            })
            print(f"✗ #{message_id} FAILED UPDATE: {text[:80]}...")
    
    return results


def print_report(results: Dict[str, Any]):
    """Print detailed report."""
    
    print(f"\n{'='*60}")
    print(f"ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'='*60}\n")
    
    # Overall stats
    print(f"Всего сообщений: {results['total_messages']}")
    print(f"\nСигналы:")
    print(f"  Найдено: {results['signals_found']}")
    print(f"  Распарсено: {results['signals_parsed']}/{results['signals_found']} ({results['signals_parsed']/max(results['signals_found'],1)*100:.1f}%)")
    print(f"  Ошибки: {len(results['failed_signals'])}")
    
    print(f"\nОбновления:")
    print(f"  Найдено: {results['updates_found']}")
    print(f"  Распарсено: {results['updates_parsed']}/{results['updates_found']} ({results['updates_parsed']/max(results['updates_found'],1)*100:.1f}%)")
    print(f"  Ошибки: {len(results['failed_updates'])}")
    
    # By ticker
    print(f"\n{'='*60}")
    print(f"ПО ТИКЕРАМ")
    print(f"{'='*60}\n")
    
    sorted_tickers = sorted(results['by_ticker'].items(), key=lambda x: x[1]['parsed'], reverse=True)
    for ticker, stats in sorted_tickers[:15]:  # Top 15
        print(f"{ticker}: {stats['parsed']} сигналов")
    
    # Failed signals
    if results['failed_signals']:
        print(f"\n{'='*60}")
        print(f"ОШИБКИ ПАРСИНГА СИГНАЛОВ")
        print(f"{'='*60}\n")
        for err in results['failed_signals'][:10]:  # Show first 10
            print(f"Message #{err['message_id']}: {err['text_preview']}...")
    
    # Failed updates
    if results['failed_updates']:
        print(f"\n{'='*60}")
        print(f"ОШИБКИ ПАРСИНГА ОБНОВЛЕНИЙ")
        print(f"{'='*60}\n")
        for err in results['failed_updates'][:10]:  # Show first 10
            print(f"Message #{err['message_id']}: {err['text_preview']}...")
    
    # Success criteria
    print(f"\n{'='*60}")
    print(f"КРИТЕРИИ УСПЕХА")
    print(f"{'='*60}\n")
    
    signal_success = results['signals_parsed'] == results['signals_found'] == 107
    update_success = results['updates_parsed'] == results['updates_found'] == 107
    
    if signal_success:
        print("✅ Сигналы: 107/107 распарсено")
    else:
        print(f"❌ Сигналы: {results['signals_parsed']}/{results['signals_found']} (ожидалось 107/107)")
    
    if update_success:
        print("✅ Обновления: 107/107 распарсено")
    else:
        print(f"❌ Обновления: {results['updates_parsed']}/{results['updates_found']} (ожидалось 107/107)")
    
    if signal_success and update_success:
        print(f"\n🎉 ВСЕ КРИТЕРИИ ВЫПОЛНЕНЫ! Можно переходить к Этапу 2 (бэктестер).")
        return True
    else:
        print(f"\n⚠️  Требуется доработка парсера.")
        return False


def main():
    """Main entry point."""
    
    # Find export file
    data_dir = Path(__file__).parent.parent / 'data'
    export_file = data_dir / 'signals_sample.json'
    
    if not export_file.exists():
        print(f"❌ Файл не найден: {export_file}")
        print(f"   Положите экспорт Telegram в {data_dir}/signals_sample.json")
        sys.exit(1)
    
    print(f"Загрузка экспорта из {export_file}...")
    messages = load_export_data(str(export_file))
    print(f"Загружено {len(messages)} сообщений")
    
    # Run parser test
    results = test_parser(messages)
    
    # Print report
    success = print_report(results)
    
    # Save results to JSON
    output_file = data_dir / 'parse_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nРезультаты сохранены в {output_file}")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
