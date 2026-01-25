from ibapi.client import *
from ibapi.wrapper import *
import pandas as pd

from src.data.common.CountDownLatch import CountDownLatch
from src.data.contract.MyContract import contractList
from src.data.store import Store
from datetime import datetime
import time
import threading
import collections

#import logging
#logging.basicConfig(level=logging.DEBUG)


print("IB Data starts")
port = 4001
ib_host = 'host.docker.internal'
store_host = 'host.docker.internal'

DailyPriceData = collections.namedtuple('DailyPriceData', ['ticker',
                                                           'date',
                                                           'name',
                                                           'ccy',
                                                           'country',
                                                           'close',
                                                           'high',
                                                           'low'])
reqId_contract_map = {}


# https://ibkrcampus.com/trading-lessons/python-receiving-market-data/
class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = {}
        self.portfolio_data = []
        self.orderId = 0
        self.store = Store(hosts=[store_host], keyspace='store')

    def nextValidId(self, orderId: OrderId):
        self.orderId = orderId

    def nextId(self):
        self.orderId += 1
        return self.orderId

    def error(self, reqId, errorCode, errorString,
              advancedOrderReject=None, errorTime=None):
        print(f"reqId: {reqId}, errorCode: {errorCode}, "
              f"errorString: {errorString}, "
              f"orderReject: {advancedOrderReject}, "
              f"errorTime: {errorTime}")
        

    from ibapi.contract import Contract
    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        print("UpdatePortfolio.",
              "Symbol:", contract.symbol,
              "SecType:", contract.secType,
              "Exchange:", contract.exchange,
              "Position:", position,
              "MarketPrice:", marketPrice,
              "MarketValue:", marketValue,
              "AverageCost:", averageCost,
              "UnrealizedPNL:", unrealizedPNL,
              "RealizedPNL:", realizedPNL,
              "AccountName:", accountName)

        self.portfolio_data.append({
            'ticker': contract.symbol,
            'account_id': accountName,
            'position_type': 'Long' if position >= 0 else 'Short',
            'qty': int(position),
            'price': marketPrice,
            'market_value': marketValue,
            'avg_cost': averageCost,
            'currency': {
                'code': contract.currency,
                'country': contract.exchange
            }
        })

        global contractList
        if contract.secType in ["STK", "ETF"]:
            contract.exchange = "SMART"
            contractList.append(contract)

    def accountDownloadEnd(self, account: str):
        print(f"Account download complete for {account}")
        self.store.batch_insert_portfolio(self.portfolio_data)


    def historicalData(self, reqId: int, bar: BarData):
        mycontract = reqId_contract_map[reqId]
        # print(mycontract.symbol, bar)
        if reqId not in self.data:
            self.data[reqId] = []
        self.data[reqId].append(DailyPriceData(ticker=mycontract.symbol,
                                               date=datetime.strptime(bar.date, '%Y%m%d').date(),
                                               name=mycontract.symbol,
                                               ccy=mycontract.currency,
                                               country=mycontract.exchange,
                                               close=bar.close,
                                               high=bar.high,
                                               low=bar.low
                                               ))

    def historicalDataEnd(self, reqId, start, end):
        mycontract = reqId_contract_map[reqId]
        print(f"Historical Data Ended for {mycontract.symbol}. Started at {start}, ending at {end}")
        # print(self.data)
        self.store.batch_insert_daily_price(self.data[reqId])
        global latch
        latch.count_down()
        return super().historicalDataEnd(reqId, start, end)

    def clear(self):
        self.data.clear()

app = TestApp()
app.connect(ib_host, port, clientId=1)
threading.Thread(target=app.run, daemon=True).start()

time.sleep(3)
app.reqAccountUpdates(True, "") # Request portfolio data
time.sleep(10) # Wait to receive portfolio data


print("start requesting historical data")
global latch
latch = CountDownLatch(len(contractList))
for contract in contractList:
    reqId_contract_map[app.nextId()] = contract

print(reqId_contract_map)
for id, contract in reqId_contract_map.items():
    # print(id, " ", contract)
    #https://interactivebrokers.github.io/tws-api/historical_bars.html
    #https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
    # TRADES data is adjusted for splits, but not dividends.
    # ADJUSTED_LAST data is adjusted for splits and dividends. Requires TWS 967+.
    app.reqHistoricalData(
            reqId=id,
            contract=contract,
            endDateTime="",
            durationStr="10 Y",
            barSizeSetting="1 day",
            whatToShow="ADJUSTED_LAST",
            useRTH=0,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )

latch.wait()
print("count down complete")
time.sleep(10)
app.disconnect()
print("IB Data disconnects")
