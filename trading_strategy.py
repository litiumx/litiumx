"""
Простая торговая стратегия для криптобота
Стратегия: Покупка при падении цены на X%, продажа при росте на Y%
"""

import time
from datetime import datetime
from crypto_bot import CryptoBot


class SimpleTradingStrategy:
    def __init__(self, bot, symbol='BTC/USDT', buy_threshold=-2.0, sell_threshold=3.0):
        """
        Инициализация простой торговой стратегии
        
        :param bot: Экземпляр CryptoBot
        :param symbol: Торговая пара
        :param buy_threshold: Процент падения для покупки (отрицательное число)
        :param sell_threshold: Процент роста для продажи (положительное число)
        """
        self.bot = bot
        self.symbol = symbol
        self.buy_threshold = buy_threshold  # -2.0 означает падение на 2%
        self.sell_threshold = sell_threshold  # 3.0 означает рост на 3%
        
        self.base_price = None
        self.position = None  # {'type': 'buy', 'price': X, 'amount': Y}
        self.in_position = False
        
        print(f"\n📊 Стратегия инициализирована:")
        print(f"   Пара: {symbol}")
        print(f"   Покупка при падении: {buy_threshold}%")
        print(f"   Продажа при росте: {sell_threshold}%")
    
    def get_price_change_percent(self, current_price):
        """
        Вычислить процент изменения цены от базовой
        
        :param current_price: Текущая цена
        :return: Процент изменения
        """
        if not self.base_price:
            return 0
        
        change = ((current_price - self.base_price) / self.base_price) * 100
        return change
    
    def update_base_price(self):
        """Обновить базовую цену до текущей рыночной"""
        price = self.bot.get_price(self.symbol)
        if price:
            self.base_price = price
            print(f"   📍 Базовая цена обновлена: ${price:,.2f}")
            return price
        return None
    
    def check_and_trade(self):
        """
        Проверить условия и выполнить торговлю
        Возвращает: 'buy', 'sell', или None
        """
        if not self.base_price:
            print("⚠️ Базовая цена не установлена")
            return None
        
        current_price = self.bot.get_price(self.symbol)
        if not current_price:
            return None
        
        change_percent = self.get_price_change_percent(current_price)
        
        print(f"\n📈 Анализ рынка:")
        print(f"   Базовая цена: ${self.base_price:,.2f}")
        print(f"   Текущая цена: ${current_price:,.2f}")
        print(f"   Изменение: {change_percent:+.2f}%")
        
        # Логика покупки
        if not self.in_position and change_percent <= self.buy_threshold:
            print(f"\n💡 СИГНАЛ НА ПОКУПКУ! (падение на {change_percent:.2f}%)")
            
            # Пример: покупка на 100 USDT
            balance = self.bot.get_balance('USDT')
            if balance and balance['free'] >= 100:
                # Раскомментируйте для реальной торговли:
                # order = self.bot.buy_market(self.symbol, cost_usdt=100)
                
                # Для демонстрации просто сохраняем позицию
                self.position = {
                    'type': 'buy',
                    'price': current_price,
                    'timestamp': datetime.now()
                }
                self.in_position = True
                print(f"   ✅ Позиция открыта по цене: ${current_price:,.2f}")
                return 'buy'
            else:
                print("   ⚠️ Недостаточно средств на балансе")
                return None
        
        # Логика продажи
        elif self.in_position and change_percent >= self.sell_threshold:
            print(f"\n💡 СИГНАЛ НА ПРОДАЖУ! (рост на {change_percent:.2f}%)")
            
            if self.position:
                profit_percent = ((current_price - self.position['price']) / self.position['price']) * 100
                
                # Раскомментируйте для реальной торговли:
                # order = self.bot.sell_market(self.symbol, amount=your_amount)
                
                print(f"   ✅ Позиция закрывается по цене: ${current_price:,.2f}")
                print(f"   💰 Прибыль: {profit_percent:+.2f}%")
                
                self.position = None
                self.in_position = False
                return 'sell'
        
        else:
            print(f"   ⏳ Нет сигналов для торговли")
            return None
    
    def run(self, check_interval=60):
        """
        Запустить непрерывный мониторинг и торговлю
        
        :param check_interval: Интервал проверки в секундах
        """
        print(f"\n🚀 Запуск торгового бота...")
        print(f"   Интервал проверки: {check_interval} сек")
        print(f"   Нажмите Ctrl+C для остановки\n")
        
        # Установить начальную базовую цену
        self.update_base_price()
        
        try:
            while True:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n[{timestamp}] Проверка рынка...")
                
                self.check_and_trade()
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n\n⛔ Остановка бота по команде пользователя")
            if self.position:
                print(f"⚠️ У вас осталась открытая позиция по цене: ${self.position['price']:,.2f}")
        except Exception as e:
            print(f"\n❌ Ошибка в работе бота: {e}")


def main():
    """
    Пример запуска торговой стратегии
    """
    print("=" * 60)
    print("🤖 SIMPLE TRADING STRATEGY")
    print("=" * 60)
    
    # Создаем бота
    bot = CryptoBot(exchange_id='binance')
    
    # Создаем стратегию
    strategy = SimpleTradingStrategy(
        bot=bot,
        symbol='BTC/USDT',
        buy_threshold=-2.0,  # Покупать при падении на 2%
        sell_threshold=3.0   # Продавать при росте на 3%
    )
    
    # Запускаем стратегию с проверкой каждые 60 секунд
    # Для тестирования можно установить меньший интервал
    strategy.run(check_interval=60)


if __name__ == '__main__':
    main()
