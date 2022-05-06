from hashlib import new
from tkinter import SEL_LAST
import shift 
import threading, csv, os
import datetime as dt
from time import sleep
import pandas as pd
import numpy as np

START_TIME = dt.time(9,30,0)
END_TIME = dt.time(15,45,0)
PATH= os.path.join(os.getcwd(), "CSVFILES")

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

def get_price(trader, stock):
    """
    Fucntion to - Get the best price of a stock
    returns Ask price, Bid Price , Ask Size & Bid size 
    """
    bp= trader.get_best_price(stock)
    return bp.get_bid_price(), bp.get_bid_size(), bp.get_ask_price(), bp.get_ask_size()

def collect_data(trader):
    """
    Function to - Collect data on a timely basis until end time occurs
        Will keep on adding data till the end of market closure i.e. 4 pm
        Get current value of a stock bid and ask price with current time
        Calculate average and standard deviation
    """
    while (END_TIME > trader.get_last_trade_time().time()): 
        #print("DB collection dozzing off 10 sec...Zzzzz!!!")
        sleep(1) #wait for next 5 sec to update prices in respective csv files
        for stock_symbol in trader.get_stock_list():
            prices = get_price(trader, stock_symbol)
            time = trader.get_last_trade_time().time()
            last_price = trader.get_last_price(stock_symbol)
            entry=[last_price, prices[0], prices[2], prices[1], prices[3], prices[2]-prices[0], time]
            file= os.path.join(PATH,stock_symbol+".csv")
            with open(file, 'a') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(entry)
     
def checkif_order_placed(trader, stock_symbol, new_size, new_price, new_type):
    for order in trader.get_submitted_orders():
        if order.symbol == stock_symbol:
            if order.status in [shift.Order.Status.PENDING_NEW, shift.Order.Status.NEW,shift.Order.Status.PARTIALLY_FILLED]:
                print("comparinf --", order.size,new_size,order.price,new_price, order.type, new_type )
                if order.size == new_size and order.price == new_price and str(order.type)== str(new_type):
                    print("order exists")
                    return True
    return False

def order_stock(trader, stock, _ordertype, no_lot=10, price=10):
    if _ordertype =='limit_buy':
        if  checkif_order_placed(trader, stock, no_lot, price, "Type.LIMIT_BUY"):
            return 
        order = shift.Order(shift.Order.Type.LIMIT_BUY, stock, no_lot, price)
    if _ordertype =='limit_sell':
        if  checkif_order_placed(trader, stock, no_lot, price, "Type.LIMIT_SELL"):
            return 
        order = shift.Order(shift.Order.Type.LIMIT_SELL, stock, no_lot, price)
    if _ordertype == 'mrkt_buy':
        if  checkif_order_placed(trader, stock, no_lot, price, "Type.MARKET_BUY"):
            return 
        order = shift.Order(shift.Order.Type.MARKET_BUY, stock, no_lot, price)
    if _ordertype == 'mrkt_sell':
        if  checkif_order_placed(trader, stock, no_lot, price, "Type.MARKET_SELL"):
            return 
        order = shift.Order(shift.Order.Type.MARKET_SELL, stock, no_lot, price)
    print("Placing Order Call details - ", stock, _ordertype, no_lot, price )
    trader.submit_order(order)
    
def check_trend(data_collected):
    spread = data_collected['Spread']
    liquidity = round(spread.mean(),2)
    if data_collected['Bid Volume'].sum()> data_collected['Ask Volume'].sum(): # market trend is BEARISH
        trend = 'BEARISH'
    elif data_collected['Bid Volume'].sum()< data_collected['Ask Volume'].sum(): # market trend is BULLISH
        trend = 'BULLISH'
    if liquidity < 0.1 and trend == 'BEARISH':
        return 'SELL_ST'  #Place limit calls for SELL Long term  
    if liquidity > 0.1 and trend == 'BEARISH':
        return 'SELL_LT' #Place limit calls for SELL Short term 
    if liquidity <= 0.1 and trend == 'BULLISH':
        return 'BUY_ST'  #Place limit calls for BUY Long term  
    if liquidity >= 0.1 and trend == 'BULLISH':
        return 'BUY_LT' #Place limit calls for BUY Short term 
    return 'NO_NE'

def calculate_no_of_lots(balance, price):
    no_of_shares = round(balance/price)
    if no_of_shares< 10 or no_of_shares<100 :
        no_of_lots = 1
    else:
        no_of_lots = round(no_of_shares/100)
    return no_of_lots

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


