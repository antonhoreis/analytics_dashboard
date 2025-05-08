import panel as pn
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


KEY_METRICS = {
    "spend": "Ad spend",
    "clicks": "Ad Clicks",
    "first_call": "First Call scheduled",
    "verbal_agreement_after_first_call": "Verbal agreement (First call)",
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

# structure: {filter_type: {filter_name: filter_label}}
KEY_METRIC_COMPARISON_OPTIONS = {
    "button_group": {
        "Campaign": "campaign",
        "Source": "source",
        "Medium": "medium",
        "Content": "content",
        "Term": "term",
    },
    "date_range_picker": {
        "Date": "date",
    },
}


def key_metrics_panel(data: pd.DataFrame, global_filter_widgets: dict):
    # Create widgets for filters and comparisons
    date_range = pn.widgets.DateRangeSlider(
        name="Date Range",
        start=data.index.min().date(),  # datetime.now() - timedelta(days=90),  # data.index.min().date(),
        end=data.index.max().date(),
        value=((datetime.now() - timedelta(days=90)).date(), data.index.max().date()),
    )

    time_agg = pn.widgets.RadioButtonGroup(
        name="Time Aggregation",
        options=["daily", "weekly", "monthly"],
        value=global_filter_widgets["time_agg"].value,
    )

    # key metrics to plot
    key_metrics = pn.widgets.MultiChoice(
        name="Key Metrics",
        options=list(KEY_METRICS.values()),
        value=list(KEY_METRICS.values()),
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
                    start=data.index.min().date(),
                    end=data.index.max().date(),
                    value=(data.index.min().date(), data.index.max().date()),
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
    comparison_widgets = {}
    for filter_type, filter_options in KEY_METRIC_COMPARISON_OPTIONS.items():
        if filter_type == "button_group":
            comparison_widgets["button_group"] = pn.widgets.RadioButtonGroup(
                name="Dimension",
                options=["None"] + list(filter_options.keys()),
                value="None",
                orientation="vertical",
            )
        elif filter_type == "date_range_picker":
            comparison_widgets["date_range_picker"] = []
            for label, key in filter_options.items():
                activation_button = pn.widgets.Button(
                    name=label,
                    icon="calendar",
                )
                data_range_slider = pn.widgets.DateRangePicker(
                    name=label,
                    start=data.index.min().date(),
                    end=data.index.max().date(),
                    value=(data.index.min().date(), data.index.max().date()),
                    disabled=True,
                )

                # Create a toggle function for the button
                def toggle_date_picker(event, slider=data_range_slider):
                    slider.disabled = not slider.disabled

                # Link the button click to the toggle function
                activation_button.on_click(toggle_date_picker)

                comparison_widgets["date_range_picker"].append(
                    pn.Column(
                        activation_button,
                        data_range_slider,
                    )
                )
    # Add new widgets for relative metrics and trend lines
    show_relative = pn.widgets.Checkbox(name="Show Relative Change (%)", value=False)
    show_trend = pn.widgets.Checkbox(name="Show Trend Lines", value=False)

    # Function to create the plot
    def create_key_metrics_plot(
        data,
        date_range,
        time_agg,
        selected_metrics,
        local_filters,
        comparison_dimensions,
        comparison_date_ranges,
        show_relative=False,
        show_trend=False,
    ):
        # Filter data by date range
        filtered_data = data[
            (data.index >= pd.Timestamp(date_range[0]))
            & (data.index <= pd.Timestamp(date_range[1]))
        ]

        # Apply local filters
        for filter_name, filter_value in local_filters.items():
            if filter_name in filtered_data.columns and filter_value:
                if isinstance(filter_value, list):  # MultiChoice filters
                    if filter_value:  # Only filter if values are selected
                        filtered_data = filtered_data[
                            filtered_data[filter_name].isin(filter_value)
                        ]
                elif (
                    isinstance(filter_value, tuple) and len(filter_value) == 2
                ):  # DateRange
                    filtered_data = filtered_data[
                        (filtered_data[filter_name] >= pd.Timestamp(filter_value[0]))
                        & (filtered_data[filter_name] <= pd.Timestamp(filter_value[1]))
                    ]
                elif isinstance(filter_value, bool):  # Boolean
                    filtered_data = filtered_data[
                        filtered_data[filter_name] == filter_value
                    ]
                else:  # Single value filters
                    filtered_data = filtered_data[
                        filtered_data[filter_name] == filter_value
                    ]

        # drop rows where all metrics are 0
        metrics_to_check = [m for m in selected_metrics if m in filtered_data.columns]
        if metrics_to_check:
            filtered_data = filtered_data[
                ~(filtered_data[metrics_to_check] == 0).all(axis=1)
            ]

            # Also identify and remove series where all values are 0
            zero_metrics = []
            for metric in metrics_to_check:
                if (filtered_data[metric] == 0).all():
                    zero_metrics.append(metric)

            # Remove metrics that are all zeros from selected_metrics
            selected_metrics = [m for m in selected_metrics if m not in zero_metrics]

            # If no metrics remain after filtering, return a message
            if not selected_metrics:
                return pn.pane.Markdown(
                    "No non-zero data available for the selected metrics and filters"
                )

        # Aggregate by time
        if time_agg == "daily":
            filtered_data["time_period"] = filtered_data.index
        elif time_agg == "weekly":
            filtered_data["time_period"] = filtered_data.index.to_period("W").start_time
        elif time_agg == "monthly":
            filtered_data["time_period"] = filtered_data.index.to_period("M").start_time

        # Prepare data for plotting
        if not selected_metrics:
            return pn.pane.Markdown("Please select at least one metric to display")

        # Create a pivot table for plotting
        if comparison_dimensions or comparison_date_ranges:
            # Handle comparison by dimensions or date ranges
            fig = go.Figure()

            # Handle dimension comparison (e.g., by campaign, source, etc.)
            if comparison_dimensions:
                comparison_dim = comparison_dimensions[
                    0
                ]  # Use the first selected dimension

                for metric in selected_metrics:
                    # Group by time period and the comparison dimension
                    comparison_data = (
                        filtered_data.groupby(["time_period", comparison_dim])[metric]
                        .sum()
                        .reset_index()
                    )

                    # Get unique values for the comparison dimension
                    unique_values = comparison_data[comparison_dim].unique()

                    # Create a line for each unique value
                    for value in unique_values:
                        value_data = comparison_data[
                            comparison_data[comparison_dim] == value
                        ]
                        if not value_data.empty:
                            fig.add_trace(
                                go.Scatter(
                                    x=value_data["time_period"],
                                    y=value_data[metric],
                                    mode="lines+markers",
                                    name=f"{KEY_METRICS.get(metric, metric)} - {value}",
                                    hovertemplate="%{y:.2f}",
                                )
                            )

            # Handle date range comparison
            elif comparison_date_ranges:
                # First, plot the main date range
                for metric in selected_metrics:
                    metric_data = (
                        filtered_data.groupby("time_period")[metric].sum().reset_index()
                    )
                    if not metric_data.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=metric_data["time_period"],
                                y=metric_data[metric],
                                mode="lines+markers",
                                name=f"{KEY_METRICS.get(metric, metric)} - Current",
                                hovertemplate="%{y:.2f}",
                            )
                        )

                # Then plot each comparison date range
                for i, comp_range in enumerate(comparison_date_ranges):
                    # Get data for the comparison range
                    comp_data = data[
                        (data.index >= pd.Timestamp(comp_range[0]))
                        & (data.index <= pd.Timestamp(comp_range[1]))
                    ].copy()

                    # Apply the same time aggregation
                    if time_agg == "daily":
                        comp_data["time_period"] = comp_data.index
                    elif time_agg == "weekly":
                        comp_data["time_period"] = comp_data.index.to_period(
                            "W"
                        ).start_time
                    elif time_agg == "monthly":
                        comp_data["time_period"] = comp_data.index.to_period(
                            "M"
                        ).start_time

                    # Normalize the dates for alignment
                    if not comp_data.empty:
                        # Calculate days offset for alignment
                        main_start = pd.Timestamp(date_range[0])
                        comp_start = pd.Timestamp(comp_range[0])

                        for metric in selected_metrics:
                            metric_data = (
                                comp_data.groupby("time_period")[metric]
                                .sum()
                                .reset_index()
                            )
                            if not metric_data.empty:
                                # Align the dates by shifting to match the main date range
                                days_diff = (main_start - comp_start).days
                                metric_data["aligned_date"] = metric_data[
                                    "time_period"
                                ].apply(lambda x: x + pd.Timedelta(days=days_diff))

                                fig.add_trace(
                                    go.Scatter(
                                        x=metric_data["aligned_date"],
                                        y=metric_data[metric],
                                        mode="lines+markers",
                                        line=dict(dash="dot"),
                                        name=f"{KEY_METRICS.get(metric, metric)} - Comparison {i + 1}",
                                        hovertemplate="%{y:.2f}",
                                    )
                                )

            # Apply relative change calculation if requested
            if show_relative:
                # Recalculate all traces to show relative change
                for trace in fig.data:
                    if len(trace.y) > 0:
                        first_value = trace.y[0] if trace.y[0] != 0 else 1
                        trace.y = [(y / first_value * 100 - 100) for y in trace.y]

            # Add trend lines if requested
            if show_trend:
                # Define a color palette
                colors = px.colors.qualitative.Plotly  # Plotly's default color sequence

                # Keep track of which series we've seen
                color_mapping = {}
                color_idx = 0

                # First pass: assign colors to original series
                for series in filtered_data["series"].unique():
                    color_mapping[series] = colors[color_idx % len(colors)]
                    color_idx += 1

                # Replace the original traces with explicitly colored ones
                new_data = []
                for trace in fig.data:
                    series_name = trace.name
                    if series_name in color_mapping:
                        trace.line.color = color_mapping[series_name]
                    new_data.append(trace)

                fig.data = new_data

                # Now add trend lines with matching colors
                for series in filtered_data["series"].unique():
                    series_data = filtered_data[filtered_data["series"] == series]
                    # Get the metric that corresponds to this series
                    metric_key = None
                    for m_key, m_value in KEY_METRICS.items():
                        if m_value == series:
                            metric_key = m_key
                            break

                    if (
                        metric_key
                        and metric_key in selected_metrics
                        and len(series_data) > 1
                    ):
                        # Calculate trend line
                        x = np.arange(len(series_data))
                        y = series_data[metric_key].values
                        z = np.polyfit(x, y, 1)
                        p = np.poly1d(z)

                        # Get x values for plotting
                        x_dates = series_data["time_period"].values

                        # Add trend line with matching color
                        fig.add_trace(
                            go.Scatter(
                                x=x_dates,
                                y=p(x),
                                mode="lines",
                                line=dict(dash="dash", color=color_mapping[series]),
                                name=f"Trend: {series}",
                            )
                        )

            # Update layout
            fig.update_layout(
                title={
                    "text": "Relative Change in Key Metrics (%) - Comparison"
                    if show_relative
                    else "Key Metrics Comparison",
                    "x": 0.5,
                },
                xaxis_title="Date",
                yaxis_title="Percent Change (%)" if show_relative else "Value",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                ),
                hovermode="x unified",
                template="plotly_dark" if pn.config.theme == "dark" else "plotly_white",
                height=600,
            )

            # Return Plotly pane
            plot = pn.pane.Plotly(fig, sizing_mode="stretch_both")
            return plot

        else:
            # Simple time series without comparison
            plot_data = []

            for metric in selected_metrics:
                metric_data = (
                    filtered_data.groupby("time_period")[metric].sum().reset_index()
                )
                metric_data["series"] = KEY_METRICS.get(metric, metric)
                plot_data.append(metric_data)

            if plot_data:
                plot_df = pd.concat(plot_data)

                # Calculate relative change if requested
                if show_relative:
                    for metric in selected_metrics:
                        metric_data = plot_df[
                            plot_df["series"] == KEY_METRICS.get(metric, metric)
                        ]
                        first_value = (
                            metric_data[metric].iloc[0] if not metric_data.empty else 1
                        )

                        # Avoid division by zero
                        if first_value == 0:
                            first_value = 1

                        # Calculate percentage change for this metric
                        try:
                            plot_df.loc[
                                plot_df["series"] == KEY_METRICS.get(metric, metric),
                                metric,
                            ] = np.floor(
                                pd.to_numeric(
                                    (
                                        plot_df.loc[
                                            plot_df["series"]
                                            == KEY_METRICS.get(metric, metric),
                                            metric,
                                        ]
                                        / first_value
                                        * 100
                                        - 100
                                    ),
                                    errors="coerce",
                                )
                            ).astype("Int64")
                        except TypeError as e:
                            print(e)
                            print(plot_df)
                            print(metric)
                            print(first_value)
                # Create a Plotly figure instead of ECharts
                fig = go.Figure()

                # Add data series to the plot
                for series in plot_df["series"].unique():
                    series_data = plot_df[plot_df["series"] == series]
                    # Get the metric that corresponds to this series
                    metric_key = None
                    for m_key, m_value in KEY_METRICS.items():
                        if m_value == series:
                            metric_key = m_key
                            break

                    if metric_key and metric_key in selected_metrics:
                        fig.add_trace(
                            go.Scatter(
                                x=series_data["time_period"],
                                y=series_data[metric_key],
                                mode="lines+markers",
                                name=series,
                                hovertemplate="%{y:.2f}",
                            )
                        )

                # Add trend lines if requested
                if show_trend:
                    # Define a color palette
                    colors = (
                        px.colors.qualitative.Plotly
                    )  # Plotly's default color sequence

                    # Keep track of which series we've seen
                    color_mapping = {}
                    color_idx = 0

                    # First pass: assign colors to original series
                    for series in plot_df["series"].unique():
                        color_mapping[series] = colors[color_idx % len(colors)]
                        color_idx += 1

                    # Replace the original traces with explicitly colored ones
                    new_data = []
                    for trace in fig.data:
                        series_name = trace.name
                        if series_name in color_mapping:
                            trace.line.color = color_mapping[series_name]
                        new_data.append(trace)

                    fig.data = new_data

                    # Now add trend lines with matching colors
                    for series in plot_df["series"].unique():
                        series_data = plot_df[plot_df["series"] == series]
                        # Get the metric that corresponds to this series
                        metric_key = None
                        for m_key, m_value in KEY_METRICS.items():
                            if m_value == series:
                                metric_key = m_key
                                break

                        if (
                            metric_key
                            and metric_key in selected_metrics
                            and len(series_data) > 1
                        ):
                            # Calculate trend line
                            x = np.arange(len(series_data))
                            y = series_data[metric_key].values
                            z = np.polyfit(x, y, 1)
                            p = np.poly1d(z)

                            # Get x values for plotting
                            x_dates = series_data["time_period"].values

                            # Add trend line with matching color
                            fig.add_trace(
                                go.Scatter(
                                    x=x_dates,
                                    y=p(x),
                                    mode="lines",
                                    line=dict(dash="dash", color=color_mapping[series]),
                                    name=f"Trend: {series}",
                                )
                            )

                # Update layout
                fig.update_layout(
                    title={
                        "text": "Relative Change in Key Metrics (%)"
                        if show_relative
                        else "Key Metrics Over Time",
                        "x": 0.5,
                    },
                    xaxis_title="Date",
                    yaxis_title="Percent Change (%)" if show_relative else "Value",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                    ),
                    hovermode="x unified",
                    template="plotly_dark"
                    if pn.config.theme == "dark"
                    else "plotly_white",
                    height=600,
                )

                # Return Plotly pane
                plot = pn.pane.Plotly(fig, sizing_mode="stretch_both")
                return plot

            else:
                return pn.pane.Markdown("No data available for the selected filters")

    # Update function for the dashboard
    @pn.depends(
        date_range.param.value,
        time_agg.param.value,
        key_metrics.param.value,
        *[v.param.value for v in local_filters.values()],
        *[v.param.value for k, v in comparison_widgets.items() if k == "button_group"],
        *[
            w.param.value
            for drp in comparison_widgets.get("date_range_picker", [])
            for w in drp
        ],
        show_relative.param.value,
        show_trend.param.value,
    )
    def update_key_metrics_chart(date_range_val, time_agg_val, key_metrics_val, *args):
        if not key_metrics_val:  # Ensure at least one metric is selected
            return pn.pane.Markdown("Please select at least one metric to display.")

        # Extract filter values, comparison options, and other settings from args
        local_filter_values = {
            name: args[i] for i, name in enumerate(local_filters.keys())
        }

        comparison_dimensions = [
            KEY_METRIC_COMPARISON_OPTIONS[k].get(v.value)
            for k, v in comparison_widgets.items()
            if k == "button_group" and v.value != "None"
        ]
        comparison_date_ranges = [
            drp[1].param.value
            for drp in comparison_widgets.get("date_range_picker", [])
            if drp[0].value
        ]

        show_relative_val = args[-2]
        show_trend_val = args[-1]

        # Create the plot
        swap = lambda x: {v: k for k, v in x.items()}
        plot = create_key_metrics_plot(
            data,
            date_range_val,
            time_agg_val,
            [swap(KEY_METRICS)[k] for k in key_metrics_val],
            local_filter_values,
            comparison_dimensions,
            comparison_date_ranges,
            show_relative=show_relative_val,
            show_trend=show_trend_val,
        )

        return plot

    # Chart with collapsible sidebar for settings
    chart_settings = pn.Card(
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
        comparison_widgets.get("button_group", []),
        *comparison_widgets.get("date_range_picker", []),
        pn.layout.Divider(),
        "### Visualization Options",
        show_relative,
        show_trend,
        min_width=300,
        sizing_mode="stretch_both",
        collapsed=False,  # Start expanded
        title="Chart Settings ▼",  # Custom expanded title
        styles={"padding": "0", "margin": "0"},
    )

    chart = pn.Column(
        "## Key Metrics and Conversions over Time",
        update_key_metrics_chart,
        sizing_mode="stretch_both",
    )

    return chart_settings, chart
