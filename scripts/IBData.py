from ibapi.client import *
from ibapi.wrapper import *
import datetime
import time
import threading
port = 4001

#https://ibkrcampus.com/trading-lessons/python-receiving-market-data/
class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
    def nextValidId(self, orderId: OrderId):
        self.orderId = orderId

    def nextId(self):
        self.orderId += 1
        return self.orderId

    def error(self, reqId, errorCode, errorString, advancedOrderReject):
        print(f"reqId: {reqId}, errorCode: {errorCode}, errorString: {errorString}, orderReject: {advancedOrderReject}")

    def historicalData(self, reqId, bar):
        print(reqId, bar)

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical Data Ended for {reqId}. Started at {start}, ending at {end}")
        self.cancelHistoricalData(reqId)
app = TestApp()
app.connect("127.0.0.1", port, 0)
threading.Thread(target=app.run).start()
time.sleep(1)
mycontract = Contract()
mycontract.symbol = "AAPL"
mycontract.secType = "STK"
mycontract.exchange = "SMART"
mycontract.currency = "USD"
app.reqHistoricalData(app.nextId(), mycontract, "", "1 Y", "1 day", "TRADES", 1, 1, False, [])