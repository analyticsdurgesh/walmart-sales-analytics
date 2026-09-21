# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# pandas holds the data as tables (DataFrames).
import pandas as pd
# plotly.express draws the charts. You can hover over them and zoom in.
import plotly.express as px
# streamlit turns this script into a web page.
import streamlit as st

# The three loaders: two read CSV files, one runs a SQL query.
from src.data_loader import load_from_database, load_pos_csv, load_weekly_csv
# Builds the sales forecast shown in the Forecast tab.
from src.forecasting import forecast_weekly_sales
# Cleaning and summary helpers. All of them live in src/transform.py.
from src.transform import (
    # Tells weekly data apart from POS data by looking at column names.
    detect_dataset_type,
    # How strongly each economic column moves together with sales.
    economic_correlations,
    # Percent gap between holiday weeks and normal weeks.
    holiday_uplift,
    # Sales added up per month.
    monthly_sales,
    # Cleans a raw POS table.
    normalize_pos_columns,
    # Cleans a raw weekly table.
    normalize_weekly_columns,
    # The four numbers for the cards at the top of the page.
    sales_kpis,
    # Stores ranked from highest to lowest total sales.
    store_performance,
)


# Page setup: browser tab title, tab icon (the letter W), and a full-width layout.
# It sits at the top so it runs before anything is drawn.
st.set_page_config(page_title="Walmart Sales Analytics", page_icon="W", layout="wide")


# Streamlit reruns this whole file on every click. st.cache_data remembers the result,
# so the 6,435-row CSV is read from disk once and reused after that.
# show_spinner=False hides the "Running..." message.
@st.cache_data(show_spinner=False)
# Takes a file path, gives back the cleaned weekly table.
def cached_weekly(path: str) -> pd.DataFrame:
    # Read the weekly CSV and clean it.
    return load_weekly_csv(path)


# Same caching idea for the small POS sample file.
@st.cache_data(show_spinner=False)
# Takes a file path, gives back the cleaned POS table.
def cached_pos(path: str) -> pd.DataFrame:
    # Read the POS CSV and clean it.
    return load_pos_csv(path)


# Draws the four number cards at the top of the page.
# kpis is the dictionary that sales_kpis() returns.
def metric_row(kpis: dict[str, float]) -> None:
    # Split the page into 4 equal columns, one per card.
    cols = st.columns(4)
    # Card 1: total sales. The ",.0f" format adds commas and drops decimals, like $6,737,218,987.
    cols[0].metric("Total sales", f"${kpis['total_sales']:,.0f}")
    # Card 2: average sales per row. For weekly data one row is one store in one week.
    cols[1].metric("Average sale", f"${kpis['average_sales']:,.0f}")
    # Card 3: number of rows in the data.
    cols[2].metric("Rows", f"{kpis['row_count']:,.0f}")
    # Card 4: number of stores, or branches when the data is POS.
    cols[3].metric("Stores", f"{kpis['store_count']:,.0f}")


# Builds the sidebar and loads the data the user picked.
# Returns the cleaned table plus a label, "weekly" or "pos", so main() knows which page to draw.
def load_dashboard_data() -> tuple[pd.DataFrame, str]:
    # Heading at the top of the sidebar.
    st.sidebar.title("Data Source")
    # Four radio buttons. mode ends up holding the text of the chosen one.
    mode = st.sidebar.radio(
        # Label shown above the buttons.
        "Mode",
        # The choices. The first one is selected when the app opens.
        ["Real weekly CSV", "Sample POS CSV", "Upload CSV", "Database"],
    )

    # Choice 1: the bundled Walmart file with 45 stores and 143 weeks.
    if mode == "Real weekly CSV":
        # Hand back the cleaned table and the label "weekly".
        return cached_weekly("data/raw/walmart_real_sales.csv"), "weekly"
    # Choice 2: the 10-row POS sample.
    if mode == "Sample POS CSV":
        # Hand back the cleaned table and the label "pos".
        return cached_pos("data/sample/walmart_sales_sample.csv"), "pos"
    # Choice 3: a CSV from the user's own computer.
    if mode == "Upload CSV":
        # File picker in the sidebar. It only accepts .csv files.
        uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
        # No file picked yet.
        if uploaded is None:
            # Show a blue hint box in the main area.
            st.info("Upload a Walmart-style CSV to begin.")
            # End this run here. Streamlit runs the script again once a file arrives.
            st.stop()
        # Read the uploaded file into a table.
        raw = pd.read_csv(uploaded)
        # Decide from the column names: weekly or POS.
        dataset_type = detect_dataset_type(raw)
        # Check which kind it is.
        if dataset_type == "weekly":
            # Weekly file: use the weekly cleaning rules.
            return normalize_weekly_columns(raw), "weekly"
        # Everything else is cleaned as POS data.
        return normalize_pos_columns(raw), "pos"

    # Only "Database" is left at this point, so it needs no if.
    # Text box for the connection URL. type="password" shows dots, because the URL has the password in it.
    db_url = st.sidebar.text_input("SQLAlchemy database URL", type="password")
    # Text box for the SQL to run.
    query = st.sidebar.text_area(
        # Label above the box.
        "Query",
        # Starting text. This query fetches the whole weekly table.
        "select * from weekly_store_sales",
        # Height of the box in pixels.
        height=90,
    )
    # An empty URL means there is nothing to connect to yet.
    if not db_url:
        # Tell the user what to type.
        st.info("Enter a PostgreSQL or MySQL SQLAlchemy URL.")
        # End this run until they type something.
        st.stop()
    # Run the query and get the rows back as a table.
    raw = load_from_database(db_url, query)
    # Same weekly-or-POS check as for uploads.
    dataset_type = detect_dataset_type(raw)
    # Check which kind it is.
    if dataset_type == "weekly":
        # Weekly rows: use the weekly cleaning rules.
        return normalize_weekly_columns(raw), "weekly"
    # Other rows are cleaned as POS data.
    return normalize_pos_columns(raw), "pos"


