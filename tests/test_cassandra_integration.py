import unittest

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

class TestCassandraIntegration(unittest.TestCase):
    # @pytest.mark.skip(reason="Integration test only")
    def test_connection(self):
        hosts = ['127.0.0.1']
        cluster = Cluster(hosts)
        session = cluster.connect('store')

    #@pytest.mark.skip(reason="Integration test only")
    def test_named_tuple_factory(self):
        hosts = ['127.0.0.1']
        profile = ExecutionProfile(
            load_balancing_policy=WhiteListRoundRobinPolicy(hosts),
            # Configure the speculative execution policy
            # Execute. A new query will be sent to the server every 0.5 second
            # until we receive a response, for a max number attempts of 10.
            speculative_execution_policy=ConstantSpeculativeExecutionPolicy(delay=.5, max_attempts=10),
            retry_policy=DowngradingConsistencyRetryPolicy(),
            consistency_level=ConsistencyLevel.LOCAL_QUORUM,
            serial_consistency_level=ConsistencyLevel.LOCAL_SERIAL,
            request_timeout=15,
            row_factory=named_tuple_factory #default named_tuple_factory or dict_factory
        )
        '''
        #Users are free to setup additional profiles to be used by name:
        profile_long = ExecutionProfile(request_timeout=30)
        cluster = Cluster(execution_profiles={'long': profile_long})
        session = cluster.connect()
        session.execute(statement, execution_profile='long')
        '''

        '''
        The set of IP addresses we pass to the Cluster is simply an initial set of contact points. After the driver connects to one of these nodes it will automatically discover the rest of the nodes in the cluster and connect to them, so you don’t need to list every node in your cluster.
        '''
        cluster = Cluster(hosts, execution_profiles={EXEC_PROFILE_DEFAULT: profile})

        # To establish connections and begin executing queries
        session = cluster.connect()

        # You can always change a Session’s keyspace using set_keyspace() or by executing a USE query:
        session.set_keyspace('store')
        # session.execute('USE users')

        '''
        1. This will transparently pick a Cassandra node to execute the query against and handle any retries that are necessary if the operation fails.
        2. By default, each row in the result set will be a namedtuple. Each row will have a matching attribute for each column defined in the schema, such as name, age, and so on. You can also treat them as normal tuples by unpacking them or accessing fields by position. 
        '''
        rows = session.execute('select id, device_name, ip_address, location from devices')
        print()
        for row in rows:
            print(row.id, row.device_name, row.ip_address, row.location)

    #@pytest.mark.skip(reason="Integration test only")
    def test_orm(self):
        hosts = ['127.0.0.1']
        connection.setup(hosts=hosts, default_keyspace="store", protocol_version=3)

        class MyAddress(UserType):
            street = Text()
            zipcode = Integer()

        class Users(Model):
            __table_name__ = 'Users'
            name = Text(primary_key=True)
            addr = UserDefinedType(MyAddress)
            usr_type = Text(discriminator_column=True)

        class SuperUsers(Users):
            __discriminator_value__ = 'super'
            group = Text()

            def validate(self):
                super(SuperUsers, self).validate()
                if self.group == 'root':
                    raise ValidationError('root is not allowed as a group')

        sync_table(SuperUsers)

        SuperUsers.create(name="Joe", addr=MyAddress(street="Easy St.", zipcode=99999), group="hadoop")
        users = Users.objects(name="Joe")
        print()
        for user in users:
            print(user.name, user.addr)


if __name__ == '__main__':
    unittest.main()
