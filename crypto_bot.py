"""
Crypto Trading Bot - Основной файл бота
Поддерживает работу с Binance, Bybit, OKX и другими биржами через CCXT
"""

import ccxt
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

class CryptoBot:
    def __init__(self, exchange_id='binance', api_key=None, secret=None):
        """
        Инициализация криптобота
        
        :param exchange_id: ID биржи (binance, bybit, okx, etc.)
        :param api_key: API ключ биржи
        :param secret: Secret ключ биржи
        """
        # Получаем учетные данные из переменных окружения, если не переданы
        self.api_key = api_key or os.getenv('API_KEY')
        self.secret = secret or os.getenv('API_SECRET')
        
        # Инициализация биржи
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': self.api_key,
            'secret': self.secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # spot или margin
            }
        })
        
        # Для тестирования можно использовать песочницу
        if os.getenv('SANDBOX', 'false').lower() == 'true':
            self.exchange.set_sandbox_mode(True)
        
        print(f"✓ Бот инициализирован для биржи: {exchange_id.upper()}")
    
    def get_balance(self, currency='USDT'):
        """
        Получить баланс определенной валюты
        
        :param currency: Код валюты (USDT, BTC, ETH, etc.)
        :return: Доступный баланс
        """
        try:
            balance = self.exchange.fetch_balance()
            available = balance['free'].get(currency, 0)
            total = balance['total'].get(currency, 0)
            
            print(f"💰 Баланс {currency}:")
            print(f"   Доступно: {available}")
            print(f"   Всего: {total}")
            
            return {'free': available, 'total': total}
        except Exception as e:
            print(f"❌ Ошибка получения баланса: {e}")
            return None
    
    def get_price(self, symbol='BTC/USDT'):
        """
        Получить текущую цену торговой пары
        
        :param symbol: Торговая пара (BTC/USDT, ETH/USDT, etc.)
        :return: Текущая цена
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            
            print(f"📊 Цена {symbol}: ${price:,.2f}")
            return price
        except Exception as e:
            print(f"❌ Ошибка получения цены: {e}")
            return None
    
    def get_orderbook(self, symbol='BTC/USDT', limit=10):
        """
        Получить стакан заказов
        
        :param symbol: Торговая пара
        :param limit: Количество уровней (до 100)
        :return: Стакан заказов
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            
            print(f"\n📚 Стакан {symbol} (топ-{limit}):")
            print("   Продавцы (asks):")
            for i, ask in enumerate(orderbook['asks'][:5]):
                print(f"      {i+1}. Цена: ${ask[0]:,.2f}, Объем: {ask[1]:.4f}")
            
            print("   Покупатели (bids):")
            for i, bid in enumerate(orderbook['bids'][:5]):
                print(f"      {i+1}. Цена: ${bid[0]:,.2f}, Объем: {bid[1]:.4f}")
            
            return orderbook
        except Exception as e:
            print(f"❌ Ошибка получения стакана: {e}")
            return None
    
    def buy_market(self, symbol='BTC/USDT', amount=None, cost_usdt=None):
        """
        Купить по рыночной цене
        
        :param symbol: Торговая пара
        :param amount: Количество базовой валюты (например, 0.001 BTC)
        :param cost_usdt: Сумма в котируемой валюте (например, 100 USDT)
        :return: Результат ордера
        """
        try:
            if amount:
                # Покупаем определенное количество
                order = self.exchange.create_market_buy_order(symbol, amount)
                print(f"✅ Рыночный ордер на покупку: {amount} {symbol.split('/')[0]}")
            elif cost_usdt:
                # Покупаем на определенную сумму (если биржа поддерживает)
                order = self.exchange.create_market_buy_order(symbol, {'cost': cost_usdt})
                print(f"✅ Рыночный ордер на покупку: на {cost_usdt} USDT")
            else:
                print("❌ Укажите amount или cost_usdt")
                return None
            
            print(f"   ID ордера: {order['id']}")
            print(f"   Статус: {order['status']}")
            print(f"   Цена: ${order.get('average', 0):,.2f}")
            print(f"   Сумма: {order.get('filled', 0)}")
            
            return order
        except Exception as e:
            print(f"❌ Ошибка создания ордера на покупку: {e}")
            return None
    
    def sell_market(self, symbol='BTC/USDT', amount=None):
        """
        Продать по рыночной цене
        
        :param symbol: Торговая пара
        :param amount: Количество для продажи
        :return: Результат ордера
        """
        try:
            if not amount:
                print("❌ Укажите количество для продажи")
                return None
            
            order = self.exchange.create_market_sell_order(symbol, amount)
            
            print(f"✅ Рыночный ордер на продажу: {amount} {symbol.split('/')[0]}")
            print(f"   ID ордера: {order['id']}")
            print(f"   Статус: {order['status']}")
            print(f"   Цена: ${order.get('average', 0):,.2f}")
            
            return order
        except Exception as e:
            print(f"❌ Ошибка создания ордера на продажу: {e}")
            return None
    
    def buy_limit(self, symbol='BTC/USDT', price=None, amount=None):
        """
        Создать лимитный ордер на покупку
        
        :param symbol: Торговая пара
        :param price: Цена покупки
        :param amount: Количество
        :return: Результат ордера
        """
        try:
            if not price or not amount:
                print("❌ Укажите price и amount")
                return None
            
            order = self.exchange.create_limit_buy_order(symbol, amount, price)
            
            print(f"✅ Лимитный ордер на покупку:")
            print(f"   Цена: ${price:,.2f}")
            print(f"   Количество: {amount}")
            print(f"   ID ордера: {order['id']}")
            
            return order
        except Exception as e:
            print(f"❌ Ошибка создания лимитного ордера: {e}")
            return None
    
    def sell_limit(self, symbol='BTC/USDT', price=None, amount=None):
        """
        Создать лимитный ордер на продажу
        
        :param symbol: Торговая пара
        :param price: Цена продажи
        :param amount: Количество
        :return: Результат ордера
        """
        try:
            if not price or not amount:
                print("❌ Укажите price и amount")
                return None
            
            order = self.exchange.create_limit_sell_order(symbol, amount, price)
            
            print(f"✅ Лимитный ордер на продажу:")
            print(f"   Цена: ${price:,.2f}")
            print(f"   Количество: {amount}")
            print(f"   ID ордера: {order['id']}")
            
            return order
        except Exception as e:
            print(f"❌ Ошибка создания лимитного ордера: {e}")
            return None
    
    def cancel_order(self, symbol='BTC/USDT', order_id=None):
        """
        Отменить ордер
        
        :param symbol: Торговая пара
        :param order_id: ID ордера
        :return: Результат отмены
        """
        try:
            if not order_id:
                print("❌ Укажите order_id")
                return None
            
            result = self.exchange.cancel_order(order_id, symbol)
            print(f"✅ Ордер {order_id} отменен")
            
            return result
        except Exception as e:
            print(f"❌ Ошибка отмены ордера: {e}")
            return None
    
    def get_open_orders(self, symbol=None):
        """
        Получить открытые ордера
        
        :param symbol: Торговая пара (опционально)
        :return: Список открытых ордеров
        """
        try:
            if symbol:
                orders = self.exchange.fetch_open_orders(symbol)
            else:
                orders = self.exchange.fetch_open_orders()
            
            print(f"\n📋 Открытые ордера: {len(orders)}")
            for order in orders:
                print(f"   ID: {order['id']}")
                print(f"   Пара: {order['symbol']}")
                print(f"   Тип: {order['type']} / {order['side']}")
                print(f"   Цена: ${order['price']:,.2f}")
                print(f"   Количество: {order['amount']}")
                print(f"   Заполнено: {order['filled']}")
                print("-" * 40)
            
            return orders
        except Exception as e:
            print(f"❌ Ошибка получения открытых ордеров: {e}")
            return []
    
    def get_ohlcv(self, symbol='BTC/USDT', timeframe='1h', limit=100):
        """
        Получить свечи (OHLCV данные)
        
        :param symbol: Торговая пара
        :param timeframe: Таймфрейм (1m, 5m, 15m, 1h, 4h, 1d)
        :param limit: Количество свечей
        :return: Данные свечей
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            
            print(f"\n🕯️ Свечи {symbol} ({timeframe}):")
            print(f"   Получено свечей: {len(ohlcv)}")
            
            if ohlcv:
                last = ohlcv[-1]
                timestamp = datetime.fromtimestamp(last[0]/1000).strftime('%Y-%m-%d %H:%M')
                print(f"   Последняя свеча: {timestamp}")
                print(f"   Open: ${last[1]:,.2f}")
                print(f"   High: ${last[2]:,.2f}")
                print(f"   Low: ${last[3]:,.2f}")
                print(f"   Close: ${last[4]:,.2f}")
                print(f"   Volume: {last[5]:.2f}")
            
            return ohlcv
        except Exception as e:
            print(f"❌ Ошибка получения свечей: {e}")
            return []


def main():
    """
    Пример использования бота
    """
    print("=" * 60)
    print("🤖 CRYPTO TRADING BOT")
    print("=" * 60)
    
    # Создаем экземпляр бота
    # Для реальной торговли добавьте API ключи в .env файл или передайте напрямую
    bot = CryptoBot(exchange_id='binance')
    
    # Примеры использования:
    
    # 1. Получить баланс
    print("\n" + "=" * 60)
    bot.get_balance('USDT')
    
    # 2. Получить цену
    print("\n" + "=" * 60)
    bot.get_price('BTC/USDT')
    bot.get_price('ETH/USDT')
    
    # 3. Получить стакан
    print("\n" + "=" * 60)
    bot.get_orderbook('BTC/USDT', limit=10)
    
    # 4. Получить свечи
    print("\n" + "=" * 60)
    bot.get_ohlcv('BTC/USDT', timeframe='1h', limit=10)
    
    # 5. Получить открытые ордера
    print("\n" + "=" * 60)
    bot.get_open_orders()
    
    # === ТОРГОВЫЕ ОПЕРАЦИИ (раскомментируйте для использования) ===
    # Внимание: Для реальных операций нужны API ключи с правами на торговлю!
    
    # Рыночная покупка на 100 USDT
    # bot.buy_market('BTC/USDT', cost_usdt=100)
    
    # Рыночная покупка 0.001 BTC
    # bot.buy_market('BTC/USDT', amount=0.001)
    
    # Лимитная покупка
    # current_price = bot.get_price('BTC/USDT')
    # if current_price:
    #     bot.buy_limit('BTC/USDT', price=current_price * 0.98, amount=0.001)
    
    # Рыночная продажа
    # bot.sell_market('BTC/USDT', amount=0.001)
    
    # Лимитная продажа
    # bot.sell_limit('BTC/USDT', price=70000, amount=0.001)
    
    # Отмена ордера
    # bot.cancel_order('BTC/USDT', order_id='YOUR_ORDER_ID')
    
    print("\n" + "=" * 60)
    print("✅ Бот готов к работе!")
    print("=" * 60)


if __name__ == '__main__':
    main()
