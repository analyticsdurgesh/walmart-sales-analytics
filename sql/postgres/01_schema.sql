-- Creates every table for PostgreSQL. Run this file first.
-- Running it again deletes the tables and their rows and builds them empty,
-- so rerun it only when you want to load the data from scratch.
-- After a rerun, run 02_indexes.sql and 03_views.sql again too.

-- The views from 03_views.sql read weekly_store_sales. PostgreSQL will not drop a table
-- while a view still uses it, so the views are dropped first.
-- "if exists" means no error on the very first run, when there is nothing to drop yet.
drop view if exists vw_monthly_sales;
drop view if exists vw_store_rankings;
drop view if exists vw_holiday_uplift;

-- Now the tables. A table that points to another table has to go before it:
-- line items point to transactions, and transactions point to stores and customers.
drop table if exists transaction_line_items;
drop table if exists transactions;
drop table if exists customers;
drop table if exists products;
drop table if exists stores;
drop table if exists weekly_store_sales;

-- One row per store or branch.
create table stores (
    store_id serial primary key,            -- serial: PostgreSQL fills in 1, 2, 3 by itself
    store_code varchar(20) not null unique, -- short code for the store; required, no repeats
    branch_code varchar(10),                -- branch letter from the POS file, such as A
    city varchar(100),                      -- city name
    created_at timestamp not null default current_timestamp -- time the row was added, filled in by the database
);

-- One row per kind of customer.
create table customers (
    customer_id serial primary key, -- auto-numbered id
    customer_type varchar(50),      -- Member or Normal
    gender varchar(30)              -- gender as written in the POS file
);

-- One row per product line.
create table products (
    product_id serial primary key,            -- auto-numbered id
    product_line varchar(120) not null unique -- for example Health and beauty; each name stored once
);

-- One row per receipt.
create table transactions (
    transaction_id serial primary key,                     -- auto-numbered id
    invoice_id varchar(50) not null unique,                -- receipt number from the POS file; no repeats
    store_id integer references stores(store_id),          -- which store; must exist in the stores table
    customer_id integer references customers(customer_id), -- which customer kind; must exist in customers
    transaction_date date not null,                        -- day of the sale
    transaction_time time,                                 -- time of the sale
    payment_method varchar(50),                            -- Cash, Credit card or Ewallet
    total numeric(14, 2) not null,                         -- amount paid; up to 14 digits, 2 of them after the point
    tax numeric(14, 2),                                    -- tax part of the total
    cogs numeric(14, 2),                                   -- cost of goods sold: what the items cost the shop
    gross_income numeric(14, 2),                           -- profit on the sale
    rating numeric(5, 2)                                   -- customer rating out of 10
);

-- One row per product on a receipt.
create table transaction_line_items (
    line_item_id serial primary key,                                        -- auto-numbered id
    transaction_id integer not null references transactions(transaction_id), -- the receipt this line belongs to
    product_id integer not null references products(product_id),             -- the product that was bought
    unit_price numeric(12, 2) not null,                                      -- price of one item
    quantity integer not null,                                               -- how many items
    line_total numeric(14, 2) not null                                       -- unit_price times quantity
);

-- The Walmart weekly data. One row is one store in one week.
-- This is the table the ETL script fills and the dashboard reads.
create table weekly_store_sales (
    weekly_sale_id serial primary key,   -- auto-numbered id
    store integer not null,              -- store number, 1 to 45
    date date not null,                  -- the Friday of that sales week
    weekly_sales numeric(14, 2) not null, -- sales for that store and week
    holiday_flag integer not null,       -- 1 for a holiday week, 0 for a normal week
    temperature numeric(8, 2),           -- temperature for that store and week
    fuel_price numeric(8, 3),            -- fuel price, 3 decimals like 2.572
    cpi numeric(10, 6),                  -- Consumer Price Index, 6 decimals like 211.096358
    unemployment numeric(8, 3),          -- unemployment rate in percent
    unique (store, date)                 -- a store can have one row per week; a second load of the same file is refused
);
