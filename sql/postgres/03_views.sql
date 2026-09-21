-- Views. Run this file third.
-- A view is a saved query with a name. It holds no data of its own.
-- "select * from vw_monthly_sales" runs the query below each time, so the answer is always current.
-- "create or replace" makes this file safe to run more than once.

-- Sales per month.
create or replace view vw_monthly_sales as
select
    date_trunc('month', date)::date as month, -- cut the date down to the 1st of its month; ::date removes the time part
    sum(weekly_sales) as total_sales,         -- all stores and weeks of that month added up
    avg(weekly_sales) as average_weekly_sales, -- average of one store-week in that month
    count(*) as store_weeks                   -- how many rows went into the month
from weekly_store_sales
group by 1; -- 1 means "the first column in the select list", which is month

-- Stores ranked by total sales.
create or replace view vw_store_rankings as
select
    store,                                                      -- store number
    sum(weekly_sales) as total_sales,                           -- everything the store sold
    avg(weekly_sales) as average_weekly_sales,                  -- its typical week
    rank() over (order by sum(weekly_sales) desc) as sales_rank -- window function: 1 for the biggest total, 2 for the next
from weekly_store_sales
group by store; -- one output row per store

-- Holiday weeks next to normal weeks.
create or replace view vw_holiday_uplift as
select
    holiday_flag,                              -- 0 = normal week, 1 = holiday week
    avg(weekly_sales) as average_weekly_sales, -- the number to compare between the two rows
    sum(weekly_sales) as total_sales,          -- total for that kind of week
    count(*) as week_count                     -- how many store-weeks of that kind
from weekly_store_sales
group by holiday_flag; -- gives two rows
