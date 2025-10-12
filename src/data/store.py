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

from src.data.model.daily_price import DailyPrice, Currency, Portfolio
import pandas as pd

class Store:
    def __init__(self, hosts, keyspace):
        connection.setup(hosts=hosts, default_keyspace=keyspace, protocol_version=3)
        sync_table(DailyPrice)
        sync_table(Portfolio)

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

    
    def select_portfolio_by_account(self, account_id):
        return Portfolio.objects.filter(account_id=account_id)

    def select_portfolio_in_pd_by_account(self, account_id):
        rows = self.select_portfolio_by_account(account_id)
        tmp = pd.DataFrame.from_records([x.toMap() for x in rows])
        tmp.set_index('ticker', inplace=True, drop=True)
        return tmp
    

    def select_first_portfolio(self):
        row = Portfolio.objects().first()
        if row:
            return row.toMap()
        return None

    def select_first_portfolio_in_pd(self):
        row = Portfolio.objects().first()
        if row:
            df = pd.DataFrame([row.toMap()])
            df.set_index('ticker', inplace=True, drop=True)
            return df
        return pd.DataFrame()  # Return empty DataFrame if no data found




    


    


