-- Three analysis queries to run by hand after the data is loaded.
-- Nothing in the app depends on this file. It changes no data.
-- Window functions such as lag() and rank() need MySQL 8.0 or newer.

-- Query 1: sales per month, and how each month compares with the month before.
-- "with monthly as (...)" is a CTE: a named result that the query below it can read like a table.
with monthly as (
    select
        date_format(date, '%Y-%m-01') as month, -- the 1st of the month, as text like 2010-02-01
        sum(weekly_sales) as total_sales        -- all sales in that month
    from weekly_store_sales
    group by date_format(date, '%Y-%m-01')
)
select
    month,
    total_sales,
    -- lag() reads the value from the previous row. Ordered by month, that is last month's total.
    total_sales - lag(total_sales) over (order by month) as mom_change,
    -- The same change as a percent of last month.
    -- nullif(x, 0) turns 0 into NULL, so a zero month cannot cause a divide-by-zero error.
    100.0 * (total_sales - lag(total_sales) over (order by month))
        / nullif(lag(total_sales) over (order by month), 0) as mom_growth_pct
from monthly
order by month; -- oldest month first; its change columns are empty because nothing comes before it

-- Query 2: a 4-week moving average for every store. It smooths out single odd weeks.
select
    store,
    date,
    weekly_sales,
    avg(weekly_sales) over (
        partition by store -- keep each store's weeks separate
        order by date      -- walk through them oldest to newest
        rows between 3 preceding and current row -- average this week with the 3 weeks before it
    ) as rolling_4_week_avg
from weekly_store_sales
order by store, date;

-- Query 3: holiday weeks next to normal weeks.
select
    holiday_flag,                              -- 0 = normal week, 1 = holiday week
    avg(weekly_sales) as average_weekly_sales, -- the number to compare between the two rows
    count(*) as week_count                     -- how many store-weeks of that kind
from weekly_store_sales
group by holiday_flag;
