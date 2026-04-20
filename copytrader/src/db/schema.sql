-- Schema for copytrader database
-- Tables: signals, trades, signal_updates

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    signal_id BIGINT UNIQUE NOT NULL,  -- Telegram message_id
    channel_id BIGINT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    leverage INT NOT NULL,
    entry_price DECIMAL(20, 8),  -- nullable for "по рынку"
    tp1 DECIMAL(20, 8) NOT NULL,
    tp2 DECIMAL(20, 8) NOT NULL,
    tp3 DECIMAL(20, 8) NOT NULL,
    sl DECIMAL(20, 8) NOT NULL,
    raw_text TEXT NOT NULL,
    parsed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'OPEN', 'CLOSED', 'CANCELLED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_signals_signal_id ON signals(signal_id);
CREATE INDEX idx_signals_ticker ON signals(ticker);
CREATE INDEX idx_signals_status ON signals(status);

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    signal_id BIGINT REFERENCES signals(signal_id) ON DELETE CASCADE,
    exchange_order_id VARCHAR(100),
    position_id VARCHAR(100),
    ticker VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    leverage INT NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    notional DECIMAL(20, 8) NOT NULL,
    margin DECIMAL(20, 8) NOT NULL,
    sl_price DECIMAL(20, 8) NOT NULL,
    tp1_price DECIMAL(20, 8),
    tp2_price DECIMAL(20, 8),
    tp3_price DECIMAL(20, 8),
    tp1_closed BOOLEAN DEFAULT FALSE,
    tp2_closed BOOLEAN DEFAULT FALSE,
    tp3_closed BOOLEAN DEFAULT FALSE,
    sl_closed BOOLEAN DEFAULT FALSE,
    close_price DECIMAL(20, 8),
    pnl DECIMAL(20, 8),
    pnl_pct DECIMAL(10, 4),
    fee_paid DECIMAL(20, 8) DEFAULT 0,
    funding_paid DECIMAL(20, 8) DEFAULT 0,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'OPEN', 'TP1', 'TP2', 'TP3', 'CLOSED', 'CANCELLED', 'LIQUIDATED')),
    opened_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trades_signal_id ON trades(signal_id);
CREATE INDEX idx_trades_ticker ON trades(ticker);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_opened_at ON trades(opened_at);

CREATE TABLE IF NOT EXISTS signal_updates (
    id SERIAL PRIMARY KEY,
    signal_id BIGINT REFERENCES signals(signal_id) ON DELETE CASCADE,
    update_message_id BIGINT NOT NULL,
    update_type VARCHAR(20) NOT NULL CHECK (update_type IN ('TP1', 'TP2', 'TP3', 'SL', 'CANCELLED', 'INFO')),
    price DECIMAL(20, 8),
    percent_change DECIMAL(10, 4),
    raw_text TEXT NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_signal_updates_signal_id ON signal_updates(signal_id);
CREATE INDEX idx_signal_updates_type ON signal_updates(update_type);

-- View for trade statistics
CREATE OR REPLACE VIEW trade_stats AS
SELECT 
    DATE(opened_at) as trade_date,
    ticker,
    COUNT(*) as total_trades,
    COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
    COUNT(*) FILTER (WHERE pnl <= 0) as losing_trades,
    ROUND(100.0 * COUNT(*) FILTER (WHERE pnl > 0) / NULLIF(COUNT(*), 0), 2) as winrate_pct,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl,
    MAX(pnl) as max_pnl,
    MIN(pnl) as min_pnl,
    SUM(fee_paid) as total_fees,
    SUM(funding_paid) as total_funding
FROM trades
WHERE status = 'CLOSED' AND pnl IS NOT NULL
GROUP BY DATE(opened_at), ticker
ORDER BY trade_date DESC, ticker;

-- View for daily summary
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
    trade_date,
    COUNT(total_trades) as symbols_traded,
    SUM(total_trades) as trades,
    SUM(winning_trades) as wins,
    SUM(losing_trades) as losses,
    ROUND(100.0 * SUM(winning_trades) / NULLIF(SUM(total_trades), 0), 2) as winrate_pct,
    SUM(total_pnl) as net_pnl,
    SUM(total_fees) as total_fees,
    SUM(total_funding) as total_funding
FROM trade_stats
GROUP BY trade_date
ORDER BY trade_date DESC;
