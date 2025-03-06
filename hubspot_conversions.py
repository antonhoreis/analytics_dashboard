import logging
import time
from api_clients import hubspot_api as hubspot, calendly_api as calendly
import pandas as pd
import datetime
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


def get_deals():
    global deals_df
    logger.info("Retrieving deals from Hubspot")

    start_time = time.time()
    deals = hubspot.search_objects(
        object_type="deal",
        filter_groups=[
            {
                "filters": [
                    {
                        "propertyName": "pipeline",
                        "operator": "EQ",
                        "value": "default",
                    }
                ]
            }
        ],
        properties=[
            "dealname",
            "dealstage",
            "pipeline",
            "contact_email",
            "hs_deal_score",
            "goals",
            "hs_tag_ids",
            "verbal_agreement",
        ],
        # association_types=["contacts"],
    )
    logger.info(
        f"Retrieved {len(deals)} deals from Hubspot in {round(time.time() - start_time, 2)} seconds"
    )
    deals_df = pd.DataFrame(deals)
    deals_df = (
        pd.concat(
            [deals_df, deals_df.properties.apply(pd.Series)],
            axis=1,
        )
        .drop(columns=["properties"])
        .convert_dtypes()
    ).rename(columns={"createdAt": "date"})
    deals_df.date = pd.to_datetime(deals_df.date, format="ISO8601")
    deals_df.updatedAt = pd.to_datetime(deals_df.updatedAt, format="ISO8601")
    deals_df.hs_lastmodifieddate = pd.to_datetime(
        deals_df.hs_lastmodifieddate, format="ISO8601"
    )
    deals_df = deals_df.sort_values(by="date").drop_duplicates(
        subset=["contact_email"], keep="first"
    )
    deals_df.set_index("date", inplace=True)

    return deals_df


def get_first_calls():
    start_time = time.time()
    logger.info("Retrieving first calls from Hubspot")
    calendly_first_calls = hubspot.search_objects(
        object_type="meeting",
        filter_groups=[
            {
                "filters": [
                    {
                        "propertyName": "hs_meeting_title",
                        "operator": "EQ",
                        "value": "Calendly: First call with LALIA",
                    },
                    {
                        "propertyName": "hs_activity_type",
                        "operator": "EQ",
                        "value": "First Call",
                    },
                ],
                "groupType": "OR",
            }
        ],
        properties=[
            "hs_meeting_title",
            "hs_activity_type",
            "hs_meeting_start_time",
            "hs_meeting_outcome",
        ],
        # association_types=["contacts"],
    )
    first_calls_df = pd.DataFrame(calendly_first_calls)
    first_calls_df = pd.concat(
        [first_calls_df, first_calls_df.properties.apply(pd.Series)], axis=1
    )
    first_calls_df = (
        (
            first_calls_df.drop(columns=["properties"])
            .rename(
                columns={
                    "hs_meeting_title": "meeting_title",
                    "hs_activity_type": "activity_type",
                    "createdAt": "date",
                },
            )
            .drop_duplicates(
                subset=["id"],
            )
        )
        .infer_objects()
        .convert_dtypes()
    )
    first_calls_df.date = pd.to_datetime(first_calls_df.date, format="ISO8601")
    first_calls_df.updatedAt = pd.to_datetime(
        first_calls_df.updatedAt, format="ISO8601"
    )
    first_calls_df.hs_lastmodifieddate = pd.to_datetime(
        first_calls_df.hs_lastmodifieddate, format="ISO8601"
    )
    first_calls_df.hs_createdate = pd.to_datetime(
        first_calls_df.hs_createdate, format="ISO8601"
    )
    first_calls_df.hs_meeting_start_time = pd.to_datetime(
        first_calls_df.hs_meeting_start_time
    )
    first_calls_df.set_index("date", inplace=True)
    first_calls_df["conversion"] = "First call"
    logger.info(
        f"Retrieved {len(first_calls_df)} first calls from Hubspot in {round(time.time() - start_time, 2)} seconds"
    )

    return first_calls_df


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


def get_first_call_verbal_agreements():
    if deals_df.empty:
        get_deals()
    verbal_agreement_deals = deals_df[deals_df["hs_tag_ids"].str.contains("33264189")]
    verbal_agreement_deals["conversion"] = "Verbal agreement after first call"

    return verbal_agreement_deals


def get_placement_calls():
    if deals_df.empty:
        get_deals()
    placement_deals = deals_df[deals_df["hs_tag_ids"].str.contains("32600779")]
    placement_deals["conversion"] = "Placement scheduled"

    return placement_deals


def get_hubspot_conversions(fetch_deals=True):
    global calendly_data

    if fetch_deals:
        get_deals()
    first_calls_df = get_first_calls()
    verbal_agreement_deals = get_first_call_verbal_agreements()
    placement_deals = get_placement_calls()

    conversions = pd.concat([first_calls_df, verbal_agreement_deals, placement_deals])

    # Check if we need to update calendly_data for newer conversions
    if not conversions.empty:
        latest_date = conversions.index.max()
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

    # Prepare utm columns for merging
    utm_columns = [
        "utm_campaign",
        "utm_source",
        "utm_medium",
        "utm_content",
        "utm_term",
    ]

    # Reset index of conversions to have date as a column
    conversions_reset = conversions.reset_index()

    # Enrich conversions with UTM data by joining on email
    enriched_conversions = pd.merge(
        conversions_reset,
        calendly_data[utm_columns],
        left_on="contact_email",
        right_index=True,
        how="left",
    )

    # Fill missing UTM values
    for col in utm_columns:
        if col in enriched_conversions.columns:
            enriched_conversions[col] = enriched_conversions[col].fillna("unknown")
        else:
            enriched_conversions[col] = "unknown"

    # Group by date, UTM parameters, and conversion type, then count
    result = (
        enriched_conversions.groupby(["date"] + utm_columns + ["conversion"])
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
                "utm_campaign": "Campaign",
                "utm_source": "Source",
                "utm_medium": "Medium",
                "utm_content": "Content",
                "utm_term": "Term",
            }
        )
        .set_index("date")
    )

    return result
