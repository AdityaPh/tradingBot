from lumibot.brokers import Alpaca # Our broker
from lumibot.backtesting import YahooDataBacktesting # Framework for backtesting
from lumibot.strategies.strategy import Strategy # Actual Trading Bot
from lumibot.traders import Trader # Deployment capability to run it live
from datetime import datetime
from alpaca_trade_api import REST # dynamically get news
from timedelta import Timedelta # calculate diff between days, weeks, etc
from finbert_utils import estimate_sentiment

# NOTE: Must hide key, secret before publishing to github!
API_KEY = config.API_KEY
API_SECRET = config.API_SECRET
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY" : API_KEY,
    "API_SECRET" : API_SECRET,
    "PAPER" : True

}

# All of the trading logic goes inside this class
class MLTrader(Strategy):
    def initialize(self, symbol:str="GOOGL", cash_at_risk:float=0.5): # using SPY index for now
        self.symbol = symbol
        self.sleeptime = "24H" # How often we want to trade
        self.last_trade = None # so we can undo buys
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price)
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime() # With respect to backtest 
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start=three_days_prior, end=today)

        news = [ev.__dict__["_raw"]["headline"] for ev in news]

        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment


    # Every time we get new data from our data source
    # we will do an iteration that executes a trade or
    # we will do somehting with it. All trading logic will
    # be encapsulated in the function below:
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        # if there is enough cash, then only buy
        if cash > last_price*quantity: # tutorial did not include quantity but I think you need
        
            if sentiment == 'positive' and probability > 0.999:
                # Close short positions. Sentiment is positive, so
                # I am no longer bearish and cannot benefit from short
                # selling.

                # start long position (sell current open positions
                # since I believe market will rise because sentiment
                # is positive and use that extra cash to buy)
                if self.last_trade == "sell":
                    self.sell_all()
               
                order = self.create_order(
                    self.symbol,
                    quantity, # num shares 
                    "buy",
                    type="bracket",
                    take_profit_price = last_price*1.20,
                    stop_loss_price = last_price*0.95
                )
                self.submit_order(order)
                self.last_trade = "buy"
            
            elif sentiment == 'negative' and probability > 0.999:
                
                # Close long positions (sentiment is negative
                # so no longer am I bullish)
                if self.last_trade == "buy":
                    self.sell_all()
                
                order = self.create_order(
                    self.symbol,
                    quantity, # num shares 
                    "sell",
                    type="bracket",
                    take_profit_price = last_price*0.8,
                    stop_loss_price = last_price*1.05
                )
                self.submit_order(order)
                self.last_trade = "sell"


start_date = datetime(2020, 1, 1)
end_date = datetime(2023, 12, 31)

broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name='mlstrategy', broker=broker,
                    parameters={"symbol" : "GOOGL", 
                                "cash_at_risk" : 0.5})
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol" : "GOOGL", "cash_at_risk" : 0.5}
)
