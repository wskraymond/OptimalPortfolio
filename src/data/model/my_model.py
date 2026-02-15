from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
# from cassandra.cqlengine.columns import Text, UUID, Integer, UserDefinedType, Float
from cassandra.cqlengine.usertype import UserType
from cassandra.policies import WhiteListRoundRobinPolicy, DowngradingConsistencyRetryPolicy, \
    ConstantSpeculativeExecutionPolicy
from cassandra.query import named_tuple_factory

import uuid
from cassandra.cqlengine import columns, ValidationError
from cassandra.cqlengine import connection
from datetime import datetime, timezone
from cassandra.cqlengine.management import sync_table
from cassandra.cqlengine.models import Model



class Currency(UserType):
    code = columns.Text()
    country = columns.Text()


class Stock(Model):
    __table_name__ = 'Stock'
    
    bucket = columns.Text(partition_key=True)
    ticker = columns.Text(primary_key=True, index=True) #here only mark indexing, you're required to create index: CREATE INDEX ON Stock (ticker)
    secType = columns.Text()  # Security type (STK, OPT, etc.)
    exchange = columns.Text()  # Exchange (SMART, NASDAQ, etc.)
    currency = columns.UserDefinedType(Currency)
    lastTradeDateOrContractMonth = columns.Text()  # Optional: for options and futures # lastTradeDateOrContractMonth = '20441115'
    created_at = columns.DateTime(default=lambda: datetime.now(timezone.utc))
    updated_at = columns.DateTime(default=lambda: datetime.now(timezone.utc))
    
    def toMap(self):
        return {
            'bucket': self.bucket,
            'ticker': self.ticker,
            'secType': self.secType,
            'exchange': self.exchange,
            'currency': {
                'code': self.currency.code,
                'country': self.currency.country
            },
            'lastTradeDateOrContractMonth': self.lastTradeDateOrContractMonth,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class DailyPrice(Model):
    __table_name__ = 'DailyPrice'
    # __options__ = {'compaction': {'class': 'SizeTieredCompactionStrategy',
    #                               'bucket_low': .3,
    #                               'bucket_high': 2,
    #                               'min_threshold': 2,
    #                               'max_threshold': 64,
    #                               'tombstone_compaction_interval': 86400},
    #                'gc_grace_seconds': 0}
    ticker = columns.Text(primary_key=True, partition_key=True)
    date = columns.Date(primary_key=True, clustering_order="DESC")
    year = columns.Integer()
    name = columns.Text()
    currency = columns.UserDefinedType(Currency)
    close = columns.Float()
    high = columns.Float()
    low = columns.Float()
    created_at = columns.DateTime()
    updated_at = columns.DateTime()

    # Defining a function
    def toMap(self):
        return {
            'ticker': self.ticker,
            'date': self.date.date(),  # convert from cassandra date to datetime.date
            'close': self.close,
            'high': self.high,
            'low': self.low
        }
    


class Portfolio(Model):
    __table_name__ = 'Portfolio'

    ticker = columns.Text(primary_key=True, partition_key=True)
    account_id = columns.Text(primary_key=True)  # Optional: if multiple accounts are tracked
    position_type = columns.Text()  # e.g., 'Long' or 'Short'
    qty = columns.Integer()
    price = columns.Float()
    market_value = columns.Float()
    avg_cost = columns.Float()
    currency = columns.UserDefinedType(Currency)
    updated_at = columns.DateTime(default=datetime.utcnow)

    def toMap(self):
        return {
            'ticker': self.ticker,
            'account_id': self.account_id,
            'position_type': self.position_type,
            'qty': self.qty,
            'price': self.price,
            'market_value': self.market_value,
            'avg_cost': self.avg_cost,
            'currency': {
                'code': self.currency.code,
                'country': self.currency.country
            },
            'updated_at': self.updated_at
        }

class Dividend(Model):
    __table_name__ = 'Dividend'

    ticker = columns.Text(primary_key=True, partition_key=True)
    date = columns.Date(primary_key=True, clustering_order="DESC")
    amount = columns.Float()  # Dividend amount
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime(default=datetime.utcnow)

    def toMap(self):
        return {
            'ticker': self.ticker,
            'date': self.date,
            'amount': self.amount,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
class Fund(Model):
    __table_name__ = 'Fund'

    ticker = columns.Text(primary_key=True, partition_key=True)
    expense_ratio = columns.Float()  # Annual expense ratio as a percentage
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime(default=datetime.utcnow)

    def toMap(self):
        return {
            'ticker': self.ticker,
            'expense_ratio': self.expense_ratio,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

