# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# pandas does all the table work in this file.
import pandas as pd


# Old name on the left, new name on the right.
# The CSV uses names like Weekly_Sales. The code and the SQL tables use weekly_sales.
WEEKLY_COLUMN_MAP = {
    # Store number, 1 to 45.
    "Store": "store",
    # The week of the sales. Every date in the file is a Friday.
    "Date": "date",
    # Money that store took in that week.
    "Weekly_Sales": "weekly_sales",
    # 1 if the week has a holiday in it, otherwise 0.
    "Holiday_Flag": "holiday_flag",
    # Temperature for that store and week.
    "Temperature": "temperature",
    # Cost of fuel in the store's region.
    "Fuel_Price": "fuel_price",
    # Consumer Price Index, a measure of how expensive things are.
    "CPI": "cpi",
    # Unemployment rate in percent.
    "Unemployment": "unemployment",
}

# Same renaming idea for the POS file, where one row is one receipt.
POS_COLUMN_MAP = {
    # Receipt number.
    "Invoice ID": "invoice_id",
    # Branch letter: A, B or C.
    "Branch": "branch",
    # City the branch is in.
    "City": "city",
    # "Member" or "Normal".
    "Customer type": "customer_type",
    # Gender of the customer.
    "Gender": "gender",
    # Product category, for example "Health and beauty".
    "Product line": "product_line",
    # Price of one item.
    "Unit price": "unit_price",
    # How many items were bought.
    "Quantity": "quantity",
    # The 5% tax amount. "%" cannot be part of a column name in code, so it becomes "pct".
    "Tax 5%": "tax_5_pct",
    # What the customer paid, tax included.
    "Total": "total",
    # Day of the purchase.
    "Date": "date",
    # Time of the purchase.
    "Time": "time",
    # Cash, Credit card or Ewallet.
    "Payment": "payment",
    # Cost of goods sold: what the items cost the shop.
    "cogs": "cogs",
    # Profit as a percent of the sale.
    "gross margin percentage": "gross_margin_percentage",
    # Profit in money.
    "gross income": "gross_income",
    # Customer rating out of 10.
    "Rating": "rating",
}


# Returns "weekly" or "pos". Used when the app cannot know the file type in advance
# (an uploaded CSV or a database query).
def detect_dataset_type(df: pd.DataFrame) -> str:
    # Lowercase every column name, so "Store" and "store" count as the same.
    lowered = {col.lower() for col in df.columns}
    # Weekly data must have both weekly_sales and store. First test the lowercased names.
    if {"weekly_sales", "store"}.issubset(lowered) or {"weekly_sales", "store"}.issubset(
        # Second test: rename through the weekly map first, then lowercase.
        # .get(col, col) means "use the new name if the map has one, else keep the old name".
        {WEEKLY_COLUMN_MAP.get(col, col).lower() for col in df.columns}
    ):
        # Both columns found.
        return "weekly"
    # Anything else is handled as POS data.
    return "pos"


# Turns a raw weekly table into a clean one. Every weekly chart depends on this.
def normalize_weekly_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Rename the columns. .copy() makes a new table, so the caller's table is not changed.
    normalized = df.rename(columns=WEEKLY_COLUMN_MAP).copy()
    # The eight clean names that must be present.
    required = set(WEEKLY_COLUMN_MAP.values())
    # Names from that set that the table does not have.
    missing = required.difference(normalized.columns)
    # A missing column would break the charts later with a confusing error.
    # Better to stop here and name the missing columns.
    if missing:
        # sorted() puts the names in A to Z order, so the message reads the same every time.
        raise ValueError(f"Missing weekly sales columns: {sorted(missing)}")

    # Text to real dates. The file writes day first: 05-02-2010 is 5 February 2010.
    # Without dayfirst=True pandas would read it as 2 May.
    normalized["date"] = pd.to_datetime(normalized["date"], dayfirst=True)
    # Columns that should hold numbers.
    numeric_cols = ["store", "weekly_sales", "holiday_flag", "temperature", "fuel_price", "cpi", "unemployment"]
    # Go through them one at a time.
    for col in numeric_cols:
        # Text to number. errors="coerce" turns junk like "abc" into an empty value instead of crashing.
        normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
    # A row with no store, no date or no sales cannot be used. Drop those rows.
    normalized = normalized.dropna(subset=["store", "date", "weekly_sales"])
    # Store numbers are whole numbers: 1, not 1.0.
    normalized["store"] = normalized["store"].astype(int)
    # An empty holiday flag is treated as 0 (normal week), then stored as a whole number.
    normalized["holiday_flag"] = normalized["holiday_flag"].fillna(0).astype(int)
    # Oldest week first, and store 1 to 45 inside each week. reset_index renumbers the rows from 0.
    return normalized.sort_values(["date", "store"]).reset_index(drop=True)


