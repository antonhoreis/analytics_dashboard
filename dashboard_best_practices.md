To create a dashboard that is easy to understand and use, follow these best practices:

# Dependencies

- [Panel](https://panel.holoviz.org/)
- [HoloViews](https://holoviews.org/)
- [Pandas](https://pandas.pydata.org/)
- [Plotly](https://plotly.com/)

## Dependencies Best practices

- Use panel for the dashboard
- if possible, use holoviews for the plots if not suitable, use plotly
- Use pandas for data manipulation

## Fetching data

Different data sources are connected through api-clients in the data_sources folder. However, if possible, the data should be fetched through the fetch_api.py file.

The fetch_api.py file provides a single interface to fetch all data sources. It also caches the data to disk to avoid redundant fetches.

A convenient way to fetch the data is to use the get_daily_data function of the fetch_api.py file. This function fetches all data sources and combines them into a single dataframe with a datetime index. The daily data can be used as starting point for data visualization. To avoid re-fetching of data, the daily data should be resampled to the desired time granularity.

An example of the daily data is shown below:

```python
import fetch_api
data = fetch_api.get_daily_data()
data[['campaign', 'source', 'medium', 'content', 'term', 'first_call', 'sales', 'landing_page']].tail(10)
```
| date                | campaign                       | source         | medium            | content                                              | term                                                                 | first_call   | sales   | landing_page   |
|:--------------------|:-------------------------------|:---------------|:------------------|:-----------------------------------------------------|:---------------------------------------------------------------------|:-------------|:--------|:---------------|
| 2025-04-08 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Animated Video2 - New LP | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - New LP    | <NA>         | <NA>    | Hubspot2       |
| 2025-04-08 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Rebecca2 (New LP)        | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - Mixed LPs | <NA>         | <NA>    | Hubspot2       |
| 2025-03-08 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Review 2 - New LP        | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - New LP    | <NA>         | <NA>    | Hubspot2       |
| 2025-03-17 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Review 2 - New LP        | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - New LP    | <NA>         | <NA>    | Hubspot2       |
| 2025-03-20 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Review 2 - New LP        | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - New LP    | <NA>         | <NA>    | Hubspot2       |
| 2025-03-24 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Review 2 - New LP        | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - New LP    | <NA>         | <NA>    | Hubspot2       |
| 2025-03-26 00:00:00 | HM - TOF - ANGLE TESTING - ABO | ig             | Instagram_Stories | [T] TOF - AT - New Copies - Review 2 - New LP        | [T] HM - TOF - AT - Value-Based Purchase LLA - AUTO & DC - New LP    | <NA>         | <NA>    | Hubspot2       |
| 2025-03-18 00:00:00 | (referral)                     | m.facebook.com | referral          | (not set)                                            | (not set)                                                            | <NA>         | <NA>    | Hubspot2       |
| 2025-04-06 00:00:00 | (referral)                     | m.facebook.com | referral          | (not set)                                            | (not set)                                                            | <NA>         | <NA>    | Hubspot2       |
| 2025-04-18 00:00:00 | (referral)                     | m.facebook.com | referral          | (not set)                                            | (not set)                                                            | <NA>         | <NA>    | Hubspot2       |



## Dashboard structure

The dashboard is structured in the following way:

- Sidebar: Contains filters for the dashboard
- Main area: Contains the plots and tables for the dashboard