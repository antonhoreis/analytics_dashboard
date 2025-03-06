import os
import logging
from dotenv import load_dotenv
import pandas as pd
import time

load_dotenv()
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    FilterExpression,
    Filter,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def response_to_dataframe(response):
    """
    Transform a Google Analytics API response into a pandas DataFrame.

    Args:
        response: The response object from the Google Analytics API

    Returns:
        pandas.DataFrame: A DataFrame with dimensions as index, metrics as columns,
                         and the corresponding values
    """

    # Extract dimension and metric names
    dimension_names = [dim.name for dim in response.dimension_headers]
    metric_names = [metric.name for metric in response.metric_headers]

    # Create a list to store the data
    data = []

    # Process each row in the response
    for row in response.rows:
        # Extract dimension values
        dimension_values = [dim_value.value for dim_value in row.dimension_values]

        # Extract metric values
        metric_values = [metric_value.value for metric_value in row.metric_values]

        # Combine dimension and metric values
        row_data = dimension_values + metric_values
        data.append(row_data)

    # Create DataFrame
    df = pd.DataFrame(data, columns=dimension_names + metric_names)

    # Set dimensions as index if there are dimensions
    if dimension_names:
        df = df.set_index(dimension_names)

    return df


def get_landing_page_report():
    start_time = time.time()
    logger.info("Retrieving landing page report")
    property_id = "346484289"

    client = BetaAnalyticsDataClient()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="hostname"),
            Dimension(name="landingPage"),
            Dimension(name="sessionManualSource"),
            Dimension(name="sessionManualMedium"),
            Dimension(name="sessionManualCampaignName"),
            Dimension(name="sessionManualAdContent"),
            Dimension(name="sessionManualTerm"),
            # Dimension(name="keyEvents"),
            # Dimension(name="sessionKeyEventRate"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="eventCount"),  # Metric(name="engagementRate"),
        ],
        date_ranges=[DateRange(start_date="90daysAgo", end_date="today")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="pageTitle",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.CONTAINS,
                    value="LALIA | Effective Online German Language Courses",
                ),
            )
        ),
    )
    response = client.run_report(request)
    logger.info(
        f"Retrieved landing page report in {round(time.time() - start_time, 2)} seconds"
    )

    df = response_to_dataframe(response)
    df = df[
        df.index.get_level_values(1).isin(["/hp-2", "/", "(not set)"])
    ].reset_index()
    df.date = pd.to_datetime(df.date)
    df.landingPage = df.hostname.map(
        {
            "lalia-berlin.com": "Zenler ",
            "page.lalia-berlin.com": "Hubspot",
        }
    ) + df.landingPage.map(
        {
            "(not set)": "1",
            "/": "1",
            "/hp-2": "2",
        }
    )

    return df
