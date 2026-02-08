import cassandra.cqlengine.models
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.cqlengine.columns import Text, UUID, Integer, UserDefinedType, Float
from cassandra.cqlengine.usertype import UserType
from cassandra.policies import WhiteListRoundRobinPolicy, DowngradingConsistencyRetryPolicy, \
    ConstantSpeculativeExecutionPolicy
from cassandra.query import named_tuple_factory

import uuid
from cassandra.cqlengine import columns, ValidationError
from cassandra.cqlengine import connection
from cassandra.cqlengine.query import BatchQuery
from datetime import datetime
from cassandra.cqlengine.management import sync_table, drop_table
from cassandra.cqlengine.models import Model

from data.model.daily_price import DailyPrice, Currency, Portfolio, Fund, Dividend, Stock
import concurrent.futures
import pandas as pd
from ibapi.contract import Contract

class Store:
    def __init__(self, hosts, keyspace):
        connection.setup(hosts=hosts, default_keyspace=keyspace, protocol_version=3)
        sync_table(DailyPrice)
        sync_table(Portfolio)
        sync_table(Stock)
        sync_table(Fund)
        sync_table(Dividend)

    def drop_daily_price_table(self):
        drop_table(DailyPrice)

    def insert_daily_price(self, ticker, date, name, ccy, country, close, high, low, created_at=None, batch=None):
        if created_at is None:
            created_at = datetime.now()

        DailyPrice.batch(batch).create(ticker=ticker,
                                       year=date.year,
                                       date=date,
                                       name=name,
                                       currency=Currency(code=ccy, country=country),
                                       close=float(close),
                                       high=float(high),
                                       low=float(low),
                                       created_at=created_at,
                                       updated_at=created_at)

    def batch_insert_daily_price(self, dailyprices, execute_on_exception=False):
        with BatchQuery(execute_on_exception=execute_on_exception, timeout=None) as b:
            now = datetime.now()
            for dailyprice in dailyprices:
                self.insert_daily_price(ticker=dailyprice.ticker,
                                        date=dailyprice.date,
                                        name=dailyprice.name,
                                        ccy=dailyprice.ccy,
                                        country=dailyprice.country,
                                        close=dailyprice.close,
                                        high=dailyprice.high,
                                        low=dailyprice.low,
                                        created_at=now,
                                        batch=b
                                        )

    def batch_delete_daily_price(self, dailyprice_ranges, execute_on_exception=False):
        with BatchQuery(execute_on_exception=execute_on_exception, timeout=None) as b:
            for dailyprice_range in dailyprice_ranges:
                exclude = False
                if hasattr(dailyprice_range, 'exclude'):
                    exclude = dailyprice_range.exclude

                self.delete_daily_price(ticker=dailyprice_range.ticker,
                                        fromDate=dailyprice_range.fromDate,
                                        toDate=dailyprice_range.toDate,
                                        exclude=exclude,
                                        batch=b
                                        )

    def batch_update_daily_price(self, dailyprice_updates, execute_on_exception=False):
        with BatchQuery(execute_on_exception=execute_on_exception, timeout=None) as b:
            now = datetime.now()
            for dailyprice_update in dailyprice_updates:
                dailyprice_update.kwargs['updated_at'] = now
                exclude = False
                if hasattr(dailyprice_update, 'exclude'):
                    exclude = dailyprice_update.exclude
                self.update_daily_price(ticker=dailyprice_update.ticker,
                                        fromDate=dailyprice_update.fromDate,
                                        toDate=dailyprice_update.toDate,
                                        exclude=exclude,
                                        batch=b,
                                        **dailyprice_update.kwargs)

    def update_daily_price(self, ticker, fromDate, toDate, exclude=False, batch=None, **kwargs):
        rows = self.select_daily_price_by_range(ticker, fromDate, toDate, exclude)
        for row in rows:
            row.batch(batch).update(**kwargs)

    def save(self, model):
        if model is not None and isinstance(model, cassandra.cqlengine.models.Model):
            raise ValueError('class should be inherited from cassandra.cqlengine.models.Model')

        model.save()

    def delete_daily_price(self, ticker, fromDate, toDate, exclude=False, batch=None):
        return self.select_daily_price_by_range(ticker, fromDate, toDate, exclude).batch(batch).delete()

    def select_daily_price_by_range(self, ticker, fromDate, toDate, exclude=False):
        q = DailyPrice.objects.filter(ticker=ticker) \
            .filter(DailyPrice.date >= fromDate)
        if exclude:
            return q.filter(DailyPrice.date < toDate).order_by('date')
        else:
            return q.filter(DailyPrice.date <= toDate).order_by('date')


    #https://docs.datastax.com/en/developer/python-driver/3.24/index.html
    def select_daily_price_in_pd_by_range(self, ticker, fromDate, toDate, exclude=False):
        rows = self.select_daily_price_by_range(ticker,fromDate,toDate,exclude)
        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        tmp.set_index('date', inplace=True, drop=True)
        return tmp
    
    def insert_portfolio(self, ticker, account_id, position_type, qty, price, market_value,
                     avg_cost, currency, updated_at=None, batch=None):
        if updated_at is None:
            updated_at = datetime.now()

        Portfolio.batch(batch).create(
            ticker=ticker,
            account_id=account_id,
            position_type=position_type,
            qty=qty,
            price=price,
            market_value=market_value,
            avg_cost=avg_cost,
            currency=Currency(code=currency['code'], country=currency['country']),
            updated_at=updated_at
        )

    def batch_insert_portfolio(self, portfolios, execute_on_exception=False):
        with BatchQuery(execute_on_exception=execute_on_exception, timeout=None) as b:
            now = datetime.now()
            for p in portfolios:
                self.insert_portfolio(
                    ticker=p['ticker'],
                    account_id=p['account_id'],
                    position_type=p['position_type'],
                    qty=p['qty'],
                    price=p.get('price'),
                    market_value=p['market_value'],
                    avg_cost=p['avg_cost'],
                    currency=p['currency'],
                    updated_at=now,
                    batch=b
                )

    
    def select_portfolio(self):
        return Portfolio.objects()

    def select_portfolio_in_pd(self):
        rows = self.select_portfolio()
        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        tmp.set_index('ticker', inplace=True, drop=True)
        return tmp

    # --- CRUD Operations for Fund ---
    def insert_fund(self, ticker, expense_ratio, created_at=None, updated_at=None):
        if created_at is None:
            created_at = datetime.now()
        if updated_at is None:
            updated_at = datetime.now()

        Fund.create(
            ticker=ticker,
            expense_ratio=expense_ratio,
            created_at=created_at,
            updated_at=updated_at
        )

    def select_fund(self, ticker):
        return Fund.objects(ticker=ticker).first()

    def update_fund(self, ticker, **kwargs):
        fund = self.select_fund(ticker)
        if fund:
            for key, value in kwargs.items():
                setattr(fund, key, value)
            fund.updated_at = datetime.now()
            fund.save()

    def delete_fund(self, ticker):
        fund = self.select_fund(ticker)
        if fund:
            fund.delete()

    def select_all_funds(self):
        return Fund.objects()

    def select_all_funds_in_pd(self):
        rows = self.select_all_funds()
        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        tmp.set_index('ticker', inplace=True, drop=True)
        return tmp

    # --- CRUD Operations for Stock ---
    def insert_stock(self, bucket, ticker, secType, exchange, currency, created_at=None, updated_at=None, batch=None):
        if created_at is None:
            created_at = datetime.now()
        if updated_at is None:
            updated_at = datetime.now()

        Stock.batch(batch).create(
            bucket=bucket,
            ticker=ticker,
            secType=secType,
            exchange=exchange,
            currency=Currency(code=currency['code'], country=currency['country']),
            created_at=created_at,
            updated_at=updated_at
        )

    def batch_insert_stock(self, stocks:list[Stock], execute_on_exception=False):
        with BatchQuery(execute_on_exception=execute_on_exception, timeout=None) as b:
            now = datetime.now()
            for stock in stocks:
                # Skip if ticker already exists in any bucket
                existing = Stock.objects.filter(ticker=stock['ticker']).first()
                if existing is not None:
                    continue
                self.insert_stock(
                    bucket=stock['bucket'],
                    ticker=stock['ticker'],
                    secType=stock['secType'],
                    exchange=stock['exchange'],
                    currency=stock['currency'],
                    created_at=now,
                    updated_at=now,
                    batch=b
                )

    # --- CRUD Operations for Stock ---
    def select_stock(self, bucket, ticker):
        return Stock.objects(bucket=bucket, ticker=ticker).first()

    def update_stock(self, bucket, ticker, **kwargs):
        stock = self.select_stock(bucket, ticker)
        if stock:
            for key, value in kwargs.items():
                setattr(stock, key, value)
            stock.updated_at = datetime.now()
            stock.save()
        
    def save_contract_list(self, contracts:list[Contract], bucket='S&P'):
        l = []
        for contract in contracts:
            # Determine country by ticker suffix
            country = "US"
            if contract.currency == "JPY":
                country = "JP"
            elif contract.currency == "HKD":
                country = "HK"
            elif contract.currency == "CNY":
                country = "CN"
            
            stock = Stock(
                bucket=bucket,
                ticker=contract.symbol,
                secType=contract.secType,
                exchange=contract.exchange,
                currency=Currency(code=contract.currency, country=country)
            )
            l.append(stock)
        self.batch_insert_stock(l)
        

    def delete_stock(self, bucket, ticker):
        stock = self.select_stock(bucket, ticker)
        if stock:
            stock.delete()

    def select_stocks_by_bucket(self, bucket):
        return Stock.objects.filter(bucket=bucket).all()

    def select_all_stocks(self):
        rows = Stock.objects.all()
        for r in rows:
            yield r

    def select_all_stocks_in_pd(self):
        rows = list(self.select_all_stocks())
        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        if not tmp.empty:
            tmp.set_index('ticker', inplace=True, drop=True)
        return tmp
    
    def select_all_stocks_in_contract(self):
        rows = list(self.select_all_stocks())
        contracts = []
        for r in rows:
            contract = Contract()
            contract.symbol = r.ticker
            contract.secType = r.secType
            contract.exchange = r.exchange
            contract.currency = r.currency.code
            contracts.append(contract)
        return contracts
    

    # --- CRUD Operations for Dividend ---
    def insert_dividend(self, ticker, date, amount, created_at=None, updated_at=None):
        if created_at is None:
            created_at = datetime.now()
        if updated_at is None:
            updated_at = datetime.now()

        Dividend.create(
            ticker=ticker,
            date=date,
            amount=amount,
            created_at=created_at,
            updated_at=updated_at
        )

    def select_dividend(self, ticker, date):
        return Dividend.objects(ticker=ticker, date=date).first()

    def update_dividend(self, ticker, date, **kwargs):
        dividend = self.select_dividend(ticker, date)
        if dividend:
            for key, value in kwargs.items():
                setattr(dividend, key, value)
            dividend.updated_at = datetime.now()
            dividend.save()

    def delete_dividend(self, ticker, date):
        dividend = self.select_dividend(ticker, date)
        if dividend:
            dividend.delete()

    def select_dividends_by_ticker(self, ticker):
        return Dividend.objects(ticker=ticker).all()

    def select_dividends_by_ticker_in_pd(self, ticker):
        rows = self.select_dividends_by_ticker(ticker)
        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        tmp.set_index('date', inplace=True, drop=True)
        return tmp

    def select_dividends_in_pd_by_range(self, ticker, fromDate, toDate):
        rows = Dividend.objects.filter(ticker=ticker) \
            .filter(Dividend.date >= fromDate) \
            .filter(Dividend.date <= toDate) \
            .order_by('date') \
            .all()

        if not rows:
            # Return an empty DataFrame with the expected columns if no data is found
            return pd.DataFrame(columns=['ticker', 'date', 'amount', 'created_at', 'updated_at'])

        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        tmp.set_index('date', inplace=True, drop=True)
        return tmp








