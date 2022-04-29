import shift 
import threading, csv, os
import datetime as dt
from time import sleep
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate

START_TIME = dt.time(9,30,0)
END_TIME = dt.time(15,45,0)

PATH= os.path.join(os.getcwd(), "CSVFILES")
SHORT_TRADE_STOCKS=[]
LONG_TRADE_STOCKS=[]
def connect(username, password):
    """
    Function to - Connect to Stock exchage with username and password creds and initiator.cfg configuration
    - uses shift library to connect
    - if connection not successful check the Exceptions 
    - code will exit on exception
    """
    print("Connecting..", username, password)
    trader = shift.Trader(username)
    try:
        trader.connect("initiator.cfg", password)
        return trader
    except Exception as e:
        print("Exception occurred : ", e)
        exit()

def market_is_open(trader):
    """
    Function to - 
    Checking if Market is open,
        start_time - set to 9:30 am
        end_time - set as 3:45 pm
        if yet to start, will recheck every 10 seconds
        Once open checks if the end time is past, then market should be closed
    Retuns: Boolean 
    True - if market is open
    False if market is close
    """
    #Original start & end time need to set before code release 
    while START_TIME > trader.get_last_trade_time().time():
        print("Market not yet open at ", trader.get_last_trade_time().time())
        sleep(10) #recheck after 10 seconds
    print("Market seems to be open! Current time - ", trader.get_last_trade_time().time())
    if  trader.get_last_trade_time().time()>END_TIME:
        print ("Market is Closed. Current time - ", trader.get_last_trade_time().time())
        return False 
    #Create a csv file to collect data 
    os.mkdir(PATH)
    print("Directory created successfully -", PATH)
    for stock_symbol in trader.get_stock_list():
        with open(os.path.join(PATH,stock_symbol+".csv"),  'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Last Price', 'Bid Price','Ask Price', 'Bid Volume','Ask Volume', 'Spread', 'Time']) 
    print ("CSV Files created successfully")
    return True 

def get_price(trader, stock):
    """
    Fucntion to - Get the best price of a stock
    returns Ask price, Bid Price , Ask Size & Bid size 
    """
    bp= trader.get_best_price(stock)
    return bp.get_bid_price(), bp.get_bid_size(), bp.get_ask_price(), bp.get_ask_size()

def sell_all_shares(trader):
    """
    Very last function to be executed to sell all the stocks owned so far P/L 
    """
    print("Cancelling pending orders")
    trader.cancel_all_pending_orders()
    print("Selling all shares")
    for item in trader.get_portfolio_items().values():
        lots = item.get_shares()
        if lots!=0:
            lots= int(lots/100)
            if lots <0 :
                #lots= abs(lots)
                order_stock(trader, item.get_symbol(), 'mrkt_buy', abs(lots), 10)
                print("settled for shares --- ", item.get_symbol(),item.get_shares() )
            else:
                order_stock(trader, item.get_symbol(), 'mrkt_sell', lots, 10)
                print ("sold shares --- ", item.get_symbol(),item.get_shares())
    sleep(10)
    return

def order_stock(trader, stock, _ordertype, no_lot=10, price=10):
    print("Order Call details - ", stock, _ordertype, no_lot, price )
    if _ordertype =='limit_buy':
        order = shift.Order(shift.Order.Type.LIMIT_BUY, stock, no_lot, price)
    if _ordertype =='limit_sell':
        order = shift.Order(shift.Order.Type.LIMIT_SELL, stock, no_lot, price)
    if _ordertype == 'mrkt_buy':
        order = shift.Order(shift.Order.Type.MARKET_BUY, stock, no_lot, price)
    if _ordertype == 'mrkt_sell':
        order = shift.Order(shift.Order.Type.MARKET_SELL, stock, no_lot, price)
    trader.submit_order(order)

