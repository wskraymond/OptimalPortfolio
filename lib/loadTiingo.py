import requests

apiToken = 'b6aa06a239545aa707fc32cf7ffa17f3d828380f'
url = 'https://api.tiingo.com/tiingo/daily/'


def getInfoFromTickers(tickers):
    return loadData(tickers)


def getLatestPriceFromTickers(tickers, startDate=None, endDate=None):
    options = {
        'getLatestPrice': True
    }
    if startDate is not None:
        options['startDate'] = startDate
    if endDate is not None:
        options['endDate'] = endDate
    return loadData(tickers, options)


def loadData(tickers, options=None):
    options = options if options else {}
    tickerInfo = []
    if type(tickers) is list:
        for ticker in tickers:
            tickerInfo.append(getData(ticker, options))
    else:
        tickerInfo.append(getData(tickers, options))
    return tickerInfo


def getData(ticker, options=None):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token ' + apiToken
    }
    options = options if options else {}
    httpReq = url + ticker
    if options != {}:
        if 'getLatestPrice' in options:
            httpReq += '/prices'
            if 'startDate' in options:
                httpReq += '?' if '?' not in httpReq else '&'
                httpReq += 'startDate' + options['startDate']
            if 'endDate' in options:
                httpReq += '?' if '?' not in httpReq else '&'
                httpReq += 'endDate=' + options['endDate']

    requestResponse = requests.get(httpReq, headers=headers)
    return requestResponse.json()