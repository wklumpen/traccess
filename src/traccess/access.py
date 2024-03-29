import numpy
import pandas
from typing import Union

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
        supply_columns: list[str] = None,
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

    def cumulative_decay(self, cost_columns: list[str], decay_function) -> Access:
        pass


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
            df[df[access_column] > poverty_line][self.demographic.columns].sum()
        else:
            return df[df[access_column] < poverty_line][self.demographic.columns].sum()

    def fgt_poverty(
        self, access_column: str, poverty_line: float, alpha: float, is_dual=False
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

        Returns
        -------
        pandas.Series
            A series with an index for each demographic column, containing the
            specified measure.
        """
        df = self.access.data.join(self.demographic.data)

        # Keep the total of each population group
        n = self.demographic.data.sum().rename("n")

        if is_dual == True:
            df["_delta"] = df[access_column] - poverty_line
        else:
            df["_delta"] = poverty_line - df[access_column]

        # We only do the math on the set of those in poverty
        df = df[df["_delta"] > 0]
        df["_delta"] = df["_delta"] / poverty_line
        df["_delta"] = df["_delta"].pow(alpha)
        df[self.demographic.columns] = df[self.demographic.columns].multiply(
            df["_delta"], axis="index"
        )
        totals = df[self.demographic.columns].sum().rename("count")
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

    def weighted_average(self, access_column: str) -> pandas.Series:
        """Compute the population group-weighted average access for all groups.

        Parameters
        ----------
        access_column : str
            The access value to weight

        Returns
        -------
        pandas.Series
            A series with a row for demographic group, with the weighted average
            access.
        """
        df = self.access.data.join(self.demographic.data)
        # Normalize the population columns
        for c in self.demographic.columns:
            df[c] = df[c] / df[c].sum()
        # Multiply and sum
        df[self.demographic.columns] = df[self.demographic.columns].multiply(
            df[access_column], axis="index"
        )
        df = df[self.demographic.columns].sum()
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


def _get_nth(df, o, n, cost):
    df = df.sort_values(by=cost, ascending=True, na_position="last")
    df["_cumsum"] = df[o].cumsum()
    df = df[df["_cumsum"] >= n]
    return df[cost].min()
