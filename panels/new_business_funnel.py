import plotly.graph_objects as go
import pandas as pd
import colorsys
from collections import defaultdict
import panel as pn
from hubspot_conversions import (
    get_first_calls,
    get_first_call_verbal_agreements,
    get_placement_calls,
    get_users,
)


def get_funnel_sankey_panel():
    funnel_data = get_funnel_data()

    widgets = get_funnel_widgets(funnel_data)
    sankey_chart = get_sankey_chart(funnel_data)
    return pn.Column(widgets, sankey_chart)


def get_funnel_data():
    first_calls_df = get_first_calls()
    verbal_agreement_deals = get_first_call_verbal_agreements()
    placement_deals = get_placement_calls()
    users = get_users()

    funnel_data = pd.concat(
        [first_calls_df, verbal_agreement_deals, placement_deals]
    ).dropna(subset=["contact_email", "meeting_owner_id"])
    funnel_data["user"] = (
        users.loc[funnel_data.meeting_owner_id]["first_name"]
        + " "
        + users.loc[funnel_data.meeting_owner_id]["last_name"]
    ).values

    return funnel_data


def get_sankey_chart(funnel_data: pd.DataFrame):
    labels = [
        "First Call",
        "First Call Verbal Agreement",
        "Placement Call",
        "Placement Verbal Agreement",
        "Sale",
    ]

    # Define allowed transitions in the funnel
    transitions = [
        ("First Call", "First Call Verbal Agreement"),
        ("First Call", "Placement Call"),
        ("First Call Verbal Agreement", "Sale"),
        ("Placement Call", "Placement Verbal Agreement"),
        ("Placement Call", "Sale"),
        ("Placement Verbal Agreement", "Sale"),
    ]

    # Dynamically create sources and targets arrays
    sources = []
    targets = []
    for source_label, target_label in transitions:
        sources.append(labels.index(source_label))
        targets.append(labels.index(target_label))

    def get_index(from_conversion, to_conversion):
        """Get the index in the values array for a specific transition between stages"""
        try:
            from_idx = labels.index(from_conversion)
            to_idx = labels.index(to_conversion)

            for idx, (src, tgt) in enumerate(zip(sources, targets)):
                if src == from_idx and tgt == to_idx:
                    return idx

            return -1  # Return -1 if not found
        except ValueError:
            return -1  # Return -1 if label not found

    def compute_sankey(group):
        # Create a list to store individual links
        links = []  # Each link will be a tuple of (source, target, value, user)

        conversions = group.conversion.values
        if "First call" not in conversions:
            return links

        # Process each transition based on the user who handled it
        if "Verbal agreement after first call" in conversions:
            # Get the specific user who handled this conversion
            user = group.user.loc[
                group.conversion == "Verbal agreement after first call"
            ].iloc[0]
            source_idx = labels.index("First Call")
            target_idx = labels.index("First Call Verbal Agreement")
            links.append((source_idx, target_idx, 1, user))

            if "closedwon" in group.dealstage.values:
                source_idx = labels.index("First Call Verbal Agreement")
                target_idx = labels.index("Sale")
                links.append((source_idx, target_idx, 1, user))

        if "Placement scheduled" in conversions:
            # Get the user who scheduled the first call
            fc_user = group.user.loc[group.conversion == "First call"].iloc[0]
            source_idx = labels.index("First Call")
            target_idx = labels.index("Placement Call")
            links.append((source_idx, target_idx, 1, fc_user))

            # Get the user who scheduled the placement
            if any(group.conversion == "Placement scheduled"):
                placement_user = group.user.loc[
                    group.conversion == "Placement scheduled"
                ].iloc[0]

                if "true" in group.verbal_agreement.values:
                    source_idx = labels.index("Placement Call")
                    target_idx = labels.index("Placement Verbal Agreement")
                    links.append((source_idx, target_idx, 1, placement_user))

                    if "closedwon" in group.dealstage.values:
                        source_idx = labels.index("Placement Verbal Agreement")
                        target_idx = labels.index("Sale")
                        links.append((source_idx, target_idx, 1, placement_user))

                elif "closedwon" in group.dealstage.values:
                    source_idx = labels.index("Placement Call")
                    target_idx = labels.index("Sale")
                    links.append((source_idx, target_idx, 1, placement_user))

        return links

    # Process data to get individual links
    all_links = []
    for email, group_data in funnel_data.groupby("contact_email"):
        links = compute_sankey(
            group_data[["conversion", "dealstage", "verbal_agreement", "user"]]
        )
        all_links.extend(links)

    # Create a dynamic color palette for users
    def generate_color_palette(users):
        """Generate a color palette for users with consistent colors"""

        # Get unique users
        unique_users = sorted(list(set(users)))
        n = len(unique_users)

        # Generate colors using HSV color space to ensure they're visually distinct
        colors = {}
        for i, user in enumerate(unique_users):
            # Generate evenly spaced hues
            hue = i / n
            # Use high saturation and value for vibrant colors
            saturation = 0.7
            value = 0.9

            # Convert HSV to RGB
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)

            # Convert to rgba string with opacity
            colors[user] = f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, 0.8)"

        return colors

    # Extract all users from links
    all_users = [link[3] for link in all_links]
    user_colors = generate_color_palette(all_users)

    # Group links by source, target, and user
    link_dict = defaultdict(int)
    for source, target, value, user in all_links:
        link_dict[(source, target, user)] += value

    # Prepare data for Sankey diagram
    sources = []
    targets = []
    values = []
    colors = []
    user_labels = []

    for (source, target, user), value in link_dict.items():
        sources.append(source)
        targets.append(target)
        values.append(value)
        colors.append(user_colors[user])
        user_labels.append(user)

    # Apply the same color scheme to nodes (based on position in funnel)
    node_colors = ["rgba(150, 150, 150, 0.8)"] * len(labels)  # Neutral color for nodes

    # Create the Sankey diagram
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=labels,
                    color=node_colors,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    label=user_labels,  # Show user name on hover
                    color=colors,  # Color by user
                ),
            )
        ]
    )

    # Create a custom legend for user colors
    legend_y_start = 1.0

    # Add title and descriptions
    fig.update_layout(
        title_text="Conversion Funnel by User",
        font_size=10,
        height=600,
        width=1000,
        margin=dict(t=100, l=50, r=250),  # Extra right margin for legend
    )

    # Add a custom legend using annotations
    for i, (user, color) in enumerate(sorted(user_colors.items())):
        y_pos = legend_y_start - (i * 0.06)

        # Add colored rectangle
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=1.02,
            y0=y_pos - 0.02,
            x1=1.05,
            y1=y_pos + 0.02,
            fillcolor=color,
            line=dict(color="black", width=1),
        )

        # Add user name
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=1.06,
            y=y_pos + 0.01,
            text=user,
            showarrow=False,
            xanchor="left",
        )

    # Add legend title
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=1,
        y=legend_y_start + 0.1,
        text="User Legend",
        showarrow=False,
        xanchor="left",
        font=dict(size=16, color="black", family="Arial"),
    )

    return pn.pane.Plotly(fig, sizing_mode="stretch_both")


