from ibapi.client import *
from ibapi.wrapper import *



# To take the MSFT example, if you request contract details for MSFT without specifying the exchange
# (ie just use symbol=”MSFT” and sectype=”STK”), you get 25 contracts returned. Two of them have exchange=”SMART”,
# so if you want to SMART-route an order you have to supply something additional,
# and primary exchange is one way of doing this: if you like, it’s a hint to IB to tell them
# which SMART routing infrastructure to us: the US one (primary exchange=”NASDAQ”, or the European one
# (primary exchange=”EBS”).
# Primary exchange is primarily relevant when using SMART as exchange in your order placement, market data requests, etc.
# Since SMART can only be used with stocks and options,
# you probably never need to supply primary exchange for other securities.
# And for stocks and options where you are direct routing to a particular exchange,
# primary exchange is probably completely irrelevant.
# (I say ‘probably’ because nothing ever seems to be certain in the realm of contracts!...)

AAPL = Contract()
AAPL.symbol = "AAPL"
AAPL.secType = "STK"
AAPL.exchange = "SMART"
AAPL.currency = "USD"

VOO = Contract()
VOO.symbol = "VOO"
VOO.secType = "STK"
VOO.exchange = "SMART"
VOO.currency = "USD"

QQQ = Contract()
QQQ.symbol = "QQQ"
QQQ.secType = "STK"
QQQ.exchange = "SMART"
QQQ.currency = "USD"

GLD = Contract()
GLD.symbol = "GLD"
GLD.secType = "STK"
GLD.exchange = "SMART"
GLD.currency = "USD"

GLD = Contract()
GLD.symbol = "GLD"
GLD.secType = "STK"
GLD.exchange = "SMART"
GLD.currency = "USD"

BRK = Contract()
BRK.symbol = "BRK B"
BRK.secType = "STK"
BRK.exchange = "SMART"
BRK.currency = "USD"

ELT = Contract()
ELT.symbol = "ELT"
ELT.secType = "STK"
ELT.exchange = "SMART"
ELT.currency = "USD"

BND = Contract()
BND.symbol = "BND"
BND.secType = "STK"
BND.exchange = "SMART"
BND.currency = "USD"

contractList = [
    VOO,
    QQQ,
    BRK,
    GLD
    # AAPL
]
