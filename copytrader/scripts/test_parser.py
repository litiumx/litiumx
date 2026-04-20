#!/usr/bin/env python3
"""Test parser on historical signals from the channel.

Loads signals from data/signals_sample.json and tests parsing.
Generates a report of success/failure rates.
"""

import json
from datetime import datetime
from pathlib import Path

import structlog

from src.parser.regex_parser import parse_signal
from src.parser.models import ParsedSignal

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger('INFO'),
)

logger = structlog.get_logger(__name__)


def load_signals(filepath: str) -> list[dict]:
    """Load signals from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_parsing(signals: list[dict]) -> tuple[list[ParsedSignal], list[dict]]:
    """Test parsing on a list of signals.
    
    Returns:
        Tuple of (successfully_parsed, failed_to_parse)
    """
    successful = []
    failed = []
    
    for sig in signals:
        message_id = sig['message_id']
        timestamp = datetime.fromisoformat(sig['timestamp'])
        text = sig['text']
        
        parsed = parse_signal(message_id, timestamp, text)
        
        if parsed:
            successful.append(parsed)
            logger.info(
                "Parsed successfully",
                signal_id=message_id,
                symbol=parsed.symbol,
                leverage=parsed.leverage,
            )
        else:
            failed.append(sig)
            logger.warning("Failed to parse", signal_id=message_id)
    
    return successful, failed


def generate_report(successful: list[ParsedSignal], failed: list[dict]) -> str:
    """Generate a parsing report."""
    total = len(successful) + len(failed)
    success_rate = len(successful) / total * 100 if total > 0 else 0
    
    report = []
    report.append("=" * 60)
    report.append("PARSER TEST REPORT")
    report.append("=" * 60)
    report.append(f"Total signals: {total}")
    report.append(f"Successfully parsed: {len(successful)}")
    report.append(f"Failed to parse: {len(failed)}")
    report.append(f"Success rate: {success_rate:.1f}%")
    report.append("")
    
    if successful:
        report.append("SUCCESSFULLY PARSED SIGNALS:")
        report.append("-" * 40)
        symbols = {}
        for sig in successful:
            symbols[sig.symbol] = symbols.get(sig.symbol, 0) + 1
        
        for symbol, count in sorted(symbols.items()):
            report.append(f"  {symbol}: {count} signals")
        
        # Show sample
        if successful:
            sample = successful[0]
            report.append("")
            report.append("Sample parsed signal:")
            report.append(f"  ID: {sample.signal_id}")
            report.append(f"  Symbol: {sample.symbol}")
            report.append(f"  Type: {sample.signal_type}")
            report.append(f"  Leverage: x{sample.leverage}")
            report.append(f"  Entry: {sample.entry_price}")
            report.append(f"  TP1/TP2/TP3: {sample.tp1}/{sample.tp2}/{sample.tp3}")
            report.append(f"  SL: {sample.sl}")
    
    if failed:
        report.append("")
        report.append("FAILED TO PARSE:")
        report.append("-" * 40)
        for sig in failed[:5]:  # Show first 5 failures
            report.append(f"  Message ID: {sig['message_id']}")
            report.append(f"  Text preview: {sig['text'][:80]}...")
            report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)


def main():
    """Main entry point."""
    data_path = Path(__file__).parent.parent / "data" / "signals_sample.json"
    
    if not data_path.exists():
        logger.error("Signals file not found", path=str(data_path))
        print(f"Error: Signals file not found at {data_path}")
        return 1
    
    logger.info("Loading signals", path=str(data_path))
    signals = load_signals(str(data_path))
    logger.info("Loaded signals", count=len(signals))
    
    print(f"\nTesting parser on {len(signals)} signals...\n")
    
    successful, failed = test_parsing(signals)
    report = generate_report(successful, failed)
    
    print(report)
    
    # Save report to file
    report_path = data_path.parent / "parser_test_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info("Report saved", path=str(report_path))
    print(f"\nReport saved to: {report_path}")
    
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    exit(main())
