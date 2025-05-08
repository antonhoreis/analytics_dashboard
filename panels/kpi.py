import panel as pn
import pandas as pd


def KPI_panel(data: pd.DataFrame, global_filter_widgets: dict):
    # TODO
    return pn.Row(
        pn.pane.Markdown("KPI"),
        sizing_mode="stretch_width",
    )
