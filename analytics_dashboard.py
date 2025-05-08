import pandas as pd
import panel as pn
from datetime import datetime, timedelta

from ads_analytics import (
    get_facebook_ads_campaign_metrics,
    get_google_ads_campaign_metrics,
)
from google_analytics import get_landing_page_report
from hubspot_conversions import get_hubspot_conversions
from sales import get_sales_data

from panels import (
    key_metrics,
    conversion_attribution,
    kpi,
    new_business_funnel,
)

pd.options.mode.chained_assignment = None  # default='warn'

pn.extension(design="material")
pn.extension("plotly")
pn.config.theme = "dark"

plot_opts = dict(responsive=True, min_height=400)


# structure: {filter_type: {filter_name: filter_label}}
GLOBAL_FILTERS = {
    "date_range": {
        "date": "date",
    },
    "multi_choice": {
        "campaign": "Campaign",
        "source": "Source",
        "medium": "Medium",
        "content": "Content",
        "term": "Term",
    },
    "radio_button_group": {
        "time_agg": "Time Aggregation",
    },
}

GLOBAL_FILTER_WIDGETS = {}
for filter_type, filter_options in GLOBAL_FILTERS.items():
    for key, value in filter_options.items():
        if filter_type == "multi_choice":
            GLOBAL_FILTER_WIDGETS[key] = pn.widgets.MultiChoice(
                name=value,
                options=[],  # TODO: update when panels are created
            )
        elif filter_type == "radio_button_group":
            GLOBAL_FILTER_WIDGETS[key] = pn.widgets.RadioButtonGroup(
                name=value,
                options=[],  # TODO: update when panels are created
            )
        elif filter_type == "date_range":
            GLOBAL_FILTER_WIDGETS[key] = pn.widgets.DateRangeSlider(
                name=value,
                start=datetime.now()
                - timedelta(days=90),  # TODO: update when panels are created
                end=datetime.now()
                + timedelta(days=90),  # TODO: update when panels are created
                value=(
                    datetime.now() - timedelta(days=90),
                    datetime.now(),
                ),
            )


@pn.cache(ttl=3600, to_disk=True)
def get_daily_data() -> pd.DataFrame:
    """Fetch all data sources and combine into a single dataframe with a datetime index.
    Returns:
        pd.DataFrame: A dataframe with a datetime index.
    """
    hs = get_hubspot_conversions(filters=None)
    sales = get_sales_data()
    fb = get_facebook_ads_campaign_metrics()
    ga = get_google_ads_campaign_metrics()
    lp = get_landing_page_report()
    data = pd.concat([hs, sales, fb, ga, lp]).infer_objects().convert_dtypes()
    # Ensure index is datetime
    data.index = pd.to_datetime(data.index)
    return data


data = get_daily_data()


# Instantiate the template with widgets displayed in the sidebar
template = pn.template.FastGridTemplate(
    title="LALIA Analytics Dashboard",
    sidebar=GLOBAL_FILTER_WIDGETS.values(),
    sidebar_width=250,
    collapsed_sidebar=True,
    theme="dark",
)


key_metrics_settings, key_metrics_chart = key_metrics.key_metrics_panel(
    data, GLOBAL_FILTER_WIDGETS
)
template.main[0, :] = kpi.KPI_panel(data, GLOBAL_FILTER_WIDGETS)
template.main[1:6, 0:3] = key_metrics_settings
template.main[1:6, 3:] = key_metrics_chart
template.main[6:, :] = conversion_attribution.conversion_attribution_panel(
    data, GLOBAL_FILTER_WIDGETS
)
template.main[11:16, :] = new_business_funnel.get_funnel_sankey_panel()
# template.main.extend(
#     [
#         kpi.KPI_panel(data, GLOBAL_FILTER_WIDGETS),
#         key_metrics.key_metrics_panel(data, GLOBAL_FILTER_WIDGETS),
#         conversion_attribution.conversion_attribution_panel(
#             data, GLOBAL_FILTER_WIDGETS
#         ),
#     ]
# )

template.servable()