def show_summary(trader):
    """
    Function to -
    Show current buying power of your account
    Number of shares holding
    Shares with waiting list
    """
    print("Buying Power\tTotal Shares\tTotal P&L\tTimestamp")
    print( "%12.2f\t%12d\t%9.2f\t%26s"
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
    print("Shares with Waiting List .. \nSymbol\t\t\t\tType\t  Price\t\tSize\tExecuted\tID\t\t\t\t\t\t\t\t\t\t\t\t\t\t Status\t\tTimestamp"
)
    for order in trader.get_waiting_list():
        print(
        "%6s\t%16s\t%7.2f\t\t%4d\t\t%4d\t%36s\t%23s\t\t%26s"
        % (
            order.symbol,
            order.type,
            order.price,
            order.size,
            order.executed_size,
            order.id,
            order.status,
            order.timestamp,
        )
    )

def calculate_no_of_lots(trader, lowest_price):
    balance = (trader.get_portfolio_summary().get_total_bp() * 0.1)
    no_of_shares = round(balance/lowest_price)
    if no_of_shares< 10 or no_of_shares<100 :
        no_of_lots = 1
    else:
        no_of_lots = round(no_of_shares/100)
    return no_of_lots

def collect_data(trader):
    """
    Function to - Collect data on a timely basis until end time occurs
        Will keep on adding data till the end of market closure i.e. 4 pm
        Get current value of a stock bid and ask price with current time
        Calculate average and standard deviation
    """
    while (END_TIME > trader.get_last_trade_time().time()): 
        #print("DB collection dozzing off 10 sec...Zzzzz!!!")
        sleep(3) #wait for next 5 sec to update prices in respective csv files
        for stock_symbol in trader.get_stock_list():
            prices = get_price(trader, stock_symbol)
            time = trader.get_last_trade_time().time()
            last_price = trader.get_last_price(stock_symbol)
            entry=[last_price, prices[0], prices[2], prices[1], prices[3], prices[2]-prices[0], time]
            file= os.path.join(PATH,stock_symbol+".csv")
            with open(file, 'a') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(entry)
    return
    

def check_stock(trader, stock_symbol):
    """
    Function to Check Stock value and do following based on the status
    1. Order Market Buy stock if value is low than average
    2. Sell the stock if value is high (higher than its prevous highest if lower then sell)
    3. Order stock to Sell the 

    Steps -
    Read the stock file
    Get highest & lowest
    Check spread 
    Calculate sma
    """
    show_summary(trader)
    print("Keep on Checking stock in the check_stock:", stock_symbol)
    file_name  = os.path.join(os.getcwd(),"CSVFILES", stock_symbol+".csv")
    prev_signal = signal = 0
    while (END_TIME > trader.get_last_trade_time().time()):
        data_collected = pd.read_csv(file_name)
        #average of spread, volume trend if it is going up or down
        # if average of spread is lower i.e. within 0.05, we can place short moving average calls
        # Short moving calls meaning SMA of - 20 rolling values
        # Compared with Long EMA of - 200 rolling value
        stock_df = calculate_sma(data_collected, 'Last Price', 5, 20)
        stock_df = calculate_ema(stock_df, 'Last Price', 200)
        # create a new column 'Signal' such that if faster moving average is greater than slower moving average 
        # then set Signal as 1 else 0.
        stock_df['Signal'] = 0.0  
        stock_df['Signal'] = np.where(stock_df['SMA20'] > stock_df['EMA200'], 1.0, 0.0) 
        prev_signal = signal
        signal = stock_df.iloc[-1:]['Signal'].values[0]
        df = stock_df.iloc[-1:]
        no_of_lots = calculate_no_of_lots(trader, stock_df['Last Price'].min())
        item = trader.get_portfolio_item(stock_symbol)
        if prev_signal == signal: # Signal is same as before hence NO ACTION 
            #Check if you are holding any stock if yes then sleep if no place a new order
            if item.get_shares() !=0 : # you are holding shares  check profit or loss
                print ("You are holding {} stocks of {} with current rate of {} and P/L as - {}".format(item.get_shares(), stock_symbol, item.get_price(), trader.get_unrealized_pl(stock_symbol)))
                sleep(5)
                continue
            elif item.get_shares() == 0:
                print("Placing a new Order as per the current signal status")
                if signal == 1:
                    order_stock(trader, stock_symbol, 'mrkt_buy' , no_of_lots)
                elif signal == 0:
                    print("Placing in prev signal and current equal get share equals zero", no_of_lots)
                    order_stock(trader, stock_symbol, 'mrkt_sell' , no_of_lots)
        elif prev_signal != signal: #Signal  has changed need to take action
            no_of_lots = int(item.get_shares()/100)
            if signal == 1:
                #check if already holding if yes - sell those shares if not BUY
                if no_of_lots !=0: # you are holding shares SELL or BUY them to release
                    if no_of_lots < 0:
                        order_stock(trader, stock_symbol, 'mrkt_buy', abs(no_of_lots), 10)
                    elif no_of_lots > 0:
                        order_stock(trader, stock_symbol, 'mrkt_sell' , no_of_lots, 10)
                else: #you do not hold any shares for this stock you can place a new order based on signal
                    order_stock(trader, stock_symbol, 'limit_buy' , no_of_lots, price=df["Last Price"])
            elif signal ==0:
                if no_of_lots !=0: # you are holding shares SELL or BUY them to release
                    if no_of_lots < 0:
                        order_stock(trader, stock_symbol, 'mrkt_buy' , abs(no_of_lots), 10)
                    elif no_of_lots > 0:
                        order_stock(trader, stock_symbol, 'mrkt_sell' , no_of_lots, 10)
                else: #you do not hold any shares for this stock you can place a new order based on signal
                    order_stock(trader, stock_symbol, 'limit_sell' , no_of_lots, price=df["Last Price"])

        sleep(1)
        
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
            order.symbol, order.type,  price, order.size, order.executed_size, order.id,
            order.status, order.timestamp,
         ))

