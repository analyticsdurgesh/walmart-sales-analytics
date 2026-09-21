# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# numpy does the matrix maths for the regression.
import numpy as np
# pandas groups the sales and builds the tables.
import pandas as pd


# Predicts total sales for the next few weeks.
# The model is a straight-line trend plus a fixed bump for each calendar month.
# It is called a baseline because it is the simplest forecast a better model should beat.
def forecast_weekly_sales(df: pd.DataFrame, periods: int = 12) -> pd.DataFrame:
    # Step 1: go from 6,435 store rows to one row per week.
    weekly = (
        # Put rows with the same date together and look at their sales.
        df.groupby("date", as_index=False)["weekly_sales"]
        # Add the 45 stores together, giving one total per week.
        .sum()
        # Oldest week first.
        .sort_values("date")
        # Number the rows 0, 1, 2 and so on.
        .reset_index(drop=True)
    )
    # Week counter: 0 for the first week, 142 for the last. It lets the model learn a trend over time.
    weekly["week_index"] = np.arange(len(weekly))
    # Month number 1 to 12. It lets the model learn that December is high and January is low.
    weekly["month"] = weekly["date"].dt.month

    # Step 2: build the input table for the model.
    # get_dummies turns month into 12 yes/no columns, month_1 to month_12. A row in March has
    # month_3 = 1 and the other eleven = 0. Without this the model would treat month 12 as
    # "twelve times month 1". week_index is left as it is.
    features = pd.get_dummies(weekly[["week_index", "month"]].astype({"month": "category"}), drop_first=False)
    # Put a column of ones in front. The number the model learns for it is the base level of sales.
    x = np.column_stack([np.ones(len(features)), features.to_numpy(dtype=float)])
    # The answers to learn from: real total sales for each week.
    y = weekly["weekly_sales"].to_numpy(dtype=float)
    # Least squares. It finds one number per column so that x times those numbers lands
    # as close to y as it can. lstsq returns several things and [0] is the list of numbers.
    # The ones column overlaps with the 12 month columns (they also add up to 1 on every row).
    # lstsq copes with that overlap, and the predictions are not affected by it.
    coefficients = np.linalg.lstsq(x, y, rcond=None)[0]

    # Step 3: make the future weeks.
    future_dates = pd.date_range(
        # Start 7 days after the last real week.
        weekly["date"].max() + pd.Timedelta(days=7),
        # As many weeks as the caller asked for.
        periods=periods,
        # One date per week, always a Friday, the same as the real data.
        freq="W-FRI",
    )
    # A table for the future weeks with the same inputs the model was trained on.
    future = pd.DataFrame(
        # Three columns: date, week_index and month.
        {
            # The future Fridays.
            "date": future_dates,
            # Keep counting from where the past stopped: 143, 144 and so on.
            "week_index": np.arange(len(weekly), len(weekly) + periods),
            # Month number of each future Friday.
            "month": future_dates.month,
        }
    )
    # Turn month into yes/no columns again.
    future_features = pd.get_dummies(future[["week_index", "month"]].astype({"month": "category"}), drop_first=False)
    # Twelve future weeks only touch about three months, so only those month columns exist here.
    # reindex adds the missing month columns filled with 0 and puts all columns in the training order.
    future_features = future_features.reindex(columns=features.columns, fill_value=0)
    # The ones column again, same as in training.
    future_x = np.column_stack([np.ones(len(future_features)), future_features.to_numpy(dtype=float)])
    # "@" is matrix multiplication: each future row times the learned numbers gives one prediction.
    # np.clip lifts any negative result to 0, because sales cannot go below zero.
    future["forecast_sales"] = np.clip(future_x @ coefficients, a_min=0, a_max=None)

    # Step 4: join past and future into one table for the chart.
    # Past weeks: keep date and sales, and call the sales column actual_sales.
    historical = weekly[["date", "weekly_sales"]].rename(columns={"weekly_sales": "actual_sales"})
    # Past weeks have no forecast. NaN means "empty", so the forecast line is not drawn there.
    historical["forecast_sales"] = np.nan
    # Future weeks have no real sales yet.
    future["actual_sales"] = np.nan
    # Stack the past rows on top of the future rows. ignore_index renumbers the rows from 0.
    return pd.concat([historical, future[["date", "actual_sales", "forecast_sales"]]], ignore_index=True)
