import sys
import shift

print("lising Shitf details:", dir(shift))

tickers =['AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIA', 'DIS', 'GS', 'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'SPY', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM']


def main(argv):
    # create trader object
    trader = shift.Trader("swift_trade")
    # connect and subscribe to all available order books
    try:
        trader.connect("initiator.cfg", "crT4Y3w9")
        
        trader.sub_all_order_book()
        print("Last trader time: ", trader.get_last_trade_time())
        trader.get_subscribed_order_book_list()
        print("tick, trader.get_last_size(tick), trader.get_last_price(tick), trader.get_close_price(tick), trader.get_close_price(tick)")
        for tick in tickers:
            print("%s :%s , %s, %s, %s "%(tick, trader.get_last_size(tick), trader.get_last_price(tick), trader.get_close_price(tick), trader.get_close_price(tick))) 
        print(trader.get_last_price('AAPL'))
        print(trader.get_close_price())
        print(trader.get_best_price())
        print(trader.get)
        print(trader.get_portfolio_summary())
    except Exception as e:
        print("Excption occured!: ", e)
    except shift.IncorrectPasswordError as e:
        print(e)
    except shift.ConnectionTimeoutError as e:
        print(e)

    # demo_01(trader)
    # demo_02(trader)
    # demo_03(trader)
    # demo_04(trader)
    # demo_05(trader)
    # demo_06(trader)
    # demo_07(trader)
    # demo_08(trader)
    # demo_09(trader)
    # demo_10(trader)

    # disconnect
    trader.disconnect()

    return


if __name__ == "__main__":
    main(sys.argv)

