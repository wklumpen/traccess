import numpy
import pandas
from typing import Callable, Union

from .data import Cost, Demand, Demographic, Supply, Access


class AccessComputer:
    """Compute access to destinations."""

    def __init__(
        self,
        supply: Supply,
        cost: Cost,
        demand: Demand = None,
    ):
        """Compute access to opportunity metrics.

        The access computer uses supplied datasets on supply, cost, and
        optionally demand to compute popular access to opportunity measures.

        Parameters
        ----------
        supply : Supply
            The supply or destination set to compute access to
        cost : Cost
            A matrix of cost values (travel time, other cost, etc)
        demand : Demand, optional
            The demand for destinations, used for competitive measures
        """
        if not isinstance(supply, Supply):
            raise TypeError(
                "The supply must be of type Supply. Check the order of arguments passed."
            )
        if not isinstance(cost, Cost):
            raise TypeError(
                "The cost must be of type Cost. Check the order of arguments passed."
            )
        self._supply = supply
        self._cost = cost
        self._demand = demand

    @property
    def cost(self) -> Cost:
        """Access or set the cost object"""
        return self._cost

    @cost.setter
    def cost(self, cost: Cost):
        self._cost = cost

    @property
    def supply(self):
        """Access or set the supply object"""
        return self._supply

    @supply.setter
    def supply(self, supply: Supply):
        self._supply = supply

    def cost_to_closest(
        self, cost_column: str, supply_columns: list[str], n=1
    ) -> Access:
        """Compute the cost to the nth closest destination.

        This function is generic over any kind of numeric travel cost, such as
        distance, time and money.

        Parameters
        ----------
        cost_column : str
            The column in the Cost object that contains the travel cost
        supply_columns : list[str]
            The columns in the Supply data to compute access to
        n : int, optional
            The nth closest to compute, by default 1

        Returns
        -------
        Access
            An Access data object with an `id_column` matching the origin zone.
        """
        # First we join the destinations
        with_dest = self.cost.data.reset_index().set_index(self.cost._to_id)
        with_dest = with_dest.join(self.supply.data, how="right")

        if isinstance(supply_columns, str):
            supply_columns = [supply_columns]

        columns = []

        for c in supply_columns:
            # Keep only columns with actual destinations
            this_column = with_dest[with_dest[c] > 0]

            result = (
                this_column[[self.cost._from_id, cost_column, c]]
                .groupby(self.cost._from_id)
                .apply(_get_nth, o=c, n=n, cost=cost_column)
            )
            columns.append(result)

        final = pandas.concat(columns, axis="columns", join="outer")

        final.columns = supply_columns

        final = final.reset_index()

        return Access(final, id_column=self.cost._from_id)

    def cumulative_cutoff(
        self,
        cost_columns: list[str],
        cutoffs: list[float],
        supply_columns: list[str] | None = None,
    ) -> Access:
        """Compute the total number of opportunities within a specified travel
        cost cutoff.

        Parameters
        ----------
        cost_columns : list[str]
            A list of cost columns to apply cutoffs to. Can be a single string
            for a single column.
        cutoffs : list[float]
            A list of cutoff values corresponding to each cost column. Can be a
            single value for a single cutoff column. Must be the same length as
            `cost_columns`.
        supply_columns : list[str]
            An optional list of supply columns to use and return. If None, all
            supply columns are used. By default, None.

        Returns
        -------
        Access
            An Access data object with an `id_column` matching the origin zone.

        Raises
        ------
        ValueError
            If the supplied column list and cutoff lists are not the same length.
        """
        if isinstance(cost_columns, str):
            cost_columns = [cost_columns]
        if isinstance(cutoffs, float) or isinstance(cutoffs, int):
            cutoffs = [cutoffs]
        if isinstance(supply_columns, str):
            supply_columns = [supply_columns]

        if len(cost_columns) != len(cutoffs):
            raise ValueError("Cost and cutoff columns must be the same length")

        join_column = self.cost._to_id
        group_column = self.cost._from_id

        # Set the join index and join
        df = self.cost.data.reset_index().set_index(join_column)

        if supply_columns is None:
            supply_columns = self.supply.columns

        df = df.join(self.supply.data[supply_columns])

        df["_weights"] = 1.0
        # Iterate through the columns and update weights based on columns
        for idx, c in enumerate(cost_columns):
            df["_weights"] = numpy.where(df[c] <= cutoffs[idx], df["_weights"], 0)

        # Multily all opportunities by the weights
        df[supply_columns] = df[supply_columns].multiply(df["_weights"], axis="index")
        # Set the group columns
        df.index.rename(join_column, inplace=True)
        df.reset_index(inplace=True)
        # Group and return
        columns = [group_column]
        columns.extend(supply_columns)
        access_df = df[columns].groupby(group_column).sum().reset_index()
        return Access(
            access_df,
            id_column=group_column,
        )

    def cumulative_decay(
        self,
        cost_columns: list[str],
        decay_functions: Callable[[float], float] | list[Callable[[float], float]],
        supply_columns: list[str] | None = None,
    ) -> Access:
        """Compute the total number of opportunities weighted by a decay function
        applied to travel cost.

        Parameters
        ----------
        cost_columns : list[str]
            A list of cost columns to apply the decay function to. Can be a
            single string for a single column.
        decay_functions : Callable or list[Callable]
            A decay function or list of decay functions to apply to each cost
            column. If a single function is provided, it is applied to all cost
            columns. If a list is provided, it must be the same length as
            ``cost_columns``. Can be any callable, including the built-in
            functions in ``traccess.decay``.
        supply_columns : list[str]
            An optional list of supply columns to use and return. If None, all
            supply columns are used. By default, None.

        Returns
        -------
        Access
            An Access data object with an `id_column` matching the origin zone.
            Result columns are named ``{supply_column}_{cost_column}`` when
            multiple cost columns are provided, or ``{supply_column}`` when
            only one cost column is provided.

        Raises
        ------
        ValueError
            If ``decay_functions`` is a list not the same length as ``cost_columns``.
        """
        if isinstance(cost_columns, str):
            cost_columns = [cost_columns]
        if callable(decay_functions):
            decay_functions = [decay_functions] * len(cost_columns)

        if len(decay_functions) != len(cost_columns):
            raise ValueError(
                f"decay_functions list length ({len(decay_functions)}) must match "
                f"cost_columns length ({len(cost_columns)})"
            )

        join_column = self.cost._to_id
        group_column = self.cost._from_id

        # Set the join index and join
        df = self.cost.data.reset_index().set_index(join_column)

        if supply_columns is None:
            supply_columns = self.supply.columns

        df = df.join(self.supply.data[supply_columns])
        df.reset_index(inplace=True)
        df.index.rename(join_column, inplace=True)

        result_df = None
        use_suffix = len(cost_columns) > 1

        for cost_col, fn in zip(cost_columns, decay_functions):
            weights = df[cost_col].apply(fn)
            weighted = df[supply_columns].multiply(weights, axis="index")

            if use_suffix:
                weighted = weighted.add_suffix(f"_{cost_col}")

            result_cols = list(weighted.columns)
            weighted[group_column] = df[group_column].values
            grouped = weighted.groupby(group_column)[result_cols].sum().reset_index()

            if result_df is None:
                result_df = grouped
            else:
                result_df = result_df.merge(grouped, on=group_column)

        return Access(result_df, id_column=group_column)