def calculate_sma(df, column, short_period, long_period):
    """
    Function to -
    Calculate Simple Moving Avergae of a Data frame , for a given rolling period 
    """
    short_period_column = "SMA"+str(short_period)
    long_period_column = "SMA"+str(long_period)
    df[short_period_column] = df[column].rolling(short_period).mean()
    df[long_period_column] = df[column].rolling(long_period).mean()
    df.dropna(inplace=True)
    return df 

def calculate_ema(stock_df, column, rolling_period):
    """
    Function to -
    Calculate Simple Moving Avergae of a Data frame , for a given rolling period 
    """
    ema_column="EMA"+str(rolling_period)
    stock_df[ema_column] = stock_df[column].ewm(span = rolling_period, adjust = False).mean()
    stock_df.dropna(inplace=True)
    return stock_df

if __name__ == "__main__":
    #Connect to the Stock Exchange
    try:
        trader = connect('swift_trade', 'crT4Y3w9')  
        sleep(5) #wait until connection is successful for further executions
        trader.sub_all_order_book()
        sell_all_shares(trader)
        
        #if market is open start data collection and trading individual stocks
        if market_is_open(trader): 
            print("Start Trading!")
            #Starting data collection in respective file
            t1 = threading.Thread(target=collect_data, args=(trader, ))
            t1.start()

            #Create Multiple Threads for each Stock to check
            sleep(450)
            thread_list = []
            for a_stock in trader.get_stock_list():
                thread = threading.Thread(target=check_stock, args=(trader, a_stock, ))
                thread_list.append(thread)
                thread.start()
           
            t1.join()
            for a_thread in thread_list:
                a_thread.join() 
            
        print("DONE")

        show_orderbook(trader)
        #show_summary(trader)
        #cancel_pending_orders(trader)
        sell_all_shares(trader)
        show_summary(trader)
        trader.disconnect() 
    except Exception as e:
        print("Uncaught exception- ", e)