# Turns a raw POS table into a clean one.
def normalize_pos_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Rename the columns and work on a copy.
    normalized = df.rename(columns=POS_COLUMN_MAP).copy()
    # Only these six are needed by the POS page. The other columns are optional.
    required = {"invoice_id", "branch", "product_line", "total", "date", "payment"}
    # Required names the table does not have.
    missing = required.difference(normalized.columns)
    # Stop early and say which ones are missing.
    if missing:
        # The error message lists the missing names in A to Z order.
        raise ValueError(f"Missing POS sales columns: {sorted(missing)}")

    # Text to real dates. The POS file writes 2019-01-05, which pandas reads correctly by default.
    normalized["date"] = pd.to_datetime(normalized["date"])
    # Columns that should hold numbers.
    for col in ["unit_price", "quantity", "tax_5_pct", "total", "cogs", "gross_income", "rating"]:
        # Some of these may be absent, so check before converting.
        if col in normalized.columns:
            # Text to number. Junk becomes an empty value.
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
    # Drop rows with no date or no total, put the oldest first, renumber the rows.
    return normalized.dropna(subset=["date", "total"]).sort_values("date").reset_index(drop=True)


# The four numbers for the cards at the top of the dashboard.
# sales_col is "weekly_sales" for weekly data and "total" for POS data.
def sales_kpis(df: pd.DataFrame, sales_col: str) -> dict[str, float]:
    # Count different stores if there is a store column. If not, count different branches.
    # The empty pd.Series is a fallback, so a table with neither column gives 0 instead of an error.
    store_count = df["store"].nunique() if "store" in df.columns else df.get("branch", pd.Series(dtype=str)).nunique()
    # float() turns numpy numbers into normal Python numbers.
    return {
        # All sales added together.
        "total_sales": float(df[sales_col].sum()),
        # Total divided by the number of rows.
        "average_sales": float(df[sales_col].mean()),
        # How many rows there are.
        "row_count": float(len(df)),
        # How many stores or branches there are.
        "store_count": float(store_count),
    }


# One row per month with the sales of all stores added up.
def monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    # A raw table still has the Weekly_Sales column. Clean it first in that case. Otherwise just copy.
    weekly = normalize_weekly_columns(df) if "Weekly_Sales" in df.columns else df.copy()
    # Add a month column. to_period("M") cuts a date down to its month,
    # and to_timestamp() turns that into the first day of the month, e.g. 2010-02-01.
    monthly = weekly.assign(month=weekly["date"].dt.to_period("M").dt.to_timestamp())
    # Add up weekly_sales inside each month. as_index=False keeps month as a normal column.
    return monthly.groupby("month", as_index=False)["weekly_sales"].sum()


# One row per store, best seller first.
def store_performance(df: pd.DataFrame) -> pd.DataFrame:
    # Clean first if the table is still raw.
    weekly = normalize_weekly_columns(df) if "Weekly_Sales" in df.columns else df.copy()
    # The brackets let the chain of steps run over several lines.
    ranking = (
        # Put all rows of the same store together.
        weekly.groupby("store")
        # Work out four numbers per store. Each line reads: new_column=(source column, what to do).
        .agg(
            # Every week of the store added up.
            total_sales=("weekly_sales", "sum"),
            # The store's typical week.
            average_weekly_sales=("weekly_sales", "mean"),
            # How many weeks of data the store has.
            weeks=("weekly_sales", "size"),
            # The flag is 0 or 1, so adding the flags counts the holiday weeks.
            holiday_weeks=("holiday_flag", "sum"),
        )
        # groupby moved store into the row labels. Bring it back as a normal column.
        .reset_index()
        # Highest total at the top.
        .sort_values("total_sales", ascending=False)
    )
    # The rows are sorted now, so numbering them 1, 2, 3 gives the rank.
    ranking["rank"] = range(1, len(ranking) + 1)
    # Pick the column order for display, rank first.
    return ranking[["rank", "store", "total_sales", "average_weekly_sales", "weeks", "holiday_weeks"]]


# How much higher (or lower) holiday weeks are than normal weeks, in percent.
def holiday_uplift(df: pd.DataFrame) -> float:
    # Clean first if the table is still raw.
    weekly = normalize_weekly_columns(df) if "Weekly_Sales" in df.columns else df.copy()
    # Average sales for flag 0 and for flag 1. means.loc[0] is the normal-week average.
    means = weekly.groupby("holiday_flag")["weekly_sales"].mean()
    # No comparison is possible if one group is missing. A zero average would mean dividing by zero.
    if 0 not in means or 1 not in means or means.loc[0] == 0:
        # Report "no difference" in those cases.
        return 0.0
    # (holiday - normal) / normal * 100. With 1,122,888 and 1,041,256 this gives 7.84.
    return float(((means.loc[1] - means.loc[0]) / means.loc[0]) * 100)


# Correlation between sales and each economic column.
# Correlation runs from -1 to 1. Close to 0 means the two numbers barely move together.
def economic_correlations(df: pd.DataFrame) -> pd.DataFrame:
    # Clean first if the table is still raw.
    weekly = normalize_weekly_columns(df) if "Weekly_Sales" in df.columns else df.copy()
    # The four columns to compare with sales.
    signals = ["temperature", "fuel_price", "cpi", "unemployment"]
    # Build a list with one small dictionary per signal.
    rows = [
        # .corr() returns the correlation between two columns.
        {"signal": signal, "correlation_to_sales": weekly[signal].corr(weekly["weekly_sales"])}
        # Repeat that for each of the four names.
        for signal in signals
    ]
    # Make a table from the list.
    return pd.DataFrame(rows).assign(
        # Add the correlation without its sign. -0.106 is a stronger link than 0.009,
        # and sorting on the unsigned value puts it first.
        absolute_correlation=lambda frame: frame["correlation_to_sales"].abs()
    # Largest unsigned value first.
    ).sort_values("absolute_correlation", ascending=False)
