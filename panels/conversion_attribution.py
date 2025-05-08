import panel as pn
import pandas as pd

CONVERSION_ATTRIBUTION_CONVERSION_TYPES = {
    "ad_click": "Ad Click",
    "first_call": "First call",
    "verbal_agreement_after_first_call": "Verbal agreement (First call)",
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


def conversion_attribution_panel(data: pd.DataFrame, global_filter_widgets: dict):
    # TODO
    return pn.Row(
        pn.pane.Markdown("Conversion Attribution"),
        sizing_mode="stretch_both",
    )
