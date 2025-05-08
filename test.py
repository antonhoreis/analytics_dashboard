import pandas as pd
import hvplot.pandas
import panel as pn

pn.extension("echarts")
plot_df = pd.read_csv("plot_df.csv")
# plot_df
selected_metrics = [
    "first_call",
    "verbal_agreement_after_first_call",
    "placement_scheduled",
    "sales",
    "spend",
]
plot1 = plot_df.hvplot.line(
    x="time_period",
    y=selected_metrics,
    by="series",
    responsive=True,
    xlabel="Date",
    ylabel="Value",
    title=f"Key Metrics Over Time",
    legend="top",
    height=600,
)
series_list = []
plot_df["time_period"] = pd.to_datetime(plot_df["time_period"])
categories = plot_df["time_period"].dt.strftime("%Y-%m-%d").unique().tolist()

for series_name in plot_df["series"].unique():
    series_data = plot_df[plot_df["series"] == series_name]
    for metric in selected_metrics:
        if metric in series_data.columns:
            # Create series data
            data_values = []
            for date in categories:
                date_data = series_data[
                    series_data["time_period"].dt.strftime("%Y-%m-%d") == date
                ]
                value = date_data[metric].iloc[0] if not date_data.empty else None
                data_values.append(value)

            series_list.append(
                {
                    "name": series_name,
                    "type": "line",
                    "data": data_values,
                    "smooth": True,
                }
            )

# Create ECharts options
options = {
    "title": {
        "text": "Relative Change in Key Metrics (%)Key Metrics Over Time",
        "left": "center",
    },
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
    "legend": {"data": [s["name"] for s in series_list], "top": 25},
    "grid": {
        "left": "3%",
        "right": "4%",
        "bottom": "3%",
        "containLabel": True,
    },
    "xAxis": {
        "type": "category",
        "boundaryGap": False,
        "data": categories,
        "name": "Date",
    },
    "yAxis": {
        "type": "value",
        "name": "Value",
    },
    "series": series_list,
}

plot2 = pn.pane.ECharts(options=options, height=600, sizing_mode="stretch_width")
# Instantiate the template with widgets displayed in the sidebar
template = pn.template.EditableTemplate(
    editable=True,
    title="EditableTemplate",
)


template.main.extend([plot1, plot2])

template.servable()
