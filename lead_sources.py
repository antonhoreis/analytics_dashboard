import pandas as pd
import panel as pn

from data_sources import ads_analytics, google_analytics, hubspot_conversions, sales
import fetch_api

# --- Configuration ---
pn.extension("tabulator", "indicators", design="material")


# --- Data Loading ---
@pn.cache(ttl=3600)  # Cache the processed data for an hour
def load_and_prepare_data():
    """Loads data using fetch_api and performs initial preparation."""
    df = fetch_api.get_daily_data()
    # Ensure index is datetime
    df.index = pd.to_datetime(df.index)

    # Add platform column
    def get_platform(src):
        src = str(src).lower()
        if "google" in src:
            return "Google"
        elif "facebook" in src or "ig" in src or "instagram" in src or "meta" in src:
            return "Meta"
        else:
            return "Other"

    df["platform"] = df["source"].apply(get_platform)

    # Fill NA for cost and potential lead columns for easier aggregation
    df["cost"] = df["cost"].fillna(0)
    # Assuming 'landing_page' itself indicates a visit if present from GA source?
    # For simplicity, let's assume non-null indicates the conversion event happened.
    df["landing_page_lead"] = ~df["landing_page"].isnull()
    df["first_call_lead"] = ~df["first_call"].isnull()
    df["sales_lead"] = ~df["sales"].isnull()

    # Use campaign name, fill missing ones
    df["campaign"] = df["campaign"].fillna("Unknown")

    return df


raw_data = load_and_prepare_data()

# --- Constants ---
CONVERSION_MAP = {
    "Landing Page Visit": "landing_page_lead",
    "First Call": "first_call_lead",
    "Sale": "sales_lead",
}
DEFAULT_CONVERSION = "First Call"
# Add a small epsilon to avoid division by zero
EPSILON = 1e-9

# --- Widgets ---
min_date = raw_data.index.min().date()
max_date = raw_data.index.max().date()

date_range_slider = pn.widgets.DateRangeSlider(
    name="Date Range",
    start=min_date,
    end=max_date,
    value=(min_date, max_date),
    step=1,  # Days
)

conversion_select = pn.widgets.Select(
    name="Target Conversion",
    options=list(CONVERSION_MAP.keys()),
    value=DEFAULT_CONVERSION,
)


# --- Reactive Data Processing ---
@pn.cache  # Cache results based on widget values
def process_metrics(data, date_range, conversion_type, group_by_col):
    """Filters data and calculates metrics based on selected filters and grouping."""
    start_date, end_date = date_range
    # Ensure comparison is between datetime objects
    mask = (data.index >= pd.to_datetime(start_date)) & (
        data.index <= pd.to_datetime(end_date)
    )
    filtered_data = data[mask]

    lead_col = CONVERSION_MAP[conversion_type]

    # Calculate Costs per group
    total_costs = filtered_data.groupby(group_by_col)["cost"].sum()

    # Calculate Leads per group
    leads_data = filtered_data[filtered_data[lead_col] == True]
    total_leads = leads_data.groupby(group_by_col).size()

    # Combine metrics
    metrics = pd.DataFrame(
        {"Total Cost": total_costs, "Number of Leads": total_leads}
    ).fillna(0)  # Fill groups with 0 leads/cost if they exist in one but not the other

    # Calculate Cost per Lead
    metrics["Cost per Lead"] = (
        metrics["Total Cost"] / (metrics["Number of Leads"] + EPSILON)
    ).round(2)

    # Ensure columns have correct types
    metrics["Number of Leads"] = metrics["Number of Leads"].astype(int)

    return metrics.sort_values(by="Number of Leads", ascending=False)


# --- Reactive Plotting ---
def create_plots(metrics_df):
    """Generates bar charts for Number of Leads and Cost per Lead."""
    if metrics_df.empty:
        return pn.pane.Markdown("No data available for the selected filters.")

    # Explicitly use pandas index for x-axis if it's the campaign/platform name
    metrics_df = metrics_df.reset_index()
    group_col = metrics_df.columns[
        0
    ]  # First column is the grouping column (campaign or platform)

    leads_plot = metrics_df.hvplot.bar(
        x=group_col,
        y="Number of Leads",
        title="Number of Leads",
        xlabel="Source",
        ylabel="Count",
        rot=45,  # Rotate labels if they overlap
        height=300,
        responsive=True,
    ).opts(show_grid=True)

    cpl_plot = metrics_df.hvplot.bar(
        x=group_col,
        y="Cost per Lead",
        title="Cost per Lead",
        xlabel="Source",
        ylabel="Cost ($)",
        rot=45,  # Rotate labels if they overlap
        height=300,
        responsive=True,
    ).opts(show_grid=True)

    return pn.Column(leads_plot, cpl_plot)


# --- Reactive Binding ---
# Bind processing function to widgets for campaign and platform levels
campaign_metrics = pn.bind(
    process_metrics,
    data=raw_data,
    date_range=date_range_slider,
    conversion_type=conversion_select,
    group_by_col="campaign",
)

platform_metrics = pn.bind(
    process_metrics,
    data=raw_data,
    date_range=date_range_slider,
    conversion_type=conversion_select,
    group_by_col="platform",
)

# Bind plotting function to the processed metrics
campaign_plots = pn.bind(create_plots, metrics_df=campaign_metrics)
platform_plots = pn.bind(create_plots, metrics_df=platform_metrics)


# --- Layout ---
sidebar = pn.Column("## Filters", date_range_slider, conversion_select, width=300)

main_area = pn.Tabs(
    ("Campaign View", campaign_plots),
    ("Platform View", platform_plots),
    dynamic=True,  # Re-render only the active tab
)

template = pn.template.FastListTemplate(
    title="Lead Source Performance Dashboard",
    sidebar=[sidebar],
    main=[main_area],
    accent_base_color="#007bff",  # Example accent color
    header_background="#007bff",
)

# --- Serve the dashboard ---
template.servable()
