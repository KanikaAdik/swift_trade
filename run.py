
from hashlib import new
from pickle import TRUE
from pydoc import describe
from tkinter import SEL_LAST
import shift 
import threading, csv, os
import datetime as dt
from time import sleep
import pandas as pd
import numpy as np
import math
from decimal import Decimal

trader=None
file_name = os.path.join(os.getcwd(), "CSVFILES")
START_TIME = dt.time(9,30,0)
END_TIME = dt.time(15,45,0)
PATH= os.path.join(os.getcwd(), "CSVFILES")

#ORDER STATIC DATA
LOOP_INTERVAL = 5
ORDER_PAIR=6
ORDER_START_SIZE = 100
ORDER_STEP_SIZE = 100

API_REST_INTERVAL=2 

INTERVAL =0.005

TIMEOUT=7

CHECK_POSITIONLIMIT=True
MIN_POSITION = -1000
MAX_POSITION = 1000

#SINGLE STOCK MIN SPREAD And Condition
MIN_SPREAD=0.01
RELIST_INTERVAL=0.01 #1%


def connect(username, password):
    """
    Function to - Connect to Stock exchage with username and password 
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

def market_is_open():
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

def get_price(stock):
    """
    Fucntion to - Get the best price of a stock
    returns Ask price, Bid Price , Ask Size & Bid size 
    """
    bp= trader.get_best_price(stock)
    return bp.get_bid_price(), bp.get_bid_size(), bp.get_ask_price(), bp.get_ask_size()

def collect_data():
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
            prices = get_price(stock_symbol)
            time = trader.get_last_trade_time().time()
            last_price = trader.get_last_price(stock_symbol)
            entry=[last_price, prices[0], prices[2], prices[1], prices[3], prices[2]-prices[0], time]
            file= os.path.join(PATH,stock_symbol+".csv")
            with open(file, 'a') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(entry)

def get_waitinglistorders():
    waiting_list={}
    for order in trader.get_waiting_list():
        waiting_list[order.symbol]= {'type': order.type, 
                                    'price': order.price,
                                    'size': order.size,
                                    'executed':order.executed_size,
                                    'status': order.status,
                                    'id': order.id
        }
    return waiting_list

def get_summary():
    portfolio = {'buyingpower': trader.get_portfolio_summary().get_total_bp(),
                  'pnl': trader.get_portfolio_summary().get_total_shares(),
                  'ts': trader.get_portfolio_summary().get_timestamp(),
                  'stocks':[]}
    for item in trader.get_portfolio_items().values():
        portfolio['stocks'].append(item.get_symbol())
        portfolio[item.get_symbol()]={'noofshares': item.get_shares(), 
                                      'buyprice':item.get_price(), 
                                      'pnl': item.get_realized_pl()}
    return portfolio

def get_orderbook():
    holding={}
    pending={}
    rejected={}
    for order in trader.get_submitted_orders():
        if order.status == shift.Order.Status.FILLED :
            holding[order.symbol] = {'type': order.status,'price': order.executed_price, 'size': order.size,
                                    'executed_size': order.executed_size, 'id': order.id, 'status': order.status}
        elif order.status == shift.Order.Status.REJECTED :
            rejected[order.symbol] = {'type': order.status,'price': order.executed_price, 'size': order.size,
                         'executed_size': order.executed_size, 'id': order.id, 'status': order.status}
        else:
            pending[order.symbol] = {'type': order.status,'price': order.executed_price, 'size': order.size,
                         'executed_size': order.executed_size, 'id': order.id, 'status': order.status}
    print("HOLDING: ", holding, "\n\nREJECTED:", rejected,"\n\n\nPENDING", pending)

def get_all_tickers():
    all_ticker = []
    for ticker in trader.get_stock_list():
        bp= trader.get_best_price(ticker)
        all_ticker[ticker] = {'bid_price':bp.get_bid_price(),
                             'bid_size': bp.get_bid_size() ,
                             'ask_price': bp.get_ask_price(),
                             'ask_size':bp.get_ask_size()}

def short_position_calls_exceeded(portfolio, ticker):
    if not CHECK_POSITIONLIMIT:
        return False
    if not portfolio['stocks']:
        return False
    noofholding = portfolio[ticker]['noofshares'] #get_current holding if short limit is exceeded
    print("i short prosiotn calls:", noofholding  )
    return  noofholding < MIN_POSITION 

def long_position_calls_exceeded(portfolio, ticker): # if long position limit is exceeded
    if not CHECK_POSITIONLIMIT:
        return False
    if not portfolio['stocks']:
        return False
    noofholding = portfolio[ticker]['noofshares'] #get_current holdings
    print("i short prosiotn calls:", noofholding  )
    return  noofholding > MAX_POSITION 


def toNearest(num, tickSize):
    """Given a number, round it to the nearest tick. Very useful for sussing float error
       out of numbers: e.g. toNearest(401.46, 0.01) -> 401.46, whereas processing is
       normally with floats would give you 401.46000000000004.
       Use this after adding/subtracting/multiplying numbers."""
    tickDec = Decimal(str(tickSize))
    return float((Decimal(round(num / tickSize, 0)) * tickDec))

def check_sanity():
    portfolio = get_summary()
    for ticker in portfolio['stocks']:
        if short_position_calls_exceeded(portfolio, ticker):
            print("short position call limits exeeeced")
        if long_position_calls_exceeded(portfolio, ticker):
            print("long position call limits exeeeced")
    #position limits are reached
    #if current position get delta maximum position
    order_book = get_orderbook()
    waiting_orders = get_waitinglistorders()
    if portfolio['pnl']<0:
        print("Running in loss , need to take action")
    else:
        print("Running in profit")
#in get ticker prices place the 

def place_orders():
    buy=[]
    sell=[]
    portfolio = get_summary()
    print("in place order ", portfolio)
    for ticker in trader.get_stock_list():
            for i in reversed(range(1, ORDER_PAIR + 1)):
                print("in place orders:", i)
                print(long_position_calls_exceeded(portfolio, ticker))
                if not long_position_calls_exceeded(portfolio, ticker):
                    print("longpositioncalls done")
                    buy.append(set_quantity_price(-i, ticker))
                if not short_position_calls_exceeded(portfolio, ticker):
                    print("shortpositioncalls done")
                    sell.append(set_quantity_price(i, ticker))
    return converge_orders(buy, sell)

def get_price_offset(index, ticker, quantity):
    #read the CSV's  for a single TICKER 
    #calcualte mean of the SPREAD to calculate BUY& SELL
    #Get HIGHEST of BUY Call
    #get LOWEST of SELL price 
    #having SPREAD already, get MIN SPREAD to calculate start position to buy & sell 
    #set in a dictionary and resend back with buy or sell call
    filename = os.path.join(file_name,ticker+".csv")
    data_collected = pd.read_csv(filename)
    data_collected.dropna(inplace=True)
    current_spread = round(data_collected['Spread'].mean(),2)  
    start_position_buy = data_collected['Bid Price'].min()  + current_spread
    start_position_sell = data_collected['Ask Price'].max() - current_spread

    start_position = start_position_buy if index < 0 else start_position_sell
    # First positions (index 1, -1) should start right at start_position, others should branch from there
    index = index + 1 if index < 0 else index - 1
    return toNearest(start_position * (1 + INTERVAL) ** index,quantity )

def set_quantity_price(index, ticker): #prepare order
    quantity = ORDER_START_SIZE + ((abs(index) - 1) * ORDER_STEP_SIZE)
    price = get_price_offset(index, ticker, quantity)
    return {'price': price, 'orderQty': quantity, 'side': "Buy" if index < 0 else "Sell", 'stock':ticker}
   
def converge_orders(buy_order, sell_order):
    existing_orders = get_waitinglistorders()
    to_amend = []
    to_create = []
    to_cancel = []
    buysmatched =0
    sellsmatched =0
    for order in existing_orders.items():
        try:
            if order[1]['type']== "Type.LIMIT_BUY" or order[1]['type']=="Type.MARKET_BUY" : 
                desired_order = buy_order[buysmatched]
                buysmatched  +=1
            elif order[1]['type']== "Type.LIMIT_SELL" or order[1]['type']=="Type.MARKET_SELL" :
                desired_order = sell_order[sellsmatched]
                sellsmatched +=1
            #if found existingorder
            if desired_order['orderQty'] != order[1]['size'] or (
                desired_order['price'] != order[1]['price'] and abs((desired_order['price'] / order[1]['price']) - 1) > RELIST_INTERVAL):
                to_amend.append({'stock': order[0], 'orderID': order[1]['id'], 'orderQty': order['quantity'] + desired_order['orderQty'],
                             'price': desired_order['price'], 'type': order[1]['type']})
        except IndexError:             # Will throw if there isn't a desired order to match. In that case, cancel it.
            to_cancel.append(order)
    while buysmatched < len(buy_order):
        buy_order[buysmatched].update({"type":"buy"})
        to_create.append(buy_order[buysmatched])
        buysmatched += 1
    while sellsmatched < len(sell_order):
        sell_order[sellsmatched].update({"type":"sell"})
        to_create.append(sell_order[sellsmatched])
        sellsmatched += 1 
    if len(to_amend) > 0:
        for order in to_amend:
            if trader.get_order(order['id']).status== 'Status.FILLED':
                continue
            if  order['type'] =='buy': #in ["Type.LIMIT_BUY", "Type.MARKET_BUY"]:
                place_order = shift.Order(shift.Order.Type.LIMIT_BUY, order['stock'], order['orderQty'], order['price'])
            if  order['type'] =='sell': #in ["Type.LIMIT_SELL", "Type.MARKET_SELL"]:
                place_order = shift.Order(shift.Order.Type.LIMIT_SELL, order['stock'], order['orderQty'], order['price'])
            print("Placing order Type.LIMIT_SELL", order['stock'], order['orderQty'], order['price']  )
            trader.submit_order(place_order)
    if len(to_create) > 0:
        for orders in reversed(to_create):
            print(orders)
            if  orders['type'] =='buy': # in ["Type.LIMIT_BUY", "Type.MARKET_BUY"]:
                place_order = shift.Order(shift.Order.Type.LIMIT_BUY, orders['stock'], orders['orderQty'], orders['price'])
            if  orders['type'] =='sell': #in  in ["Type.LIMIT_SELL", "Type.MARKET_SELL"]:
                place_order = shift.Order(shift.Order.Type.LIMIT_SELL, orders['stock'], orders['orderQty'], orders['price'])
            print("Placing order Type.LIMIT_SELL", orders['stock'], orders['orderQty'], orders['price']  )
            trader.submit_order(place_order)

def run_loop():
    while (END_TIME > trader.get_last_trade_time().time()): 
        sleep(LOOP_INTERVAL)
        #check sanity if you are making profits
        #print current status
        #place orders 
        check_sanity()
        place_orders()

if __name__ == "__main__":
    #Connect to the Stock Exchange
    try:
        trader = connect('swift_trade', 'crT4Y3w9')  
        sleep(5) #wait until connection is successful for further executions
        trader.sub_all_order_book()
        
        #if market is open start data collection and trading individual stocks
        if market_is_open(): 
            print("Start Trading!")
            #Starting data collection in respective file
            pf= get_summary()
            print("Before Order execution summary: ", pf)
            #Loop through what you wish to continue doing
            t1 = threading.Thread(target=collect_data)
            t1.start()
            sleep(400)
            t2 = threading.Thread(target=run_loop )
            t2.start()
            t1.join()
            t2.join()
            """
            #Create Multiple Threads for each Stock to check
            sleep(100)
            thread_list = []
            for a_stock in trader.get_stock_list():
                thread = threading.Thread(target=run_loop ))
                thread_list.append(thread)
                thread.start()
            
            for a_thread in thread_list:
                a_thread.join() 
            """

        print("DONE")
        trader.disconnect() 
    except Exception as e:
        print("Uncaught exception- ", e)