class EquityComputer:
    """Compute distributive equity across population demograhics"""

    def __init__(self, access: Access, demographic: Demographic):
        """Compute distributive equity metrics across population demographics

        An EquityComputer allows for the combination of access measures and
        demographic data to compute various metrics of distributive equity or
        transportation justice.

        Parameters
        ----------
        access : Access
            An `Access` object which contains data on access to opportunities.
        demographic : Demographic
            A `Demographic` data object which contains data on demographics and
            populations
        """
        self._access = access
        self._demographic = demographic

    @property
    def access(self) -> Access:
        return self._access

    @access.setter
    def access(self, access: Access):
        assert isinstance(access, Access)
        self._access = access

    @property
    def demographic(self) -> Demographic:
        return self._demographic

    @demographic.setter
    def demographic(self, demographic: Demographic):
        assert isinstance(demographic, Demographic)
        self._demographic = demographic

    def in_poverty(
        self, access_column: str, poverty_line: float, is_dual=False
    ) -> pandas.Series:
        """Compute the number of individuals in poverty in any given demographic.

        Parameters
        ----------
        access_column : str
            The access column to compare the poverty line to
        poverty_line : float
            The poverty line
        is_dual: bool, optional
            Whether the measure is a dual measure, where lower values are
            better, by default False

        Returns
        -------
        pandas.Series
            A series with each row consisting of a demogrphic group, containing
            the number of that group in poverty.
        """
        # Count the number of people in poverty
        df = self.access.data.join(self.demographic.data)
        if is_dual == True:
            return df[df[access_column] > poverty_line][self.demographic.columns].sum()
        else:
            return df[df[access_column] < poverty_line][self.demographic.columns].sum()

    def fgt_poverty(
        self,
        access_column: str,
        poverty_line: float,
        alpha: float,
        is_dual=False,
        population_columns: list[str] | None = None,
    ) -> pandas.Series:
        """Compute a Foster-Greer-Thorbecke (FGT) index for all demographics.

        FGT measures consider the average amount of poverty in a given
        population by comparing the distance of each individual from the poverty
        line, raised to some exponent alpha. Common values of alpha are 0, 1,
        and 2.

        When alpha = 0, the function returns the poverty rate

        When alpha = 1, the function returns the poverty gap index

        When alpha = 2, the function returns the poverty gap weighted by the
        poverty gap.

        Parameters
        ----------
        access_column : str
            The access to opportunity column to compare the measure against
        poverty_line : float
            The poverty line to compare the access measure against
        alpha : float
            The alpha parameter, or the extent which to weight those further
            below the poverty line
        is_dual: bool, optional
            Whether the measure is a dual measure, where lower values are
            better, by default False
        population_columns : list[str], optional
            The demographic columns to treat as population groups, by default
            all of them. Use this when the demographic data also holds
            non-count columns such as income.

        Returns
        -------
        pandas.Series
            A series with an index for each demographic column, containing the
            specified measure.
        """
        columns = self._population_columns(population_columns)
        df = self.access.data.join(self.demographic.data)

        # Keep the total of each population group
        n = self.demographic.data[columns].sum().rename("n")

        if is_dual == True:
            df["_delta"] = df[access_column] - poverty_line
        else:
            df["_delta"] = poverty_line - df[access_column]

        # We only do the math on the set of those in poverty
        df = df[df["_delta"] > 0]
        df["_delta"] = df["_delta"] / poverty_line
        df["_delta"] = df["_delta"].pow(alpha)
        df[columns] = df[columns].multiply(df["_delta"], axis="index")
        totals = df[columns].sum().rename("count")
        totals = pandas.concat([totals, n], axis="columns")
        totals["fgt"] = totals["count"] / totals["n"]

        return totals["fgt"].rename(f"fgt{alpha}")

    def poverty_index(
        self, access_column: str, poverty_line: float, is_dual=False
    ) -> pandas.Series:
        """Compute the poverty index at each location.

        This method computes the poverty index for each location, which is the
        difference between the poverty line and the supplied access value,
        divided by the poverty line.

        Values above the poverty line are returned as null values.

        Parameters
        ----------
        access_column : str
            The column to compare the poverty line to
        poverty_line : float
            The poverty line value for access
        is_dual: bool, optional
            Whether the measure is a dual measure, where lower values are
            better, by default False

        Returns
        -------
        pandas.Series
            A pandas Series containing the poverty index for each location
        """
        df = self.access.data.copy()
        if is_dual == True:
            df["poverty_index"] = (df[access_column] - poverty_line) / poverty_line
        else:
            df["poverty_index"] = (poverty_line - df[access_column]) / poverty_line
        df["poverty_index"] = numpy.where(
            df.poverty_index < 0, pandas.NA, df.poverty_index
        )
        return df["poverty_index"]

    def weighted_average(
        self, access_column: str, population_columns: list[str] | None = None
    ) -> pandas.Series:
        """Compute the population group-weighted average access for all groups.

        Parameters
        ----------
        access_column : str
            The access value to weight
        population_columns : list[str], optional
            The demographic columns to treat as population groups, by default
            all of them.

        Returns
        -------
        pandas.Series
            A series with a row for demographic group, with the weighted average
            access.
        """
        columns = self._population_columns(population_columns)
        df = self.access.data.join(self.demographic.data)
        # Normalize the population columns
        for c in columns:
            df[c] = df[c] / df[c].sum()
        # Multiply and sum
        df[columns] = df[columns].multiply(df[access_column], axis="index")
        df = df[columns].sum()
        df = df.rename(access_column)
        return df

    def weighted_quantile(
        self, access_column: str, quantile=0.5, is_dual=False
    ) -> pandas.Series:
        """Compute a population-weighted quantile for all demographics.

        Population-weighted quantiles are *not interpolated*, meaning that the
        values returned by this function are the highest value in the dataset
        not exceeding the quantile value.

        Parameters
        ----------
        access_column : str
            The column to compute the quantile over
        quantile : float, optional
            The quantile to use, by default 0.5
        is_dual: bool, optional
            Whether the measure is a dual measure, where lower values are
            better, by default False

        Returns
        -------
        pandas.Series
            A series containing each demographic group and the access value of
            that quantile.
        """

        if is_dual == True:
            quantile = 1.0 - quantile

        df = self.access.data.join(self.demographic.data)
        df.sort_values(access_column, inplace=True)

        result = dict()
        for c in self.demographic.columns:
            total_weight = df[c].sum()
            df["_cumulative"] = df[c].cumsum()
            result[c] = df[df["_cumulative"] <= (total_weight) * quantile][
                access_column
            ].iloc[-1]

        return pandas.Series(result, name=f"q{int(quantile * 100)}")

    # --- Inequality measures -------------------------------------------------
    #
    # Ported from IPEA's R ``accessibility`` package (gini_index, theil_t,
    # palma_ratio, concentration_index), computed once per population group:
    # each group's counts are the weights. Results are Series indexed by
    # population column, like weighted_average.

    def _population_columns(self, population_columns: list[str] | None) -> list[str]:
        if population_columns is None:
            return list(self.demographic.columns)
        missing = set(population_columns) - set(self.demographic.columns)
        if missing:
            raise ValueError(f"Not demographic columns: {sorted(missing)}")
        return list(population_columns)

    def _joined(self, access_column: str, extra_columns: list[str]) -> pandas.DataFrame:
        df = self.access.data[[access_column]].join(self.demographic.data)
        return df.dropna(subset=[access_column, *extra_columns])

    def gini_index(
        self, access_column: str, population_columns: list[str] | None = None
    ) -> pandas.Series:
        """Compute the Gini index of access for each population group.

        The Gini index is one minus twice the area under the Lorenz curve of
        population-weighted access: 0 when everyone has the same access, and
        approaching 1 when all access is concentrated in one place.

        Parameters
        ----------
        access_column : str
            The access column to measure inequality over.
        population_columns : list[str], optional
            The demographic columns to use as population weights, by default
            all of them.

        Returns
        -------
        pandas.Series
            The Gini index for each population group.
        """
        columns = self._population_columns(population_columns)
        df = self._joined(access_column, []).sort_values(access_column, kind="stable")
        access = df[access_column]

        result = {}
        for c in columns:
            weights = df[c].fillna(0)
            prop_pop = weights / weights.sum()
            total_access = (weights * access).cumsum() / (weights * access).sum()
            small_edge = total_access.shift(1, fill_value=0.0)
            area = ((small_edge + total_access) * prop_pop / 2).sum()
            result[c] = 1 - 2 * area
        return pandas.Series(result, name="gini")

    def theil_t(
        self, access_column: str, population_columns: list[str] | None = None
    ) -> pandas.Series:
        """Compute the Theil T index of access for each population group.

        Theil T is 0 when everyone has the same access and grows with
        inequality, up to ln(n). As in the R ``accessibility`` package,
        places with zero access are left out of the sum (ln 0 is undefined)
        after the population-weighted average is computed over everyone.

        Parameters
        ----------
        access_column : str
            The access column to measure inequality over.
        population_columns : list[str], optional
            The demographic columns to use as population weights, by default
            all of them.

        Returns
        -------
        pandas.Series
            The Theil T index for each population group.
        """
        columns = self._population_columns(population_columns)
        df = self._joined(access_column, [])
        result = {}
        for c in columns:
            weights = df[c].fillna(0)
            average = numpy.average(df[access_column], weights=weights)
            result[c] = _theil_t(df[access_column], average, weights)
        return pandas.Series(result, name="theil_t")

    def theil_t_decomposition(
        self,
        access_column: str,
        group_column: str,
        population_columns: list[str] | None = None,
    ) -> pandas.DataFrame:
        """Decompose the Theil T index into between- and within-group parts.

        Places are split by ``group_column`` (a category such as income
        decile, which must not itself be a population column). The total
        equals ``between_group + within_group``.

        Parameters
        ----------
        access_column : str
            The access column to measure inequality over.
        group_column : str
            The demographic column whose values define the mutually exclusive
            groups.
        population_columns : list[str], optional
            The demographic columns to use as population weights, by default
            all of them except ``group_column``.

        Returns
        -------
        pandas.DataFrame
            One row per population group, with ``between_group``,
            ``within_group`` and ``total`` columns.
        """
        if population_columns is None:
            population_columns = [
                c for c in self.demographic.columns if c != group_column
            ]
        columns = self._population_columns(population_columns)
        df = self._joined(access_column, [group_column])
        access = df[access_column]

        rows = {}
        for c in columns:
            weights = df[c].fillna(0)
            average = numpy.average(access, weights=weights)
            total_access = (weights * access).sum()
            between_parts, between_weights, within = [], [], 0.0
            for _, group in df.groupby(group_column):
                w = weights.loc[group.index]
                if w.sum() == 0:
                    continue
                group_average = numpy.average(group[access_column], weights=w)
                group_access = (w * group[access_column]).sum()
                within += _theil_t(group[access_column], group_average, w) * (
                    group_access / total_access
                )
                between_parts.append(group_average)
                between_weights.append(w.sum())
            between = _theil_t(
                pandas.Series(between_parts), average, pandas.Series(between_weights)
            )
            rows[c] = {
                "between_group": between,
                "within_group": within,
                "total": between + within,
            }
        return pandas.DataFrame.from_dict(rows, orient="index")

    def palma_ratio(
        self,
        access_column: str,
        income_column: str,
        population_columns: list[str] | None = None,
    ) -> pandas.Series:
        """Compute the Palma ratio of access for each population group.

        The average access of the wealthiest 10% divided by that of the
        poorest 40%, where "wealthiest" and "poorest" are set by
        population-weighted quantiles of ``income_column``. Values above 1
        mean the wealthy have better access.

        Parameters
        ----------
        access_column : str
            The access column to measure inequality over.
        income_column : str
            A demographic column of income per capita (not total income) for
            each place, used to rank places.
        population_columns : list[str], optional
            The demographic columns to use as population weights, by default
            all of them except ``income_column``.

        Returns
        -------
        pandas.Series
            The Palma ratio for each population group (NaN if either income
            group is empty).
        """
        columns = self._population_columns(
            population_columns
            if population_columns is not None
            else [c for c in self.demographic.columns if c != income_column]
        )
        df = self._joined(access_column, [income_column])
        income = df[income_column]

        result = {}
        for c in columns:
            weights = df[c].fillna(0)
            q40 = _weighted_quantile(income, weights, 0.4)
            q90 = _weighted_quantile(income, weights, 0.9)
            poorest = income <= q40
            wealthiest = income > q90
            if weights[poorest].sum() == 0 or weights[wealthiest].sum() == 0:
                result[c] = numpy.nan
                continue
            rich = numpy.average(df.loc[wealthiest, access_column], weights=weights[wealthiest])
            poor = numpy.average(df.loc[poorest, access_column], weights=weights[poorest])
            result[c] = rich / poor if poor != 0 else numpy.nan
        return pandas.Series(result, name="palma_ratio")

    def concentration_index(
        self,
        access_column: str,
        income_column: str,
        type: str = "standard",
        population_columns: list[str] | None = None,
    ) -> pandas.Series:
        """Compute the concentration index of access for each population group.

        Measures how much access inequality lines up with socioeconomic
        status. Ranges from -1 to 1: positive values mean access is
        concentrated among higher-income people (pro-rich), negative values
        among lower-income people.

        Parameters
        ----------
        access_column : str
            The access column to measure inequality over.
        income_column : str
            A demographic column used to rank places from least to most
            privileged: income per capita, or any numeric socioeconomic
            status measure where higher means better off.
        type : str, optional
            ``"standard"`` (the relative index) or ``"corrected"`` (Erreygers,
            2009), by default ``"standard"``.
        population_columns : list[str], optional
            The demographic columns to use as population weights, by default
            all of them except ``income_column``.

        Returns
        -------
        pandas.Series
            The concentration index for each population group.
        """
        if type not in ("standard", "corrected"):
            raise ValueError(f"type must be 'standard' or 'corrected', got {type!r}")
        columns = self._population_columns(
            population_columns
            if population_columns is not None
            else [c for c in self.demographic.columns if c != income_column]
        )
        df = self._joined(access_column, [income_column]).sort_values(
            income_column, kind="stable"
        )
        access = df[access_column]

        result = {}
        for c in columns:
            weights = df[c].fillna(0)
            pop_share = weights / weights.sum()
            # Fractional rank, eq. 4 of van Doorslaer & Koolman (2004).
            rank = pop_share.cumsum().shift(1, fill_value=0.0) + pop_share / 2
            average = numpy.average(access, weights=weights)
            contribution = (rank - 0.5) * (access - average) * pop_share / average
            index = 2 * contribution.sum()
            if type == "corrected":
                spread = access.max() - access.min()
                index = index * 4 * average / spread if spread else numpy.nan
            result[c] = index
        return pandas.Series(result, name="concentration_index")


