from data_sources import (
    ads_analytics,
    google_analytics,
    hubspot_conversions,
    sales as sales_data,
)
import pandas as pd
import panel as pn


@pn.cache(ttl=3600, to_disk=True)
def get_daily_data() -> pd.DataFrame:
    """Fetch all data sources and combine into a single dataframe with a datetime index.
    Returns:
        pd.DataFrame: A dataframe with a datetime index.
    """
    hs = hubspot_conversions.get_hubspot_conversions(filters=None)
    sales = sales_data.get_sales_data()
    fb = ads_analytics.get_facebook_ads_campaign_metrics()
    ga = ads_analytics.get_google_ads_campaign_metrics()
    lp = google_analytics.get_landing_page_report()
    data = pd.concat([hs, sales, fb, ga, lp]).infer_objects().convert_dtypes()
    # Ensure index is datetime
    data.index = pd.to_datetime(data.index)
    return data


@pn.cache(ttl=3600, to_disk=True)
def get_hourly_data() -> pd.DataFrame:
    """Fetch ads analytics and first call data and combine into a single dataframe with a datetime index. Might be useful for restoring lost tracking data.
    Returns:
        pd.DataFrame: A dataframe with a datetime index.
    """
    fc = hubspot_conversions.get_first_calls()
    fb = ads_analytics.get_facebook_ads_campaign_metrics(time_increment="hourly")
    ga = ads_analytics.get_google_ads_campaign_metrics(hourly=True)
    data = pd.concat([fc, fb, ga]).infer_objects().convert_dtypes()
    # Ensure index is datetime
    data.index = pd.to_datetime(data.index)
    return data