# The page for weekly store data. df is already cleaned.
def weekly_dashboard(df: pd.DataFrame) -> None:
    # Big heading.
    st.title("Walmart Sales Analytics")
    # Small grey line under the heading.
    st.caption("Weekly store sales, seasonality, economic signals, and baseline forecasts.")
    # The four number cards. Sales are in the weekly_sales column.
    metric_row(sales_kpis(df, sales_col="weekly_sales"))

    # Six tabs. Each variable on the left is one tab that can be filled with content.
    overview, stores, signals, forecast, insights, data = st.tabs(
        # The tab labels, left to right.
        ["Overview", "Stores", "Economic Signals", "Forecast", "Insights", "Data"]
    )

    # Everything inside this "with" block shows up in the Overview tab.
    with overview:
        # One row per month with that month's sales.
        monthly = monthly_sales(df)
        # Two columns. [2, 1] makes the left one twice as wide as the right one.
        left, right = st.columns([2, 1])
        # Left: line chart of sales by month.
        left.plotly_chart(
            # Months go left to right, sales go bottom to top.
            px.line(monthly, x="month", y="weekly_sales", title="Monthly sales trend"),
            # Let the chart fill the width of its column.
            width="stretch",
        )
        # Right: box plot. Box 0 is normal weeks, box 1 is holiday weeks.
        right.plotly_chart(
            # x picks the group (0 or 1) and y is the sales value.
            px.box(df, x="holiday_flag", y="weekly_sales", title="Holiday vs regular weeks"),
            # Fill the column width.
            width="stretch",
        )

    # Stores tab.
    with stores:
        # One row per store, best seller first.
        ranking = store_performance(df)
        # Show all 45 stores as a table. hide_index drops the row-number column.
        st.dataframe(ranking, width="stretch", hide_index=True)
        # Bar chart of the top stores.
        st.plotly_chart(
            # Build the bars.
            px.bar(
                # head(15) keeps the first 15 rows, which are the 15 best stores.
                ranking.head(15),
                # Store number along the bottom.
                x="store",
                # Bar height is total sales.
                y="total_sales",
                # Bar colour follows the average weekly sales.
                color="average_weekly_sales",
                # Text above the chart.
                title="Top stores by total sales",
            ),
            # Fill the page width.
            width="stretch",
        )

    # Economic Signals tab.
    with signals:
        # One row per signal with its correlation to sales.
        corr = economic_correlations(df)
        # Show that small table.
        st.dataframe(corr, width="stretch", hide_index=True)
        # melt reshapes the table from wide to long. The four signal columns become
        # two columns: "signal" holds the name and "value" holds the number.
        # Plotly needs this shape to draw one small chart per signal.
        melted = df.melt(
            # Columns that stay as they are on every row.
            id_vars=["date", "weekly_sales"],
            # Columns that get stacked on top of each other.
            value_vars=["temperature", "fuel_price", "cpi", "unemployment"],
            # Name of the new column holding the old column names.
            var_name="signal",
            # Name of the new column holding the numbers.
            value_name="value",
        )
        # Four scatter plots, one per signal.
        st.plotly_chart(
            # Build the dots.
            px.scatter(
                # Use the long table made above.
                melted,
                # The signal's value goes left to right.
                x="value",
                # Sales go bottom to top.
                y="weekly_sales",
                # Make a separate small chart for each signal.
                facet_col="signal",
                # Two small charts per row, which gives a 2x2 grid.
                facet_col_wrap=2,
                # Text above the chart.
                title="Sales relationship with economic indicators",
            ),
            # Fill the page width.
            width="stretch",
        )

    # Forecast tab.
    with forecast:
        # Slider from 4 to 26 weeks. It starts at 12.
        periods = st.slider("Forecast weeks", 4, 26, 12)
        # Past weeks plus the forecast weeks in one table.
        forecast_df = forecast_weekly_sales(df, periods=periods)
        # tail(periods) keeps the last rows, which are the forecast weeks.
        st.dataframe(forecast_df.tail(periods), width="stretch", hide_index=True)
        # One chart with two lines: real sales, then the forecast after them.
        st.plotly_chart(
            # Build the lines.
            px.line(
                # The table with past and future weeks.
                forecast_df,
                # Dates go left to right.
                x="date",
                # Giving two column names draws two lines.
                y=["actual_sales", "forecast_sales"],
                # Text above the chart.
                title="Baseline aggregate weekly forecast",
            ),
            # Fill the page width.
            width="stretch",
        )

    # Insights tab. Three sentences built from the numbers.
    with insights:
        # Holiday gap in percent. It is 7.84 for the bundled file.
        uplift = holiday_uplift(df)
        # iloc[0] is the first row of the ranking, which is the best store.
        best = store_performance(df).iloc[0]
        # First row here is the signal with the strongest correlation.
        strongest = economic_correlations(df).iloc[0]
        # Sentence 1. ",.2f" keeps two decimals.
        st.write(f"Holiday weeks show a {uplift:,.2f}% sales difference versus regular weeks.")
        # Sentence 2. int() turns 20.0 into 20 so the store number reads well.
        st.write(f"Store {int(best['store'])} leads the sample with ${best['total_sales']:,.0f} in total sales.")
        # Sentence 3, split over two lines of code. Python joins neighbouring strings into one.
        st.write(
            # First half: the signal name. The backticks make Streamlit show it in code style.
            f"The strongest simple economic relationship is `{strongest['signal']}` "
            # Second half: the correlation with three decimals.
            f"with correlation {strongest['correlation_to_sales']:.3f}."
        )

    # Data tab.
    with data:
        # The full cleaned table, so anyone can check the rows behind the charts.
        st.dataframe(df, width="stretch", hide_index=True)


