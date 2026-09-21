-- Indexes. Run this file second.
-- An index works like the index at the back of a book. The database looks up a value
-- in the index and jumps to the matching rows, without reading the whole table.
-- "if not exists" makes this file safe to run more than once.

-- For queries that filter or sort weekly sales by date.
create index if not exists idx_weekly_store_sales_date on weekly_store_sales(date);
-- For queries about one store, or grouped by store.
create index if not exists idx_weekly_store_sales_store on weekly_store_sales(store);
-- For comparing holiday weeks with normal weeks.
create index if not exists idx_weekly_store_sales_holiday on weekly_store_sales(holiday_flag);
-- For finding receipts by day.
create index if not exists idx_transactions_date on transactions(transaction_date);
-- For grouping receipts by payment method.
create index if not exists idx_transactions_payment on transactions(payment_method);
-- For finding every receipt line of one product.
create index if not exists idx_line_items_product on transaction_line_items(product_id);
