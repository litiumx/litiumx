# Криптобот для торговли криптовалютой

## 📖 Описание

Это простой и функциональный криптобот для автоматической торговли на криптовалютных биржах. 
Бот поддерживает работу с множеством бирж через библиотеку CCXT.

## ✨ Возможности

- **Поддержка множества бирж**: Binance, Bybit, OKX, Kraken и 100+ других
- **Получение рыночных данных**: цены, стакан заказов, свечи (OHLCV)
- **Торговые операции**: рыночные и лимитные ордера на покупку/продажу
- **Управление балансом**: проверка баланса по валютам
- **Управление ордерами**: просмотр и отмена открытых ордеров
- **Простая торговая стратегия**: покупка при падении, продажа при росте

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install ccxt python-dotenv
```

### 2. Настройка API ключей

Скопируйте файл `.env.example` в `.env` и заполните своими данными:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
SANDBOX=false  # true для тестового режима
EXCHANGE_ID=binance
```

### 3. Запуск бота

```bash
python crypto_bot.py
```

## 📋 Примеры использования

### Базовое использование

```python
from crypto_bot import CryptoBot

# Создаем бота для Binance
bot = CryptoBot(exchange_id='binance')

# Получаем цену BTC
price = bot.get_price('BTC/USDT')

# Проверяем баланс
balance = bot.get_balance('USDT')

# Получаем стакан заказов
orderbook = bot.get_orderbook('BTC/USDT', limit=10)

# Получаем свечи
ohlcv = bot.get_ohlcv('BTC/USDT', timeframe='1h', limit=100)
```

### Торговые операции

```python
# Рыночная покупка на 100 USDT
bot.buy_market('BTC/USDT', cost_usdt=100)

# Рыночная покупка определенного количества
bot.buy_market('BTC/USDT', amount=0.001)

# Лимитная покупка
bot.buy_limit('BTC/USDT', price=70000, amount=0.001)

# Рыночная продажа
bot.sell_market('BTC/USDT', amount=0.001)

# Лимитная продажа
bot.sell_limit('BTC/USDT', price=75000, amount=0.001)

# Отмена ордера
bot.cancel_order('BTC/USDT', order_id='ORDER_ID')

# Просмотр открытых ордеров
bot.get_open_orders()
```

### Использование торговой стратегии

```python
from crypto_bot import CryptoBot
from trading_strategy import SimpleTradingStrategy

# Создаем бота
bot = CryptoBot(exchange_id='binance')

# Создаем стратегию
strategy = SimpleTradingStrategy(
    bot=bot,
    symbol='BTC/USDT',
    buy_threshold=-2.0,  # Покупать при падении на 2%
    sell_threshold=3.0   # Продавать при росте на 3%
)

# Запускаем стратегию
strategy.run(check_interval=60)  # Проверка каждые 60 секунд
```

## 🔧 Поддерживаемые биржи

Бот поддерживает 100+ бирж через CCXT. Популярные варианты:

- `binance` - Binance
- `bybit` - Bybit
- `okx` - OKX (бывший OKEx)
- `kraken` - Kraken
- `kucoin` - KuCoin
- `huobi` - Huobi
- `gateio` - Gate.io
- `bitfinex` - Bitfinex

Полный список: https://github.com/ccxt/ccxt/wiki/Manual#exchanges

## ⚙️ Конфигурация

### Переменные окружения (.env)

| Переменная | Описание | Пример |
|------------|----------|--------|
| `API_KEY` | API ключ биржи | `abc123...` |
| `API_SECRET` | Secret ключ биржи | `xyz789...` |
| `SANDBOX` | Режим песочницы | `true` / `false` |
| `EXCHANGE_ID` | ID биржи | `binance` |

### Параметры методов

#### get_ohlcv()
- `timeframe`: `'1m'`, `'5m'`, `'15m'`, `'30m'`, `'1h'`, `'2h'`, `'4h'`, `'6h'`, `'12h'`, `'1d'`, `'1w'`
- `limit`: количество свечей (максимум зависит от биржи)

## ⚠️ Важные предупреждения

1. **Безопасность API ключей**
   - Никогда не публикуйте свои API ключи
   - Используйте переменные окружения или файл `.env`
   - Добавьте `.env` в `.gitignore`

2. **Торговля на реальные деньги**
   - Начните с тестового режима (SANDBOX=true)
   - Используйте небольшие суммы для тестирования
   - Помните о рисках потери средств

3. **Ограничения бирж**
   - У каждой биржи есть лимиты на запросы (rate limits)
   - Минимальные размеры ордеров зависят от биржи
   - Некоторые функции могут быть недоступны для определенных бирж

## 📁 Структура проекта

```
/workspace
├── crypto_bot.py          # Основной класс бота
├── trading_strategy.py    # Пример торговой стратегии
├── .env.example           # Шаблон конфигурации
├── .env                   # Ваша конфигурация (не коммитить!)
└── README.md              # Документация
```

## 🔗 Полезные ссылки

- [Документация CCXT](https://github.com/ccxt/ccxt/wiki/)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Bybit API Documentation](https://bybit-exchange.github.io/docs/)
- [Cryptocurrency Trading Bots Guide](https://www.investopedia.com/articles/best-bitcoin-trading-bots.asp)

## 📝 Лицензия

Этот проект предоставляется "как есть" без каких-либо гарантий. 
Используйте на свой страх и риск.

## 💡 Советы по использованию

1. **Начните с демо-счета** - многие биржи предоставляют тестовый режим
2. **Тестируйте стратегию** - прежде чем запускать на реальных деньгах
3. **Мониторьте бота** - не оставляйте без присмотра на долгое время
4. **Устанавливайте стоп-лоссы** - для ограничения убытков
5. **Ведите логирование** - для анализа торговых операций

---

**Удачной торговли! 🚀📈**
