import os
import datetime
import pandas as pd
import pickle
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from statsmodels.stats.proportion import proportion_confint

analytics_datasets = [
    d for d in os.listdir("data") if d.startswith("first_call_analytics")
]
path = os.path.join(
    "data",
    max(
        analytics_datasets,
        key=lambda x: datetime.datetime.strptime(x.split("_")[-1][:-4], "%Y-%m-%d"),
    ),
)

df = pd.read_pickle(path)

# --- Analysis Functions ---


def calculate_conversion_rates_with_ci(
    df, group_col, target_col="sale", alpha=0.05, fillna_value="Unknown"
):
    """
    Calculates conversion rates and Wilson confidence intervals for a target variable,
    grouped by a specified column. Handles missing values in the grouping column.
    """
    # Fill NaN in the grouping column to treat it as a separate category
    df_filled = df.copy()
    if df_filled[group_col].isnull().any():
        # Ensure the fillna_value fits the dtype (especially for categorical)
        if pd.api.types.is_categorical_dtype(df_filled[group_col]):
            if fillna_value not in df_filled[group_col].cat.categories:
                df_filled[group_col] = df_filled[group_col].cat.add_categories(
                    [fillna_value]
                )
        df_filled[group_col] = df_filled[group_col].fillna(fillna_value)

    grouped = df_filled.groupby(group_col)[target_col].agg(["count", "sum"])
    grouped.rename(columns={"count": "exposures", "sum": "conversions"}, inplace=True)
    grouped["conversion_rate"] = grouped["conversions"] / grouped["exposures"]

    # Calculate Wilson confidence intervals
    conf_int = proportion_confint(
        grouped["conversions"], grouped["exposures"], alpha=alpha, method="wilson"
    )
    grouped["ci_lower"] = conf_int[0]
    grouped["ci_upper"] = conf_int[1]
    grouped["ci_error"] = (grouped["ci_upper"] - grouped["ci_lower"]) / 2

    return grouped.reset_index()


def plot_conversion_rates(results_df, group_col, target_col="sale", title_suffix=""):
    """Plots conversion rates with confidence intervals."""
    results_df_sorted = results_df.sort_values("conversion_rate", ascending=False)

    plt.figure(figsize=(12, 6))
    plt.errorbar(
        results_df_sorted[group_col].astype(
            str
        ),  # Ensure x-axis treats labels as strings
        results_df_sorted["conversion_rate"],
        yerr=results_df_sorted["ci_error"],
        fmt="o",  # Plot points
        capsize=5,  # Error bar caps
        linestyle="None",  # Do not connect points
        label="Conversion Rate ± 95% CI",
    )

    # Add overall conversion rate line
    overall_rate = df[target_col].sum() / df[target_col].count()
    plt.axhline(
        overall_rate,
        color="r",
        linestyle="--",
        label=f"Overall Rate ({overall_rate:.2%})",
    )

    plt.title(f"Conversion Rate ({target_col}) by {group_col}{title_suffix}")
    plt.xlabel(group_col)
    plt.ylabel("Conversion Rate")
    plt.xticks(rotation=45, ha="right")
    plt.ylim(
        0, max(results_df_sorted["ci_upper"].max() * 1.1, 0.1)
    )  # Ensure y-axis starts at 0 and gives some space
    plt.gca().yaxis.set_major_formatter(
        plt.FuncFormatter(lambda y, _: "{:.1%}".format(y))
    )  # Format y-axis as percentage
    plt.legend()
    plt.tight_layout()
    plt.show()


# --- Question 1: Variable Influence ---

print("--- Analyzing Variable Influence on Conversion Rate ---")

# 1a. Analyze categorical variables
categorical_vars = ["source", "campaign", "fit"]
for var in categorical_vars:
    print(f"\nAnalyzing: {var}")
    results = calculate_conversion_rates_with_ci(df, var)
    print(results)
    plot_conversion_rates(results, var)

# 1b. Analyze about_me_wc (binned)
print("\nAnalyzing: about_me_wc (binned)")
# Define bins and labels
bins = [-1, 2, 9, 24, 49, np.inf]  # Bins: 0-2, 3-9, 10-24, 25-49, >=50
labels = ["0-2 words", "3-9 words", "10-24 words", "25-49 words", "50+ words"]

# Handle potential NaNs in about_me_wc before binning (treat as 0 words)
df_copy = df.copy()
df_copy["about_me_wc"].fillna(0, inplace=True)

# Create the binned category
df_copy["about_me_wc_binned"] = pd.cut(
    df_copy["about_me_wc"], bins=bins, labels=labels, right=True
)

# Analyze the binned variable
results_wc = calculate_conversion_rates_with_ci(df_copy, "about_me_wc_binned")
print(results_wc)
plot_conversion_rates(results_wc, "about_me_wc_binned", title_suffix=" (Binned)")

print("\n--- Analysis Complete ---")
