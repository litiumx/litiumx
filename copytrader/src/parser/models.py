"""Data models for signal parsing and validation."""

import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Literal

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
    entry_delay_sec: int = Field(default=30, description="Задержка перед входом в секундах")
    
    # Статусы
    status: SignalStatus = Field(default=SignalStatus.PENDING)
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Нормализация символа: убрать $, исправить опечатки, добавить USDT если нужно."""
        v = v.strip().upper().lstrip('$')
        
        # Исправление опечаток типа NEARSUDT -> NEARUSDT
        if v.endswith('SUDT') and len(v) > 5:
            v = v[:-4] + 'USDT'
        elif not v.endswith('USDT'):
            # Если не заканчивается на USDT или DT, добавляем USDT
            if not v.endswith('DT'):
                v = v + 'USDT'
            else:
                # Заканчивается на DT но не USDT (например BTCDT)
                v = v.replace('DT', 'USDT')
        
        return v
    
    @field_validator('leverage')
    @classmethod
    def clamp_leverage(cls, v: int) -> int:
        """Ограничение плеча максимум 20 для безопасности."""
        return min(v, 20)
    
    @field_validator('entry_price', 'tp1', 'tp2', 'tp3', 'sl')
    @classmethod
    def parse_decimal_with_comma(cls, v):
        """Парсинг чисел с поддержкой запятой (1,624 -> 1.624)."""
        if isinstance(v, Decimal):
            return v
        
        v_str = str(v).replace(',', '.').strip()
        # Удаляем лишние символы кроме цифр, точки и минуса
        v_str = re.sub(r'[^\d.\-]', '', v_str)
        
        if not v_str or v_str == '.' or v_str == '-':
            raise ValueError(f"Invalid decimal value: {v}")
        
        return Decimal(v_str)
    
    class Config:
        use_enum_values = True


class SignalUpdate(BaseModel):
    """Обновление статуса сигнала из канала (reply-сообщение)."""
    
    update_id: int = Field(..., description="ID сообщения обновления")
    signal_id: int = Field(..., description="ID исходного сигнала (reply_to)")
    timestamp: datetime = Field(..., description="Время обновления")
    
    # Параметры из обновления
    symbol: str = Field(..., description="Торговая пара")
    
    # Тип обновления - извлекается из текста
    target_reached: Optional[Literal[1, 2, 3]] = Field(None, description="Номер достигнутой цели (1/2/3)")
    price_reached: Optional[Decimal] = Field(None, description="Цена достижения цели")
    percent_change: Optional[Decimal] = Field(None, description="Процент изменения (+Y%)")
    
    # Вычисленный статус
    update_type: SignalStatus = Field(..., description="Тип события")
    
    raw_text: str = Field(..., description="Исходный текст обновления")
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Нормализация символа."""
        v = v.strip().upper().lstrip('$')
        if v.endswith('SUDT') and len(v) > 5:
            v = v[:-4] + 'USDT'
        elif not v.endswith('USDT'):
            if not v.endswith('DT'):
                v = v + 'USDT'
            else:
                v = v.replace('DT', 'USDT')
        return v
    
    @field_validator('price_reached', 'percent_change')
    @classmethod
    def parse_decimal_with_comma(cls, v):
        """Парсинг чисел с поддержкой запятой."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        
        v_str = str(v).replace(',', '.').strip()
        v_str = re.sub(r'[^\d.\-]', '', v_str)
        
        if not v_str or v_str == '.' or v_str == '-':
            return None
        
        return Decimal(v_str)


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
