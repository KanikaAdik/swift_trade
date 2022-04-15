import shift, time, csv
from time import sleep
import datetime as dt
from threading import Thread
from collections import defaultdict
from numpy import std, mean

STOCK_LIST =['AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIA', 'DIS', 'GS', 'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'SPY', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM']
filename = "shift.csv"
fields = ['Stock', 'Price', 'Time']

def connect(username, password):
    print("Connecting..", username, password)
    trader = shift.Trader(username)
    try:
        trader.connect("initiator.cfg", "crT4Y3w9")
        return trader
    except Exception as e:
        print("Exception occurred : ", e)
        exit()
    
def market_is_open(trader):
    print (trader.get_last_trade_time())
    #Original start & end time need to set before code release 
    start_time = dt.time(9,30,0)
    end_time = dt.time(15,30,0)
    while start_time > trader.get_last_trade_time().time():
        print("Market not yet open at ", trader.get_last_trade_time().time())
        sleep(10) #recheck after 10 seconds
    print("Market seems to be open!")
    if  trader.get_last_trade_time().time()>end_time:
        print ("Market is Closed")
        return False 
    return True   

def get_price(trader, stock):
    bp= trader.get_best_price(stock)
    return bp.get_bid_price(), bp.get_ask_price()

def print_orderbook(trader):
    print(" Price\t\tSize\t  Dest\t\tTime")
    for order in trader.get_order_book("AAPL", shift.OrderBookType.GLOBAL_BID, 5):
        print("%7.2f\t\t%4d\t%6s\t\t%19s"
        % (order.price, order.size, order.destination, order.time))
    return

def sell_all_shares(trader):
    print("Cancelling pending orders")
    trader.cancel_all_pending_orders()
    print("Selling all shares")
    for item in trader.get_portfolio_items().values():
        lots = item.get_shares()
        if lots!=0:
            lots= int(lots/100)
            order_stock(trader, item.get_symbol(), 'mrkt_sell', lots, 10)
            print ("sold shares --- ", item.get_symbol(),item.get_shares())
    sleep(10)
    return

def collect_data_incsv(trader, end_time):
    csventry=[]
    print("Checking -- ", trader.get_last_trade_time().time(), end_time)
    while end_time:
        for stock in STOCK_LIST:
            price = trader.get_last_price(stock)
            if price ==0:
                continue
            time = trader.get_last_trade_time().time()
            entry=[stock, price, time]
            csventry.append(entry)
        with open(filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)
            csvwriter.writerows(csventry)
        end_time -= 1
        sleep(3)
    return

def market_calls(trader, tickers):
    print("Placing market calls")
    for stock, values in tickers[:10]:
        balance = (trader.get_portfolio_summary().get_total_bp() * 0.1)
        no_of_shares = round(balance/ values[1])
        if no_of_shares< 10 or no_of_shares<100 :
            lot = 1
        else: 
            lot = round(no_of_shares/100)
        order_stock(trader, stock, 'mrkt_buy',lot,  values[1])
    return

def start_trading(trader, tickers_list):
    for stock, values in tickers_list[11:20]:
        #place limit orders on first 15 in the list
        #buying_power 10%
        balance = (trader.get_portfolio_summary().get_total_bp() * 0.1)
        no_of_shares = round(balance/ values[1])
        if no_of_shares< 10 or no_of_shares<100 :
            lot = 1
        else: 
            lot = round(no_of_shares/100)
        order_stock(trader, stock, 'limit_buy',lot,  values[1])
            

    #track for next 1 hr if profit in profile is higher then exit
def check_pending_orders(trader):
    timer = 10#0
    order_executed = False
    while timer:
        for order in trader.get_submitted_orders():
            if order.status == shift.Order.Status.FILLED or order.status == shift.Order.Status.REJECTED:
                order_executed = True
                continue
            else:
                print("Waiting for this order to execute -  %6s\t%16s\t%7.2f\t\t%4d\t\t%4d\t%36s\t%23s\t\t%26s" % (order.symbol, order.type,
    order.price, order.size, order.executed_size, order.id, order.status, order.timestamp,))
        sleep(10)
        timer -= 10

