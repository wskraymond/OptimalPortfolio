-- Create a keyspace
CREATE KEYSPACE IF NOT EXISTS store WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : '1' };

-- Drop a keyspace
DROP KEYSPACE store;

-- DailyPrice
select * from store.DailyPrice where ticker = 'AAPL' order by date;

-- removes the entire matching row
DELETE  FROM store.DailyPrice WHERE ticker = 'AAPL';

-- removes all record in a table
truncate store.DailyPrice

#Sample Test
-- Create a table
CREATE TABLE IF NOT EXISTS store.shopping_cart (
userid text PRIMARY KEY,
item_count int,
last_update_timestamp timestamp
);

-- Insert some data
INSERT INTO store.shopping_cart
(userid, item_count, last_update_timestamp)
VALUES ('9876', 2, toTimeStamp(now()));
INSERT INTO store.shopping_cart
(userid, item_count, last_update_timestamp)
VALUES ('1234', 5, toTimeStamp(now()));

--Delete the data in specific columns
DELETE last_update_timestamp FROM store.shopping_cart
WHERE userid = '9876';