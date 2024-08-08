from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import time

#https://ibkrcampus.com/tag/python-api/
#https://ibkrcampus.com/ibkr-quant-news/interactive-brokers-python-api-native-a-step-by-step-guide/
#https://algotrading101.com/learn/interactive-brokers-python-api-native-guide/
#api DOC: https://ibkrcampus.com/ibkr-api-page/twsapi-doc/#hist-md

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

app = IBapi()
app.connect('127.0.0.1', 4001, 123)
app.run()

#Uncomment this section if unable to connect
#and to prevent errors on a reconnect

time.sleep(2)
app.disconnect()