def sell_with_profit(trader):
    for item in trader.get_portfolio_items().values():
        if trader.get_unrealized_pl(item.get_symbol())>1000:
            print("Exit in profit - ", item.get_symbol())
            order_stock(trader, item.get_symbol(), 'mrkt_sell', lots, 10)
        if trader.get_unrealized_pl(item.get_symbol())<-300:
            print("Exiting in loss at market price - ", item.get_symbol())
            lots = item.get_shares()
            lots = int(lots/100)
            order_stock(trader, item.get_symbol(), 'mrkt_sell' , lots, price=5)

def calculate_sd():
    stocks_prices = defaultdict(list)
    std_dev = {}
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stocks_prices[row['Stock']].append(float(row['Price']))
        for stock, salaries in stocks_prices.items():
            std_dev[stock] = [std(salaries), min(salaries), max(salaries), mean(salaries)]
        std_dev = sorted(std_dev.items(), key=lambda item: item[1],reverse=True)
    return std_dev
            

def order_stock(trader, stock, _ordertype, no_lot=10, price=5):
    print("Buying - ", stock, _ordertype,no_lot, price )
    if _ordertype =='limit_buy':
        order = shift.Order(shift.Order.Type.LIMIT_BUY, stock, no_lot, price)
    if _ordertype =='limit_sell':
        order = shift.Order(shift.Order.Type.LIMIT_SELL, stock, no_lot, price)
    if _ordertype == 'mrkt_buy':
        order = shift.Order(shift.Order.Type.MARKET_BUY, stock, no_lot, price)
    if _ordertype == 'mrkt_sell':
        order = shift.Order(shift.Order.Type.MARKET_SELL, stock, no_lot, price)
    trader.submit_order(order)


def show_my_summary(trader):
    print("Buying Power\tTotal Shares\tTotal P&L\tTimestamp")
    print(
    "%12.2f\t%12d\t%9.2f\t%26s"
    % (
        trader.get_portfolio_summary().get_total_bp(),
        trader.get_portfolio_summary().get_total_shares(),
        trader.get_portfolio_summary().get_total_realized_pl(),
        trader.get_portfolio_summary().get_timestamp(),
    ))
    print("Symbol\t\tShares\t\tPrice\t\tP&L\t\tTimestamp")
    for item in trader.get_portfolio_items().values():
        print(
        "%6s\t\t%6d\t%9.2f\t%7.2f\t\t%26s"
        % (
            item.get_symbol(),
            item.get_shares(),
            item.get_price(),
            item.get_realized_pl(),
            item.get_timestamp()  
        ))

def show_orderbook(trader):
    print(
    "Symbol\t\t\t\tType\t  Price\t\tSize\tExecuted\tID\t\t\t\t\t\t\t\t\t\t\t\t\t\t Status\t\tTimestamp"
)
    for order in trader.get_submitted_orders():
        if order.status == shift.Order.Status.FILLED :
            price = order.executed_price
        else:
             price = order.price
        print(
        "%6s\t%16s\t%7.2f\t\t%4d\t\t%4d\t%36s\t%23s\t\t%26s"
        % (
            order.symbol,
            order.type,
            price,
            order.size,
            order.executed_size,
            order.id,
            order.status,
            order.timestamp,
         ))

if __name__ == '__main__' :
    print("Connecting...")
    trader = connect('swift_trade', 'crT4Y3w9')  
    sleep(5) #wait until connection is successful

    trader.sub_all_order_book()
    
    if market_is_open(trader): #or set a timer to exit from all positions
        print("Start Trading!")
        #collect_data_incsv(trader, 600) # for initial purchases get data for next 10 min
        tickers = calculate_sd()
        market_calls(trader, tickers)
        end_time = dt.time(15,30,0)
        while (end_time != trader.get_last_trade_time().time()):
            start_trading(trader,tickers) #buy next 10 on limit
            sell_with_profit(trader) # sell with profits 
    check_pending_orders(trader) 
    sell_all_shares(trader)
    show_orderbook(trader)
    show_my_summary(trader)
    trader.disconnect()