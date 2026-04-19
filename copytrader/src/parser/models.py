"""Data models for signal parsing and validation."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SignalType(str, Enum):
    """Тип сигнала."""
    LONG = "long"
    SHORT = "short"


class SignalSource(str, Enum):
    """Источник сигнала."""
    TELEGRAM_CHANNEL = "telegram_channel"
    MANUAL = "manual"


class SignalStatus(str, Enum):
    """Статус сигнала."""
    PENDING = "pending"  # Ожидает исполнения
    EXECUTING = "executing"  # Ордер отправлен
    FILLED = "filled"  # Ордер исполнен
    TP1_HIT = "tp1_hit"  # Достигнута первая цель
    TP2_HIT = "tp2_hit"  # Достигнута вторая цель
    TP3_HIT = "tp3_hit"  # Достигнута третья цель
    STOP_LOSS_HIT = "stop_loss_hit"  # Сработал стоп-лосс
    CLOSED = "closed"  # Позиция закрыта
    CANCELLED = "cancelled"  # Сигнал отменён
    FAILED = "failed"  # Ошибка исполнения


class ParsedSignal(BaseModel):
    """Распарсенный сигнал из Telegram канала."""
    
    signal_id: int = Field(..., description="ID сообщения в Telegram")
    timestamp: datetime = Field(..., description="Время публикации сигнала")
    
    # Параметры торговли
    symbol: str = Field(..., description="Торговая пара, например BTCUSDT")
    signal_type: SignalType = Field(..., description="Направление (LONG/SHORT)")
    leverage: int = Field(..., ge=1, le=100, description="Кредитное плечо")
    
    entry_price: Decimal = Field(..., description="Цена входа")
    
    # Цели и стоп
    tp1: Decimal = Field(..., description="Первая цель take-profit")
    tp2: Decimal = Field(..., description="Вторая цель take-profit")
    tp3: Decimal = Field(..., description="Третья цель take-profit")
    sl: Decimal = Field(..., description="Стоп-лосс")
    
    # Метаданные
    source: SignalSource = Field(default=SignalSource.TELEGRAM_CHANNEL)
    raw_text: str = Field(..., description="Исходный текст сообщения")
    
    # Статусы
    status: SignalStatus = Field(default=SignalStatus.PENDING)
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Нормализация символа."""
        return v.upper().replace('$', '').replace('USDT', 'USDT')
    
    @field_validator('leverage')
    @classmethod
    def clamp_leverage(cls, v: int) -> int:
        """Ограничение плеча максимум 20 для безопасности."""
        return min(v, 20)
    
    class Config:
        use_enum_values = True


class SignalUpdate(BaseModel):
    """Обновление статуса сигнала из канала."""
    
    update_id: int = Field(..., description="ID сообщения обновления")
    signal_id: int = Field(..., description="ID исходного сигнала (reply_to)")
    timestamp: datetime = Field(..., description="Время обновления")
    
    # Тип обновления
    update_type: SignalStatus = Field(..., description="Тип события")
    
    # Дополнительные данные
    price: Optional[Decimal] = Field(None, description="Цена достижения цели")
    percentage: Optional[Decimal] = Field(None, description="Процент изменения")
    
    raw_text: str = Field(..., description="Исходный текст обновления")
    parsed_at: datetime = Field(default_factory=datetime.utcnow)


class Trade(BaseModel):
    """Исполненная сделка."""
    
    trade_id: Optional[int] = Field(None, description="ID записи в БД")
    signal_id: int = Field(..., description="Ссылка на сигнал")
    
    # Параметры исполнения
    entry_price: Decimal = Field(..., description="Фактическая цена входа")
    quantity: Decimal = Field(..., description="Количество контрактов")
    leverage: int = Field(..., description="Использованное плечо")
    
    # Уровни выхода
    tp1: Decimal = Field(...)
    tp2: Decimal = Field(...)
    tp3: Decimal = Field(...)
    sl: Decimal = Field(...)
    
    # Статусы исполнения
    status: SignalStatus = Field(default=SignalStatus.EXECUTING)
    
    # Тайминги
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    # Финансы
    realized_pnl: Optional[Decimal] = Field(None, description="Реализованный PnL")
    fees_paid: Optional[Decimal] = Field(None, description="Комиссии")
    funding_paid: Optional[Decimal] = Field(None, description="Funding rate платежи")
    
    # Метаданные биржи
    order_id: Optional[str] = Field(None, description="ID ордера на бирже")
    position_id: Optional[str] = Field(None, description="ID позиции на бирже")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
