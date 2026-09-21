-- Creates every table for MySQL. Run this file first.
-- Running it again deletes the tables and their rows and builds them empty,
-- so rerun it only when you want to load the data from scratch.
-- After a rerun, run 02_indexes.sql and 03_views.sql again too.

-- Drop the old tables. A table that points to another table has to go before it:
-- line items point to transactions, and transactions point to stores and customers.
-- "if exists" means no error on the very first run, when there is nothing to drop yet.
drop table if exists transaction_line_items;
drop table if exists transactions;
drop table if exists customers;
drop table if exists products;
drop table if exists stores;
drop table if exists weekly_store_sales;

-- One row per store or branch.
create table stores (
    store_id int auto_increment primary key, -- auto_increment: MySQL fills in 1, 2, 3 by itself
    store_code varchar(20) not null unique,  -- short code for the store; required, no repeats
    branch_code varchar(10),                 -- branch letter from the POS file, such as A
    city varchar(100),                       -- city name
    created_at timestamp not null default current_timestamp -- time the row was added, filled in by the database
);

-- One row per kind of customer.
create table customers (
    customer_id int auto_increment primary key, -- auto-numbered id
    customer_type varchar(50),                  -- Member or Normal
    gender varchar(30)                          -- gender as written in the POS file
);

-- One row per product line.
create table products (
    product_id int auto_increment primary key, -- auto-numbered id
    product_line varchar(120) not null unique  -- for example Health and beauty; each name stored once
);

-- One row per receipt.
create table transactions (
    transaction_id int auto_increment primary key, -- auto-numbered id
    invoice_id varchar(50) not null unique,        -- receipt number from the POS file; no repeats
    store_id int,                                  -- which store
    customer_id int,                               -- which customer kind
    transaction_date date not null,                -- day of the sale
    transaction_time time,                         -- time of the sale
    payment_method varchar(50),                    -- Cash, Credit card or Ewallet
    total decimal(14, 2) not null,                 -- amount paid; up to 14 digits, 2 of them after the point
    tax decimal(14, 2),                            -- tax part of the total
    cogs decimal(14, 2),                           -- cost of goods sold: what the items cost the shop
    gross_income decimal(14, 2),                   -- profit on the sale
    rating decimal(5, 2),                          -- customer rating out of 10
    foreign key (store_id) references stores(store_id),         -- store_id must exist in the stores table
    foreign key (customer_id) references customers(customer_id) -- customer_id must exist in customers
);

-- One row per product on a receipt.
create table transaction_line_items (
    line_item_id int auto_increment primary key, -- auto-numbered id
    transaction_id int not null,                 -- the receipt this line belongs to
    product_id int not null,                     -- the product that was bought
    unit_price decimal(12, 2) not null,          -- price of one item
    quantity int not null,                       -- how many items
    line_total decimal(14, 2) not null,          -- unit_price times quantity
    foreign key (transaction_id) references transactions(transaction_id), -- the receipt must exist
    foreign key (product_id) references products(product_id)              -- the product must exist
);

-- The Walmart weekly data. One row is one store in one week.
-- This is the table the ETL script fills and the dashboard reads.
create table weekly_store_sales (
    weekly_sale_id int auto_increment primary key, -- auto-numbered id
    store int not null,                            -- store number, 1 to 45
    date date not null,                            -- the Friday of that sales week
    weekly_sales decimal(14, 2) not null,          -- sales for that store and week
    holiday_flag int not null,                     -- 1 for a holiday week, 0 for a normal week
    temperature decimal(8, 2),                     -- temperature for that store and week
    fuel_price decimal(8, 3),                      -- fuel price, 3 decimals like 2.572
    cpi decimal(10, 6),                            -- Consumer Price Index, 6 decimals like 211.096358
    unemployment decimal(8, 3),                    -- unemployment rate in percent
    unique key uq_weekly_store_date (store, date)  -- a store can have one row per week; a second load of the same file is refused
);
