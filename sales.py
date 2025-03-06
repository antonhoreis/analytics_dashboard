import gspread
import pandas as pd

gc = gspread.service_account(filename="./credentials/invoice-generator_gsa.json")

database_spreadsheet_id = "1oe-HGOAJsnhlYMOBtMToBJM5v5xYS6krTNhN0TqlEww"
zenler_data_sheet_id = "1545453263"


def read_gsheet_to_df(
    spreadsheet_id: str, sheet_name: str = None, sheet_id: str = None
) -> pd.DataFrame:
    """Read a Google Sheet into a pandas DataFrame
    # drop '' columns since they are not allowed in mongodb
            spreadsheet_id (str): The ID of the Google Sheet (from the URL)
            sheet_name (str): The name of the sheet to read
            sheet_id (str): The ID of the sheet to read (param gid)
        Returns:
            pd.DataFrame: DataFrame containing the sheet data
    """
    # Get the worksheet
    if sheet_id:
        sheet = gc.open_by_key(spreadsheet_id).get_worksheet_by_id(sheet_id)
    else:
        if not sheet_name:
            raise ValueError("sheet_name or sheet_id must be provided")
        sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    # Get all values including headers
    data = sheet.get_all_values()

    # Convert to DataFrame using first row as headers
    df = pd.DataFrame(data[1:], columns=data[0])
    if "" in df.columns:
        df.drop(columns=[""], inplace=True)

    return df


def get_sales_data():
    df = (
        read_gsheet_to_df(database_spreadsheet_id, sheet_id=zenler_data_sheet_id)
        .rename(columns={"EnrollmentDate": "date"})
        .set_index("date")
    )
    df.index = pd.to_datetime(df.index, format="mixed")
    df = (
        df.sort_index()
        .dropna(subset=["TransactionId"])
        .drop_duplicates(subset=["TransactionId"])
        .dropna(how="all", axis=1)
    )
    df.PaidAmount = (
        df.PaidAmount.str.replace("€", "")
        .str.replace(",", ".")
        .str.strip()
        .str.replace("", "0")
        .astype(float)
    )
    df = df[df.PaidAmount > 0]
    df["conversion"] = "Sale"
    return df
