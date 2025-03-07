import gspread
import pandas as pd
import datetime
import time
from api_clients import calendly_api as calendly
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

deals_df = pd.DataFrame()
calendly_data = (
    pd.read_csv("./data/calendly_first_call_data.csv")
    .set_index("email")
    .sort_values(by="created_at")
)
FIRST_CALL_DATA_UPDATED_AT = datetime.datetime.strptime(
    os.getenv("FIRST_CALL_DATA_UPDATED_AT"), "%Y-%m-%d"
)

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


def get_calendly_data(start_date: datetime.datetime):
    logger.info("Retrieving calendly data")
    start_time = time.time()
    calendly_meetings = calendly.list_events(min_start_time=start_date)
    calendly_meetings_df = pd.DataFrame(calendly_meetings)
    first_calls_df = calendly_meetings_df.loc[
        calendly_meetings_df.name.str.lower() == "first call with lalia"
    ].set_index("created_at")
    first_calls_df.index = pd.to_datetime(first_calls_df.index)
    first_calls_df.sort_index(inplace=True)
    first_calls_df["uuid"] = first_calls_df.uri.str.split("/").str[-1]
    calendly_data = first_calls_df.uuid.apply(calendly.list_event_invitees).apply(
        lambda x: pd.Series(x[0])
    )
    calendly_data = pd.concat(
        [calendly_data, calendly_data.tracking.apply(pd.Series)], axis=1
    ).drop(columns=["tracking"])
    logger.info(
        f"Retrieved {len(calendly_data)} calendly data from Hubspot in {round(time.time() - start_time, 2)} seconds"
    )
    return calendly_data


def get_sales_data(filter=None):
    if filter:
        raise NotImplementedError("Filtering is not implemented yet")

    global calendly_data

    logger.info("Retrieving sales data")
    start_time = time.time()
    df = (
        read_gsheet_to_df(database_spreadsheet_id, sheet_id=zenler_data_sheet_id)
        .rename(columns={"EnrollmentDate": "date"})
        .set_index("date")
    )
    logger.info(f"Retrieved sales data in {round(time.time() - start_time, 2)} seconds")
    df.index = pd.to_datetime(df.index, format="mixed")
    df = (
        df.sort_index()
        .dropna(subset=["TransactionId"])
        .drop_duplicates(subset=["TransactionId"])
        .dropna(how="all", axis=1)
        .assign(conversion="Sale")
    )
    df.PaidAmount = (
        df.PaidAmount.str.replace("€", "")
        .str.replace(",", ".")
        .str.strip()
        .str.replace("", "0")
        .astype(float)
    )
    df = df[df.PaidAmount > 0]

    # Check if we need to update calendly_data for newer sales
    if not df.empty:
        latest_date = df.index.max()
        # Convert both timestamps to naive for comparison
        latest_date_naive = (
            latest_date.tz_localize(None) if latest_date.tzinfo else latest_date
        )
        updated_at_naive = (
            FIRST_CALL_DATA_UPDATED_AT.tz_localize(None)
            if FIRST_CALL_DATA_UPDATED_AT.tzinfo
            else FIRST_CALL_DATA_UPDATED_AT
        )

        if latest_date_naive > updated_at_naive:
            logger.info(
                f"Retrieving new calendly data since {FIRST_CALL_DATA_UPDATED_AT}"
            )
            new_calendly_data = get_calendly_data(FIRST_CALL_DATA_UPDATED_AT)
            # Combine with existing calendly_data, preferring newer data if duplicates
            calendly_data = pd.concat([calendly_data, new_calendly_data])
            calendly_data = calendly_data[~calendly_data.index.duplicated(keep="last")]

    # Reset index to have date as a column
    df_reset = df.reset_index()

    # Prepare utm columns for merging
    utm_columns = [
        "utm_campaign",
        "utm_source",
        "utm_medium",
        "utm_content",
        "utm_term",
    ]

    # Enrich sales data with UTM parameters by joining on email
    # Assuming the email column in df is named "Email"
    enriched_sales = pd.merge(
        df_reset,
        calendly_data[utm_columns],
        left_on="Email",  # Adjust this if the email column has a different name
        right_index=True,
        how="left",
    )

    # Fill missing UTM values
    for col in utm_columns:
        if col in enriched_sales.columns:
            enriched_sales[col] = enriched_sales[col].fillna("unknown")
        else:
            enriched_sales[col] = "unknown"

    # Group by date, UTM parameters, and conversion type, then count
    result = (
        enriched_sales.groupby(["date"] + utm_columns + ["conversion"])
        .size()
        .unstack(fill_value=0)  # Convert conversion types to columns
    )

    # Resample daily to ensure all days are represented
    result = (
        (
            result.groupby(level=utm_columns)
            .apply(lambda x: x.droplevel(utm_columns).resample("D").sum())
            .fillna(0)
        )
        .reset_index()
        .rename(
            columns={
                "utm_campaign": "campaign",
                "utm_source": "source",
                "utm_medium": "medium",
                "utm_content": "content",
                "utm_term": "term",
                "Sale": "sales",
            }
        )
        .set_index("date")
    )

    return result
