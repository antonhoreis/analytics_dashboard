import sys

print(sys.executable)
import hvplot.pandas
import numpy as np
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

pd.options.mode.chained_assignment = None  # default='warn'

pn.extension(design="material")
pn.extension("tabulator")
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

KEY_METRICS = {
    "spend": "Ad spend",
    "clicks": "Ad Clicks",
    "first_call_scheduled": "First Call scheduled",
    "verbal_agreement": "Verbal agreement (First call)",
    "placement_scheduled": "Placement scheduled",
    "sales": "Sale",
}

# structure: {filter_type: {filter_name: (filter_label, data_sources)}}
KEY_METRIC_FILTERS = {
    "numerical": {
        "spend": ("Ad spend", ["facebook", "google"]),
        "clicks": ("Ad Clicks", ["facebook", "google"]),
    },
    "categorical": {
        "conversion": ("Conversion", ["hubspot", "sales"]),
        "metric": ("Metric", ["facebook", "google", "landing_page"]),
    },
    "date_range": {
        "date": ("Date", ["facebook", "google", "landing_page", "hubspot", "sales"]),
    },
    "multi_choice": {
        "campaign": (
            "Campaign",
            ["facebook", "google", "landing_page", "hubspot", "sales"],
        ),
        "source": ("Source", ["landing_page", "hubspot", "sales"]),
        "medium": ("Medium", ["landing_page", "hubspot", "sales"]),
        "content": ("Content", ["landing_page", "hubspot", "sales"]),
        "term": ("Term", ["landing_page", "hubspot", "sales"]),
    },
    "boolean": {},
}

# structure: {filter_type: filter_name}
KEY_METRIC_COMPARISON_OPTIONS = {
    "campaign": "Campaign",
    "source": "Source",
    "medium": "Medium",
    "content": "Content",
    "term": "Term",
}  # TODO

CONVERSION_ATTRIBUTION_CONVERSION_TYPES = {
    "ad_click": "Ad Click",
    "first_call": "First call",
    "verbal_agreement": "Verbal agreement (First call)",
    "placement_scheduled": "Placement scheduled",
    "sale": "Sale",
}

CONVERSION_ATTRIBUTION_BREAKDOWN = {
    "source": "Source",
    "medium": "Medium",
    "campaign": "Campaign",
    "content": "Content",
    "term": "Term",
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


@pn.cache
def get_daily_data():
    hs = get_hubspot_conversions(filters=None)
    sales = get_sales_data()
    fb = get_facebook_ads_campaign_metrics()
    ga = get_google_ads_campaign_metrics()
    lp = get_landing_page_report()
    data = pd.concat([hs, sales, fb, ga, lp]).infer_objects().convert_dtypes()
    return data


def key_metrics_panel():
    data = get_daily_data()
    # Ensure date column is datetime
    data["date"] = pd.to_datetime(data["date"])

    # Create widgets for filters and comparisons
    date_range = pn.widgets.DateRangeSlider(
        name="Date Range",
        start=data["date"].min().date(),
        end=data["date"].max().date(),
        value=(data["date"].min().date(), data["date"].max().date()),
    )

    time_agg = pn.widgets.RadioButtonGroup(
        name="Time Aggregation",
        options=["daily", "weekly", "monthly"],
        value=GLOBAL_FILTER_WIDGETS["time_agg"].value,
    )

    # key metrics to plot
    key_metrics = pn.widgets.MultiChoice(
        name="Key Metrics",
        options=list(KEY_METRICS.keys()),
    )

    # local filters
    local_filters = {}
    for filter_type, filter_options in KEY_METRIC_FILTERS.items():
        for key, (name, _) in filter_options.items():
            if filter_type == "multi_choice":
                options = []
                if key in data.columns:
                    options = list(data[key].dropna().unique())
                local_filters[key] = pn.widgets.MultiChoice(
                    name=name,
                    options=options,
                )
            elif filter_type == "date_range":
                local_filters[key] = pn.widgets.DateRangeSlider(
                    name=name,
                    start=data["date"].min().date(),
                    end=data["date"].max().date(),
                    value=(data["date"].min().date(), data["date"].max().date()),
                )
            elif filter_type == "radio_button_group":
                options = []
                if key in data.columns:
                    options = list(data[key].dropna().unique())
                local_filters[key] = pn.widgets.RadioButtonGroup(
                    name=name,
                    options=options,
                )
            elif filter_type == "boolean":
                local_filters[key] = pn.widgets.Checkbox(
                    name=name,
                    value=False,
                )

    # Comparison selector
    comparison_options = {}
    for name, label in KEY_METRIC_COMPARISON_OPTIONS.items():
        comparison_options[label] = pn.widgets.Select(
            name=label,
            options=list(data[name].dropna().unique()) + ["None"],
            value="None",
            styles={"background-color": "var(--pn-primary-background)"},
        )

    # Function to create the plot
    def create_key_metrics_plot(data, comparison_options):
        # TODO
        return pn.widgets.Tabulator(data)

    # Update function for the dashboard
    @pn.depends(
        date_range.param.value,
        time_agg.param.value,
        key_metrics.param.value,
        *[v.param.value for v in local_filters.values()],
        *[v.param.value for v in comparison_options.values()],
    )
    def update_key_metrics_chart(
        date_range,
        time_agg,
        key_metrics,
        local_filters,
        comparison_options,
    ):
        if not key_metrics:  # Ensure at least one conversion type is selected
            return pn.pane.Markdown(
                "Please select at least one metric or conversion type."
            )

        plot = create_key_metrics_plot(data, comparison_options)

        return plot

    chart_settings = pn.WidgetBox(
        "## Chart Settings",
        date_range,
        time_agg,
        pn.layout.Divider(),
        "### Select Metrics and Conversions",
        key_metrics,
        pn.layout.Divider(),
        "### Filters",
        *local_filters.values(),
        pn.layout.Divider(),
        "### Compare Metrics",
        *comparison_options.values(),
        width=350,
        styles={"padding": "10px"},
    )
    chart = pn.Column(
        "## Key Metrics and Conversions over Time",
        create_key_metrics_plot(data, comparison_options),
        sizing_mode="stretch_width",
    )

    return pn.Row(chart_settings, chart, sizing_mode="stretch_width")


def conversion_attribution_panel():
    # TODO
    return pn.Row(
        pn.pane.Markdown("Conversion Attribution"),
        sizing_mode="stretch_width",
    )


def KPI_panel():
    # TODO
    return pn.Row(
        pn.pane.Markdown("KPI"),
        sizing_mode="stretch_width",
    )


# Instantiate the template with widgets displayed in the sidebar
template = pn.template.EditableTemplate(
    editable=True,
    title="EditableTemplate",
    sidebar=list(GLOBAL_FILTER_WIDGETS.values()),
)

template.main.extend(
    [
        KPI_panel(),
        key_metrics_panel(),
        conversion_attribution_panel(),
    ]
)

template.servable()
