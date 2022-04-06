import shift
from time import sleep
import datetime as dt


def connect(username, password):
     print ("Connecting website -- 155.246.104.90 , %s %s"%(username, password))
     trader = shift.Trader(username)
     try:
          trader.connect("initiator.cfg",password)
          sleep(10)
          trader.sub_all_order_book()
     except Exception as e:
          print("Exception occurred!!! - %s" % e)
     return trader

def market_open(trader):
    d = trader.get_last_trade_time()
    start_time = dt.time(9,30,0)
    print(" trade time :", start_time < trader.get_last_trade_time().time() )
    while start_time > trader.get_last_trade_time().time():
         print("Market not yet open at ", trader.get_last_trade_time())
         sleep(10)
    return True
         

def start_trading(trader):
     if trader.is_connected():
         trader.sub_all_order_book()
         trader.get_subscribed_order_book_list()
         limit_buy = shift.Order(shift.Order.Type.LIMIT_BUY, "AAPL", 1, 10.00)
         trader.submit_order(limit_buy)
         print("Buying Power\tTotal Shares\tTotal P&L\tTimestamp")
         print("%12.2f\t%12d\t%9.2f\t%26s"
         % (
            trader.get_portfolio_summary().get_total_bp(),
            trader.get_portfolio_summary().get_total_shares(),
            trader.get_portfolio_summary().get_total_realized_pl(),
            trader.get_portfolio_summary().get_timestamp(),
         ))

         print("Symbol\t\tShares\t\tPrice\t\t  P&L\tTimestamp")
         for item in trader.get_portfolio_items().values():
            print(
            "%6s\t\t%6d\t%9.2f\t%9.2f\t%26s"
             %(
                item.get_symbol(),
                item.get_shares(),
                item.get_price(),
                item.get_realized_pl(),
                item.get_timestamp(),
             )
         )
         print("Waiting list orders :", trader.get_waiting_list())
         return 
         for order in trader.get_waiting_list():
             trader.submit_cancellation(order)

 
def conclude():
     print("Exit all positions")
      
"""
Starting with basic execution -
1. Connect to the the stock exchange
2. Check Timings to start tracking tickers
3. Get previous ticker close price 
4. Get Previous tickers Volume
5. Build a strategy to execute for one ticker one thread 
"""
if __name__ == '__main__' :
     trader = connect('swift_trade', 'crT4Y3w9')
     if market_open(trader):
         #start_timer() #shoudl notify once end time is approaching
         start_trading(trader)
     
         conclude()
     trader.disconnect()
     