# Traccess
Transportation access and equity computations.

Traccess offers a set of fast and convenient functions to calculate multiple
transport accessibility measures. Given a pre-computed travel cost matrix, and
using data sets on land use supply, demand, and demographics, the package
computes accessibility levels using multiple accessibility measures, such as:
cumulative opportunities, minimum travel cost to closest *n* number of activities,
gravity-based (with different decay functions) and different floating catchment
area methods.

The package also contains a number of different methods for computing
distributive and sufficientarian equity measures to compare the level of access
provided across demographic groups.

## Decay functions

`traccess.decay` provides weighting functions for
`AccessComputer.cumulative_decay`, mirroring IPEA's R
[`accessibility`](https://github.com/ipeaGIT/accessibility) package:
`binary`, `exponential`, `linear`, `logistic`, `power` and `stepped`. A missing
(NaN) travel cost always gets weight 0.

## Equity and inequality measures

`EquityComputer` computes, once per demographic group:

- Sufficientarian measures: `fgt_poverty`, `in_poverty`, `poverty_index`
- Distributive summaries: `weighted_average`, `weighted_quantile`
- Inequality indices (ported from R `accessibility`): `gini_index`, `theil_t`,
  `theil_t_decomposition` (between/within a categorical grouping),
  `palma_ratio` and `concentration_index` (both ranked by an income-per-capita
  or other socioeconomic column)

Pass `population_columns` to choose which demographic columns are population
counts, e.g. when the demographic data also holds an income column.
