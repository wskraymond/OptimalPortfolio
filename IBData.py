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

port = 4001

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
        self.orderId = 0

    def nextValidId(self, orderId: OrderId):
        self.orderId = orderId

    def nextId(self):
        self.orderId += 1
        return self.orderId

    def error(self, reqId, errorCode, errorString, advancedOrderReject):
        print(f"reqId: {reqId}, errorCode: {errorCode}, errorString: {errorString}, orderReject: {advancedOrderReject}")

    def historicalData(self, reqId: int, bar: BarData):
        print(reqId, bar)
        mycontract = reqId_contract_map[reqId]
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
        print(f"Historical Data Ended for {reqId}. Started at {start}, ending at {end}")
        # print(self.data)

        store = Store(hosts=['127.0.0.1'], keyspace='store')
        store.batch_insert_daily_price(self.data[reqId])
        latch.count_down()
        return super().historicalDataEnd(reqId, start, end)

    def clear(self):
        self.data.clear()


latch = CountDownLatch(len(contractList))
app = TestApp()
app.connect("127.0.0.1", port, 0)
threading.Thread(target=app.run).start()
time.sleep(3)

for contract in contractList:
    reqId_contract_map[app.nextId()] = contract

print(reqId_contract_map)
for id, contract in reqId_contract_map.items():
    print(id, " ", contract)
    #https://interactivebrokers.github.io/tws-api/historical_bars.html
    #https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
    # TRADES data is adjusted for splits, but not dividends.
    # ADJUSTED_LAST data is adjusted for splits and dividends. Requires TWS 967+.
    app.reqHistoricalData(
            reqId=id,
            contract=contract,
            endDateTime="",
            durationStr="30 Y",
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
