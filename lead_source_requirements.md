# **Project Requirements Document: The Urlist Website**

The following table outlines the detailed functional requirements of the lead source analysis dashboard.

Definitions:

- Lead source: A source of leads for the business. This can be any information from a utm parameter. Lead sources can be broken down from a high level (e.g. organic, paid, referral) to a intermediate level (e.g. google, facebook, instagram) to a low level (e.g. campaign, ad group, keyword).

| Requirement ID | Description               | User Story                                                                                       | Expected Behavior/Outcome                                                                                                     |
|-----------------|---------------------------|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| FR001          | Cost per Lead   | As a user, I want to be able to see the cost per lead for each lead source so I can understand how much each lead source is costing me.              | The system should provide a clear and intuitive way for the user to view the cost per lead for each lead source using a bar chart. |
| FR002          | Number of Leads   | As a user, I want to be able to see the number of leads for each lead source so I can understand how many leads each lead source is generating.              | The system should provide a clear and intuitive way for the user to view the number of leads for each lead source using a bar chart. |
| FR003          | Break down by lead source   | As a user, I want to be able to see the cost per lead for each lead source by month so I can understand how my lead sources are performing over time.              | The system should provide a clear and intuitive way for the user to view the cost per lead for each lead source by month using a line chart. |
| FR004          | Single plot   | As a user, I want to be able to see all the data and metrics on a single plot so I can compare them visually.              | The system should combine metrics (cost per lead, number of leads, etc.) into a single plot so the user can see them together. |
| FR005          | Date filter   | As a user, I want to be able to filter the data by date so I can see the data for a specific time period.              | The system should provide a clear and intuitive way for the user to filter the data by date using a date picker. |
| FR006          | Lead source filter   | As a user, I want to be able to filter the data by lead source so I can see the data for a specific lead source.              | The system should provide a clear and intuitive way for the user to filter the data by lead source using a dropdown menu. |
| FR007          | Date comparison   | As a user, I want to be able to compare the data for different time periods so I can see how my lead sources are performing in different time periods.              | The system should provide a clear and intuitive way for the user to compare the data for different time periods using a dropdown menu. |
| FR008          | Target conversions   | As a user, I want to be able to select a conversion from a list of conversions in the funnel so I can see how my lead sources are performing in different steps of the funnel.              | The system should provide a clear and intuitive way for the user to select a conversion from a list of conversions in the funnel using a dropdown menu. The list of conversions should contain Landing Page visit, First Call, and Sale. The amount of conversions will be the base for the metric calculations(cost per lead, number of leads, etc.) |