def check_stock(trader, stock_symbol):
    print("Keep on Checking stock in the check_stock:", stock_symbol)
    file_name  = os.path.join(os.getcwd(),"CSVFILES", stock_symbol+".csv")
    cleanup_timer =1800
    freshstart = 4
    while (END_TIME > trader.get_last_trade_time().time()):
        data_collected = pd.read_csv(file_name)
        trend = check_trend(data_collected)
        print("TREND-", trend)
        item = trader.get_portfolio_item(stock_symbol)
        if item.get_shares() !=0 : # you are already holding
            print ("You are holding {} stocks of {} with  buy rate {} current rate of {} and P/L as - {}".format(item.get_shares(), stock_symbol, item.get_price(),trader.get_last_price(stock_symbol), trader.get_unrealized_pl(stock_symbol)))
            if trader.get_unrealized_pl(stock_symbol)>0: #we are making profits
                #place more Buy limit orders on top of existing share holdings 
                if item.get_shares()>0:#BUY SECTION profits
                    no_of_lots = int(item.get_shares()/100)
                    highest_spread_price =  item.get_price() + data_collected['Spread'].max()
                    if  trader.get_last_price(stock_symbol) > highest_spread_price : #10 percent profits made exit
                        print("Profits are 10% above exiting")
                        order_stock(trader, stock_symbol, 'mrkt_sell' , no_of_lots, price)
                        continue
                    no_of_lots = int(round(0.5 * (item.get_shares()/100)))
                    price = data_collected['Ask Price'].min()
                    order_stock(trader, stock_symbol, 'limit_buy' , no_of_lots, price)
                elif item.get_shares()<0:
                    no_of_lots = int(item.get_shares()/100)
                    lowest_spread_price =  item.get_price() - data_collected['Spread'].max()
                    if  trader.get_last_price(stock_symbol) < lowest_spread_price : #10 percent profits made exit
                        print("Profits are 10% above exiting")
                        order_stock(trader, stock_symbol, 'mrkt_buy' , no_of_lots, price)
                        continue
                    no_of_lots = int(round(0.5 * (item.get_shares()/100)))
                    price = data_collected['Bid Price'].max()
                    order_stock(trader, stock_symbol, 'limit_sell' , no_of_lots, price)
            elif trader.get_unrealized_pl(stock_symbol)<0: # we are in loss
                #place more Sell limit orders on top of existing share holdings
                ten_percent_price = item.get_price() - item.get_price()*0.08
                if ten_percent_price > trader.get_last_price(stock_symbol): #losses are higher than 8% then exit
                    order_stock(trader, stock_symbol, 'mrkt_sell' , no_of_lots, price)
                    continue
                if item.get_shares()>0: #positive i.e. you had BUY you need to sell
                    no_of_lots = int(round(0.5 * (item.get_shares()/100)))
                    price = data_collected['Bid Price'].max()
                    order_stock(trader, stock_symbol, 'limit_sell' , no_of_lots, price)
                elif item.get_shares()<0: #negative i.e. you had SELL
                    no_of_lots = int(round(0.5 * (item.get_shares()/100)))
                    price = data_collected['Ask Price'].max()
                    order_stock(trader, stock_symbol, 'limit_buy' , no_of_lots, price)      
        else: #placing new calls
            trend = trend.split("_") #Check trend and place orders
            buying_power = trader.get_portfolio_summary().get_total_bp()

            price = trader.get_last_price(stock_symbol)
            if trend[1] == "LT": #purchase for Long term , low liquidity rate
                buying_power = buying_power*0.25
                if trend[0] == "BUY": 
                    no_of_lots = calculate_no_of_lots(buying_power, price)
                    price = data_collected['Ask Price'].min()
                    order_stock(trader, stock_symbol, 'limit_buy' , no_of_lots, price)
                elif trend[0] == "SELL":
                    no_of_lots = calculate_no_of_lots(buying_power, price)
                    price = data_collected['Bid Price'].max()
                    order_stock(trader, stock_symbol, 'limit_sell' , no_of_lots, price)
            elif trend[1] == "ST": #purchase short term for quick orders
                buying_power = buying_power*0.4
                if trend[0] == "BUY": 
                    no_of_lots = calculate_no_of_lots(buying_power, price)
                    order_stock(trader, stock_symbol, 'mrkt_buy' , no_of_lots, price)
                    price = price + (price * 0.05)
                    order_stock(trader, stock_symbol, 'limit_sell' , no_of_lots, price)
                elif trend[0] == "SELL":
                    no_of_lots = calculate_no_of_lots(buying_power, trader.get_last_price(stock_symbol))
                    order_stock(trader, stock_symbol, 'mrkt_sell' , no_of_lots, price)
                    price = price - (price * 0.05)
                    order_stock(trader, stock_symbol, 'limit_buy' , no_of_lots, price)
            else:
                print ("no trend")
        #for all executed orders set selling price
        for order in trader.get_submitted_orders():
            if order.symbol == stock_symbol:
                if order.status == shift.Order.Status.FILLED:
                    if str(order.type) == str("Type.LIMIT_BUY"):
                        price = order.executed_price + order.executed_price * 0.05
                        order_stock(trader, order.symbol , 'limit_sell' , order.executed_size, price)
                    elif str(order.type) == str("Type.LIMIT_SELL"):
                        price = order.executed_price - order.executed_price * 0.05
                        order_stock(trader, order.symbol , 'limit_buy' , order.executed_size, price)
        sleep(1)
        cleanup_timer = cleanup_timer -1
        if cleanup_timer ==0:
            show_summary(trader) 
            trader.cancel_all_pending_orders()
            cleanup_timer =1800 #cleanign up pending orders after half hr
            freshstart = freshstart -1
            if freshstart == 0:
                sell_all_shares(trader)
                freshstart=5


if __name__ == "__main__":
    #Connect to the Stock Exchange
    try:
        trader = connect('swift_trade', 'crT4Y3w9')  
        sleep(5) #wait until connection is successful for further executions
        trader.sub_all_order_book()
        
        #if market is open start data collection and trading individual stocks
        if market_is_open(trader): 
            print("Start Trading!")
            #Starting data collection in respective file
            show_summary(trader) 
            t1 = threading.Thread(target=collect_data, args=(trader, ))
            t1.start()

            #Create Multiple Threads for each Stock to check
            sleep(100)
            thread_list = []
            for a_stock in trader.get_stock_list():
                thread = threading.Thread(target=check_stock, args=(trader, a_stock, ))
                thread_list.append(thread)
                thread.start()
           
            t1.join()
            for a_thread in thread_list:
                a_thread.join() 
            
        print("DONE")
        trader.disconnect() 
    except Exception as e:
        print("Uncaught exception- ", e)