def get_funnel_widgets(funnel_data: pd.DataFrame):
    # Group data by contact_email to analyze the conversion journey
    conversion_stats = {}

    # Count event types and conversions for each user
    for email, group in funnel_data.groupby("contact_email"):
        conversions = group.conversion.values
        dealstages = group.dealstage.values
        verbal_agreements = group.verbal_agreement.values
        users = group.user.values

        # Track which users handled which events
        if "First call" in conversions:
            first_call_user = group.user.loc[group.conversion == "First call"].iloc[0]
            if first_call_user not in conversion_stats:
                conversion_stats[first_call_user] = {
                    "first_call_total": 0,
                    "first_call_to_sale": 0,
                    "first_call_va_total": 0,
                    "first_call_va_to_sale": 0,
                    "placement_total": 0,
                    "placement_to_sale": 0,
                    "placement_va_total": 0,
                    "placement_va_to_sale": 0,
                }
            conversion_stats[first_call_user]["first_call_total"] += 1

            # Check if first call led to sale
            if "closedwon" in dealstages:
                conversion_stats[first_call_user]["first_call_to_sale"] += 1

        if "Verbal agreement after first call" in conversions:
            va_user = group.user.loc[
                group.conversion == "Verbal agreement after first call"
            ].iloc[0]
            if va_user not in conversion_stats:
                conversion_stats[va_user] = {
                    "first_call_total": 0,
                    "first_call_to_sale": 0,
                    "first_call_va_total": 0,
                    "first_call_va_to_sale": 0,
                    "placement_total": 0,
                    "placement_to_sale": 0,
                    "placement_va_total": 0,
                    "placement_va_to_sale": 0,
                }
            conversion_stats[va_user]["first_call_va_total"] += 1

            # Check if verbal agreement led to sale
            if "closedwon" in dealstages:
                conversion_stats[va_user]["first_call_va_to_sale"] += 1

        if "Placement scheduled" in conversions:
            placement_user = group.user.loc[
                group.conversion == "Placement scheduled"
            ].iloc[0]
            if placement_user not in conversion_stats:
                conversion_stats[placement_user] = {
                    "first_call_total": 0,
                    "first_call_to_sale": 0,
                    "first_call_va_total": 0,
                    "first_call_va_to_sale": 0,
                    "placement_total": 0,
                    "placement_to_sale": 0,
                    "placement_va_total": 0,
                    "placement_va_to_sale": 0,
                }
            conversion_stats[placement_user]["placement_total"] += 1

            # Check if placement led to sale
            if "closedwon" in dealstages:
                conversion_stats[placement_user]["placement_to_sale"] += 1

            # Check if placement had verbal agreement
            if "true" in verbal_agreements:
                conversion_stats[placement_user]["placement_va_total"] += 1

                # Check if placement VA led to sale
                if "closedwon" in dealstages:
                    conversion_stats[placement_user]["placement_va_to_sale"] += 1

    # Create widgets to display conversion stats
    widgets = []

    for user, stats in conversion_stats.items():
        user_metrics = []

        # First Call → Sale
        if stats["first_call_total"] >= 10:
            rate = stats["first_call_to_sale"] / stats["first_call_total"] * 100
            user_metrics.append(
                pn.indicators.Number(
                    name=f"First Call → Sale ({stats['first_call_to_sale']}/{stats['first_call_total']})",
                    value=rate,
                    format="{value:.1f}%",
                    colors=[(0, "red"), (10, "orange"), (20, "green")],
                )
            )

        # First Call VA → Sale
        if stats["first_call_va_total"] >= 10:
            rate = stats["first_call_va_to_sale"] / stats["first_call_va_total"] * 100
            user_metrics.append(
                pn.indicators.Number(
                    name=f"First Call VA → Sale ({stats['first_call_va_to_sale']}/{stats['first_call_va_total']})",
                    value=rate,
                    format="{value:.1f}%",
                    colors=[(0, "red"), (30, "orange"), (50, "green")],
                )
            )

        # Placement → Sale
        if stats["placement_total"] >= 10:
            rate = stats["placement_to_sale"] / stats["placement_total"] * 100
            user_metrics.append(
                pn.indicators.Number(
                    name=f"Placement → Sale ({stats['placement_to_sale']}/{stats['placement_total']})",
                    value=rate,
                    format="{value:.1f}%",
                    colors=[(0, "red"), (20, "orange"), (40, "green")],
                )
            )

        # Placement VA → Sale
        if stats["placement_va_total"] >= 10:
            rate = stats["placement_va_to_sale"] / stats["placement_va_total"] * 100
            user_metrics.append(
                pn.indicators.Number(
                    name=f"Placement VA → Sale ({stats['placement_va_to_sale']}/{stats['placement_va_total']})",
                    value=rate,
                    format="{value:.1f}%",
                    colors=[(0, "red"), (40, "orange"), (60, "green")],
                )
            )

        # Only add the user card if they have metrics to show
        if user_metrics:
            widgets.append(
                pn.Card(
                    pn.Column(*user_metrics),
                    title=user,
                    collapsed=False,
                    width=300,
                )
            )

    # Return all user widgets in a responsive Row layout
    return pn.Row(*widgets, sizing_mode="stretch_width")
