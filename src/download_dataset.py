# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# Path builds file paths that work on Windows, macOS and Linux.
from pathlib import Path

# pandas is here for the DataFrame type hint below.
import pandas as pd
# load_dataset downloads a dataset from the Hugging Face website. It needs internet.
from datasets import load_dataset


# Where the CSV gets saved. This is the same file the dashboard reads, so running
# this script overwrites the copy that comes with the project.
OUTPUT_PATH = Path("data/raw/walmart_real_sales.csv")


# Downloads the dataset and hands it back as a pandas table.
def dataset_to_frame() -> pd.DataFrame:
    # "Ammok/walmart_sales_prediction" is the dataset's name on Hugging Face.
    ds = load_dataset("Ammok/walmart_sales_prediction")
    # A dataset can come in parts called splits. Take "train" if there is one.
    # If not, take whichever split comes first.
    split_name = "train" if "train" in ds else next(iter(ds.keys()))
    # Convert that split to a DataFrame.
    return ds[split_name].to_pandas()


# Download, then save.
def main() -> None:
    # Make the data/raw folder. parents=True also makes data/ if needed,
    # and exist_ok=True means no error when the folder is already there.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Get the data.
    df = dataset_to_frame()
    # Write it as CSV. index=False leaves out the pandas row numbers.
    df.to_csv(OUTPUT_PATH, index=False)
    # Report how many rows were written and where. ":," adds commas to the number.
    print(f"Wrote {len(df):,} rows to {OUTPUT_PATH}")


# True when started with: python -m src.download_dataset
if __name__ == "__main__":
    # Run the download.
    main()