# The page for POS data, where one row is one receipt.
def pos_dashboard(df: pd.DataFrame) -> None:
    # Big heading.
    st.title("Walmart POS Sales Analytics")
    # Small grey line under the heading.
    st.caption("Transaction-level branch, product, customer, and payment analysis.")
    # The four number cards. In POS data the sales column is called total.
    metric_row(sales_kpis(df, sales_col="total"))

    # Four tabs this time.
    overview, products, customers, data = st.tabs(["Overview", "Products", "Customers", "Data"])

    # Overview tab.
    with overview:
        # Add up the totals for each date. as_index=False keeps date as a normal column.
        by_date = df.groupby("date", as_index=False)["total"].sum()
        # Line chart of sales per day.
        st.plotly_chart(px.line(by_date, x="date", y="total", title="Daily sales"), width="stretch")
        # Bar chart of sales per branch (A, B, C).
        st.plotly_chart(px.bar(df.groupby("branch", as_index=False)["total"].sum(), x="branch", y="total"), width="stretch")

    # Products tab.
    with products:
        # Sales per product line, biggest first.
        product_sales = df.groupby("product_line", as_index=False)["total"].sum().sort_values("total", ascending=False)
        # Show it as a table.
        st.dataframe(product_sales, width="stretch", hide_index=True)
        # And as a bar chart.
        st.plotly_chart(px.bar(product_sales, x="product_line", y="total", title="Sales by product line"), width="stretch")

    # Customers tab.
    with customers:
        # Two columns, one pie chart in each.
        cols = st.columns(2)
        # Left pie: share of sales from Member and Normal customers.
        cols[0].plotly_chart(px.pie(df, names="customer_type", values="total", title="Customer type mix"), width="stretch")
        # Right pie: share of sales by payment method.
        cols[1].plotly_chart(px.pie(df, names="payment", values="total", title="Payment mix"), width="stretch")

    # Data tab.
    with data:
        # The cleaned POS rows.
        st.dataframe(df, width="stretch", hide_index=True)


# Entry point. Streamlit runs this on every page load and every click.
def main() -> None:
    # Get the table and its label from the sidebar logic.
    df, dataset_type = load_dashboard_data()
    # Look at the label.
    if dataset_type == "weekly":
        # Weekly data gets the weekly page.
        weekly_dashboard(df)
    # Any other label means POS data.
    else:
        # POS data gets the POS page.
        pos_dashboard(df)


# True when the file is run as a script, which is how "streamlit run app.py" runs it.
if __name__ == "__main__":
    # Build the page.
    main()
