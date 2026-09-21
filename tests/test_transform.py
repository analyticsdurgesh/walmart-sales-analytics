# pandas builds the small tables the tests feed into the functions.
import pandas as pd

# The forecast function under test.
from src.forecasting import forecast_weekly_sales
# The cleaning and summary functions under test.
from src.transform import holiday_uplift, monthly_sales, normalize_weekly_columns, store_performance


# pytest runs every function whose name starts with test_.
# This one guards the date format: 05-02-2010 has to mean 5 February, not 2 May.
def test_normalize_weekly_columns_parses_day_first_dates():
    # One raw row with the same column names and date style as the real CSV.
    raw = pd.DataFrame(
        # Each key is a column name. Each list holds that column's values, one per row.
        {
            # Store number.
            "Store": [1],
            # Day first, then month, then year.
            "Date": ["05-02-2010"],
            # Sales for the week.
            "Weekly_Sales": [100.0],
            # 0 means a normal week.
            "Holiday_Flag": [0],
            # The last four columns only need to exist. This test never reads their values.
            "Temperature": [42.31],
            # Copied from the first row of the real file.
            "Fuel_Price": [2.572],
            # Also from the real file.
            "CPI": [211.096358],
            # Also from the real file.
            "Unemployment": [8.106],
        }
    )

    # Run the cleaning.
    df = normalize_weekly_columns(raw)

    # assert stops the test with an error if the condition is false.
    # Row 0 must have the date 2010-02-05.
    assert df.loc[0, "date"] == pd.Timestamp("2010-02-05")
    # Cleaning must not change the sales number.
    assert df.loc[0, "weekly_sales"] == 100.0


# The store with the most sales must come out on top.
def test_store_performance_ranks_by_total_sales():
    # Three rows: store 1 sells 100. Store 2 sells 150 and 200.
    raw = pd.DataFrame(
        # Column name, then one value per row.
        {
            # Row 1 belongs to store 1, rows 2 and 3 to store 2.
            "Store": [1, 2, 2],
            # 5 Feb, 5 Feb and 12 Feb 2010.
            "Date": ["05-02-2010", "05-02-2010", "12-02-2010"],
            # Store 1 has 100 in total. Store 2 has 150 + 200 = 350.
            "Weekly_Sales": [100.0, 150.0, 200.0],
            # Only the last row is a holiday week.
            "Holiday_Flag": [0, 0, 1],
            # Filler value 1 for the four columns this test does not look at.
            "Temperature": [1, 1, 1],
            # Filler.
            "Fuel_Price": [1, 1, 1],
            # Filler.
            "CPI": [1, 1, 1],
            # Filler.
            "Unemployment": [1, 1, 1],
        }
    )
    # Clean the rows first, as the app does.
    df = normalize_weekly_columns(raw)

    # Build the ranking.
    ranking = store_performance(df)

    # iloc[0] is the first row. It must be store 2.
    assert ranking.iloc[0]["store"] == 2
    # Its total must be 150 + 200 = 350.
    assert ranking.iloc[0]["total_sales"] == 350.0


# Checks the monthly total and the holiday percentage with numbers that are easy to do by hand.
def test_monthly_sales_and_holiday_uplift():
    # Two weeks in February 2010: a normal week with 100 and a holiday week with 150.
    raw = pd.DataFrame(
        # Column name, then one value per row.
        {
            # Both rows are store 1.
            "Store": [1, 1],
            # 5 Feb and 12 Feb 2010, so both fall in the same month.
            "Date": ["05-02-2010", "12-02-2010"],
            # 100 in the normal week, 150 in the holiday week.
            "Weekly_Sales": [100.0, 150.0],
            # First row normal, second row holiday.
            "Holiday_Flag": [0, 1],
            # Filler value 1 for the four columns this test does not look at.
            "Temperature": [1, 1],
            # Filler.
            "Fuel_Price": [1, 1],
            # Filler.
            "CPI": [1, 1],
            # Filler.
            "Unemployment": [1, 1],
        }
    )
    # Clean the rows.
    df = normalize_weekly_columns(raw)

    # Both weeks are in the same month, so there is one row and it must say 100 + 150 = 250.
    assert monthly_sales(df).loc[0, "weekly_sales"] == 250.0
    # (150 - 100) / 100 * 100 = 50 percent.
    assert holiday_uplift(df) == 50.0


# The forecast must add exactly the number of weeks that was asked for.
def test_forecast_appends_requested_periods():
    # Eight Fridays in a row with slowly rising sales.
    raw = pd.DataFrame(
        # Column name, then one value per row.
        {
            # [1] * 8 is a list with eight 1s, so every row is store 1.
            "Store": [1] * 8,
            # Eight weekly dates starting Friday 5 February 2010.
            "Date": pd.date_range("2010-02-05", periods=8, freq="W-FRI"),
            # Sales climb from 100 to 130 with small dips on the way.
            "Weekly_Sales": [100, 110, 105, 115, 120, 118, 125, 130],
            # No holiday weeks.
            "Holiday_Flag": [0] * 8,
            # Filler value 1 for the four columns this test does not look at.
            "Temperature": [1] * 8,
            # Filler.
            "Fuel_Price": [1] * 8,
            # Filler.
            "CPI": [1] * 8,
            # Filler.
            "Unemployment": [1] * 8,
        }
    )
    # Clean the rows.
    df = normalize_weekly_columns(raw)

    # Ask for 4 future weeks.
    forecast = forecast_weekly_sales(df, periods=4)

    # 8 past rows + 4 future rows = 12.
    assert len(forecast) == 12
    # The last 4 rows must each have a forecast number. notna() is True where a value exists.
    assert forecast["forecast_sales"].tail(4).notna().all()
