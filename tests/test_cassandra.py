import unittest

import collections
import pytest
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
from datetime import datetime
from cassandra.cqlengine.management import sync_table
from cassandra.cqlengine.models import Model
import sys, inspect

from src.data.model.my_model import Currency
from src.data.store import Store


class TestCassandra(unittest.TestCase):
    # @pytest.mark.skip(reason="Integration test only")
    def test_insert(self):
        store = Store(hosts=['127.0.0.1'], keyspace='store')
        store.insert_daily_price(ticker='test',
                                 date=datetime.strptime('01/01/2015', '%d/%m/%Y').date(),
                                 name='test',
                                 ccy='USD',
                                 country='USA',
                                 close=100,
                                 high=110,
                                 low=98
                                 )
        store.insert_daily_price(ticker='test',
                                 date=datetime.strptime('01/08/2015', '%d/%m/%Y').date(),
                                 name='test',
                                 ccy='USD',
                                 country='USA',
                                 close=105,
                                 high=115,
                                 low=98
                                 )

        store.insert_daily_price(ticker='test',
                                 date=datetime.strptime('01/01/2016', '%d/%m/%Y').date(),
                                 name='test',
                                 ccy='USD',
                                 country='USA',
                                 close=110,
                                 high=110,
                                 low=98
                                 )

        rows = store.select_daily_price_by_range(ticker='test',
                                                 fromDate=datetime.strptime('01/05/2015', '%d/%m/%Y').date(),
                                                 toDate=datetime.strptime('01/01/2016', '%d/%m/%Y').date())

        self.assertEqual(rows.count(), 2)

        print()
        for row in rows:
            print(row.ticker, row.date, row.close)

        store.delete_daily_price(ticker='test',
                                 fromDate=datetime.strptime('01/05/2015', '%d/%m/%Y').date(),
                                 toDate=datetime.strptime('01/01/2016', '%d/%m/%Y').date())

        rows = store.select_daily_price_by_range(ticker='test',
                                                 fromDate=datetime.strptime('01/01/2015', '%d/%m/%Y').date(),
                                                 toDate=datetime.strptime('01/01/2017', '%d/%m/%Y').date(),
                                                 exclude=True)
        self.assertEqual(rows.count(), 1)

        #store.drop_daily_price_table()

    #@pytest.mark.skip(reason="Integration test only")
    def test_batch_insert(self):
        store = Store(hosts=['127.0.0.1'], keyspace='store')
        DailyPriceData = collections.namedtuple('DailyPriceData', ['ticker',
                                                                   'date',
                                                                   'name',
                                                                   'ccy',
                                                                   'country',
                                                                   'close',
                                                                   'high',
                                                                   'low'])
        data = [DailyPriceData(ticker='test',
                               date=datetime.strptime('01/01/2015', '%d/%m/%Y').date(),
                               name='test',
                               ccy='USD',
                               country='USA',
                               close=100,
                               high=110,
                               low=98
                               ),
                DailyPriceData(ticker='test',
                               date=datetime.strptime('01/08/2015', '%d/%m/%Y').date(),
                               name='test',
                               ccy='USD',
                               country='USA',
                               close=105,
                               high=115,
                               low=98
                               ),
                DailyPriceData(ticker='test',
                               date=datetime.strptime('01/01/2016', '%d/%m/%Y').date(),
                               name='test',
                               ccy='USD',
                               country='USA',
                               close=110,
                               high=110,
                               low=98
                               )]

        store.batch_insert_daily_price(data)

        rows = store.select_daily_price_by_range(ticker='test',
                                                 fromDate=datetime.strptime('01/05/2015', '%d/%m/%Y').date(),
                                                 toDate=datetime.strptime('01/01/2016', '%d/%m/%Y').date())

        self.assertEqual(rows.count(), 2)
        print()
        for row in rows:
            print(row.ticker, row.date, row.close)

        DeleteCriterion = collections.namedtuple('DeleteCriterion', ['ticker',
                                                                     'fromDate',
                                                                     'toDate'])
        criterion = [DeleteCriterion(ticker='test',
                                     fromDate=datetime.strptime('01/05/2015', '%d/%m/%Y').date(),
                                     toDate=datetime.strptime('01/01/2016', '%d/%m/%Y').date())]
        store.batch_delete_daily_price(criterion)

        rows = store.select_daily_price_by_range(ticker='test',
                                                 fromDate=datetime.strptime('01/01/2015', '%d/%m/%Y').date(),
                                                 toDate=datetime.strptime('01/01/2017', '%d/%m/%Y').date(),
                                                 exclude=True)
        self.assertEqual(rows.count(), 1)

        UpdateCriterion = collections.namedtuple('UpdateCriterion', ['ticker',
                                                                     'fromDate',
                                                                     'toDate',
                                                                     'kwargs'])
        criterion = [UpdateCriterion(ticker='test',
                                     fromDate=datetime.strptime('01/01/2015', '%d/%m/%Y').date(),
                                     toDate=datetime.strptime('01/01/2017', '%d/%m/%Y').date(),
                                     kwargs={'close': 66, 'low':66})]
        store.batch_update_daily_price(criterion)

        rows = store.select_daily_price_by_range(ticker='test',
                                     fromDate=datetime.strptime('01/01/2015', '%d/%m/%Y').date(),
                                     toDate=datetime.strptime('01/01/2017', '%d/%m/%Y').date())
        for row in rows:
            print(row.ticker, row.date, row.close, row.low, row.updated_at, row.created_at)

        #store.drop_daily_price_table()


if __name__ == '__main__':
    unittest.main()
