"""
Fetches advertising campaign data from Google Ads and Facebook Ads.

This script utilizes the respective API clients to retrieve campaign performance
metrics (like spend, impressions, clicks, reach) from both platforms.
It then parses and formats the data into pandas DataFrames for analysis.
"""

import pandas as pd
import logging
from api_clients.google_ads_api import GoogleAdsAPIWrapper
from api_clients.facebook_api import get_campaign_insights, get_campaigns
import time

google_ads_client = GoogleAdsAPIWrapper()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_google_ads_campaigns_to_dataframe(campaigns):
    """
    Parse Google Ads campaign data into a pandas DataFrame.

    Args:
        campaigns (list): List of dictionaries containing campaign data

    Returns:
        pandas.DataFrame: DataFrame with campaign name and date as indices and metrics as columns
    """
    # Create a list to store the processed data
    data = []

    # Process each campaign
    for campaign in campaigns:
        # Extract campaign name
        campaign_name = campaign["campaign"].get("name", "Unknown")

        # Extract date
        date = campaign["segments"].get("date", "Unknown")

        # Extract metrics
        metrics = campaign["metrics"]

        # Create a row with campaign name, date, and all metrics
        row = {"campaign_name": campaign_name, "date": date, **metrics}

        data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Convert numeric columns to appropriate types
    numeric_columns = df.columns.difference(["campaign_name", "date"])
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])

    if "costMicros" in df.columns:
        df["cost"] = df["costMicros"] / 1_000_000

    # Set campaign_name and date as index
    df = df.set_index("date").sort_index()

    return df


def parse_fb_insights_to_dataframe(campaign_insights):
    """
    Parse Facebook campaign insights data into a pandas DataFrame.

    Args:
        campaign_insights (list): List of lists containing AdsInsights objects

    Returns:
        pandas.DataFrame: DataFrame with campaign name and date as indices and metrics as columns
    """
    # Create a list to store the processed data
    data = []

    # Process each campaign's insights
    for insights_list in campaign_insights:
        # Skip empty lists
        if not insights_list:
            continue

        # Process each insight in the list
        for insight in insights_list:
            # Convert the AdsInsights object to a dictionary
            insight_dict = insight.export_all_data()

            # Extract campaign name and date (required fields)
            campaign_name = insight_dict.get("campaign_name", "Unknown")
            date = insight_dict.get("date_start", "Unknown")

            # Remove the fields we're using as indices to avoid duplication
            insight_dict.pop("campaign_name", None)
            insight_dict.pop("date_start", None)
            insight_dict.pop(
                "date_stop", None
            )  # Often redundant with date_start for daily data

            # Create a row with campaign name, date, and all remaining metrics
            row = {
                "campaign_name": campaign_name,
                "date": date,
                **insight_dict,  # Include all remaining fields as metrics
            }

            data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data)

    # If DataFrame is empty, return empty DataFrame with proper structure
    if df.empty:
        return pd.DataFrame(columns=["campaign_name", "date"]).set_index(
            ["campaign_name", "date"]
        )

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Convert numeric columns to appropriate types
    # Exclude campaign_name and date from numeric conversion
    numeric_columns = df.columns.difference(["campaign_name", "date"])
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Set campaign_name and date as index
    df = df.set_index("date").sort_index()

    return df


def get_google_ads_campaign_metrics(hourly: bool = False):
    start_time = time.time()
    logger.info("Retrieving Google Ads campaign metrics")
    campaigns = google_ads_client.get_campaigns(hourly=hourly)
    df = parse_google_ads_campaigns_to_dataframe(campaigns)
    logger.info(
        f"Retrieved Google Ads campaign metrics in {round(time.time() - start_time, 2)} seconds"
    )
    df.columns = [
        "".join("_" + c.lower() if c.isupper() else c for c in s)
        for s in list(df.columns)
    ]
    return df.rename(
        columns={
            "campaign_name": "campaign",
            "cost": "spend",
        }
    )


def get_facebook_ads_campaign_metrics(
    since: str | None = None,
    until: str | None = None,
    date_preset: str | None = None,
    time_increment: int | str = 1,
):
    """
    Retrieve Facebook Ads campaign metrics.

    Args:
        since (str | None, optional): Date string in YYYY-MM-DD format. Defaults to None.
        until (str | None, optional): Date string in YYYY-MM-DD format. Defaults to None.
        date_preset (str | None, optional): Date preset. Defaults to None.
        time_increment (int | str, optional): Time increment in days (int) or "hourly" (str) or "all_days" (str). Defaults to 1.

    Raises:
        ValueError: Either date_preset or since and until must be provided

    Returns:
        pd.DataFrame: DataFrame with campaign name and date as indices and metrics as columns
    """
    start_time = time.time()
    logger.info("Retrieving Facebook Ads campaign metrics")
    fields = [
        "campaign_name",
        "spend",
        "impressions",
        "clicks",
        "reach",
    ]
    params = {
        "time_increment": time_increment,
        # "breakdowns": "hourly_stats_aggregated_by_advertiser_time_zone",
    }
    if time_increment == "hourly":
        params["breakdowns"] = "hourly_stats_aggregated_by_advertiser_time_zone"
        params["time_increment"] = 1
    if date_preset:
        params["date_preset"] = date_preset
    elif since and until:
        params["time_range"] = {
            "since": since,
            "until": until,
        }
    else:
        raise ValueError("Either date_preset or since and until must be provided")
    fb_campaigns = get_campaigns(params=params)
    campaign_insights = []
    for campaign in fb_campaigns:
        campaign_insights.append(
            get_campaign_insights(campaign.get_id(), fields=fields, params=params)
        )
    # Create DataFrame from Facebook campaign insights
    fb_campaign_df = parse_fb_insights_to_dataframe(campaign_insights)

    logger.info(
        f"Retrieved Facebook Ads campaign metrics in {round(time.time() - start_time, 2)} seconds"
    )
    return fb_campaign_df.rename(
        columns={
            "campaign_name": "campaign",
        }
    )