def _get_nth(df, o, n, cost):
    df = df.sort_values(by=cost, ascending=True, na_position="last")
    df["_cumsum"] = df[o].cumsum()
    df = df[df["_cumsum"] >= n]
    return df[cost].min()


def _theil_t(values: pandas.Series, average: float, weights: pandas.Series) -> float:
    """Weighted mean of (x / avg) ln(x / avg) over positive values, as in the
    R accessibility package's calc_theil_t (zero values are dropped)."""
    values = pandas.Series(values).reset_index(drop=True)
    weights = pandas.Series(weights).reset_index(drop=True)
    positive = values > 0
    if not positive.any() or weights[positive].sum() == 0:
        return float("nan")
    ratio = values[positive] / average
    return float(numpy.average(ratio * numpy.log(ratio), weights=weights[positive]))


def _weighted_quantile(values: pandas.Series, weights: pandas.Series, q: float) -> float:
    """Population-weighted quantile: the smallest value whose cumulative
    weight share reaches q."""
    order = numpy.argsort(values.to_numpy(), kind="stable")
    sorted_values = values.to_numpy()[order]
    cumulative = numpy.cumsum(weights.to_numpy()[order])
    if cumulative[-1] == 0:
        return float("nan")
    index = numpy.searchsorted(cumulative / cumulative[-1], q, side="left")
    return float(sorted_values[min(index, len(sorted_values) - 1)])
