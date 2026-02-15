import pandas as pd
from sqlalchemy import create_engine

EXCEL_PATH = "data/lab_data.xlsx"
DB_PATH = "drugage.db"
TABLE_NAME = "tox_data"

def clean_columns(cols):
    # makes column names SQL friendly
    return (
        cols.str.strip()
            .str.lower()
            .str.replace(r"[^a-z0-9]+", "_", regex=True)
            .str.strip("_")
    )

def main():
    # read excel
    df = pd.read_excel(EXCEL_PATH)

    # clean headers
    df.columns = clean_columns(df.columns)

    # remove completely empty rows
    df = df.dropna(how="all")

    # optional: convert lc50 to a real number if it exists
    if "lc50_mm" in df.columns:
        df["lc50_mm"] = pd.to_numeric(df["lc50_mm"], errors="coerce")

    # create sqlite db and write table
    engine = create_engine(f"sqlite:///{DB_PATH}")
    df.to_sql(TABLE_NAME, engine, if_exists="replace", index=False)

    print("Import complete")
    print("Rows:", len(df))
    print("Columns:", list(df.columns))
    print(f"Database file created: {DB_PATH}")
    print(f"Table name: {TABLE_NAME}")

if __name__ == "__main__":
    main()
