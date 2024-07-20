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
from datetime import datetime
from cassandra.cqlengine.management import sync_table
from cassandra.cqlengine.models import Model


class Currency(UserType):
    code = columns.Text()
    country = columns.Text()

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
