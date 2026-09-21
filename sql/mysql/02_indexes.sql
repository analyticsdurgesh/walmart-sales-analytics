-- Indexes. Run this file second, once, right after 01_schema.sql.
-- An index works like the index at the back of a book. The database looks up a value
-- in the index and jumps to the matching rows, without reading the whole table.
-- MySQL has no "create index if not exists". Running this file twice in a row stops with
-- "Duplicate key name". Rerun 01_schema.sql first: dropping a table removes its indexes too.

-- For queries that filter or sort weekly sales by date.
create index idx_weekly_store_sales_date on weekly_store_sales(date);
-- For queries about one store, or grouped by store.
create index idx_weekly_store_sales_store on weekly_store_sales(store);
-- For comparing holiday weeks with normal weeks.
create index idx_weekly_store_sales_holiday on weekly_store_sales(holiday_flag);
-- For finding receipts by day.
create index idx_transactions_date on transactions(transaction_date);
-- For grouping receipts by payment method.
create index idx_transactions_payment on transactions(payment_method);
-- For finding every receipt line of one product.
create index idx_line_items_product on transaction_line_items(product_id);
