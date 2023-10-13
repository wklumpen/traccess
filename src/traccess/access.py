import numpy
import pandas
from typing import Union

from .data import Cost, Demand, Demographic, Supply, Access


class AccessComputer:
    def __init__(
        self,
        supply: Supply,
        cost: Cost,
        demand: Demand = None,
        demographic: Demographic = None,
    ):
        self._supply = supply
        self._cost = cost
        self._demand = demand
        self._demographic = demographic

    @property
    def cost(self) -> Cost:
        return self._cost

    @cost.setter
    def cost(self, cost: Cost):
        self._cost = cost

    @property
    def supply(self):
        return self._supply

    @supply.setter
    def supply(self, supply: Supply):
        self._supply = supply

    def cost_to_closest(self, cost_column: str, supply_columns: list[str], n=1) -> pandas.DataFrame:
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
        pandas.DataFrame
            A dataframe containing travel times to the nth closest destination
            for each origin
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

    def cumulative_cutoff(self, cost_columns: list[str], cutoffs: list[float]) -> Access:
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
        if isinstance(cutoffs, float):
            cutoffs = [cutoffs]

        if len(cost_columns) != len(cutoffs):
            raise ValueError("Cost and cutoff columns must be the same length")

        join_column = self.cost._to_id
        group_column = self.cost._from_id

        # Set the join index and join
        df = self.cost.data.reset_index().set_index(join_column)
        df = df.join(self.supply.data)

        df["_weights"] = 1.0
        # Iterate through the columns and update weights based on columns
        for idx, c in enumerate(cost_columns):
            df["_weights"] = numpy.where(df[c] <= cutoffs[idx], df["_weights"], 0)

        # Multily all opportunities by the weights
        df[self.supply.columns] = df[self.supply.columns].multiply(df["_weights"], axis="index")
        # Set the group columns
        df.index.rename(join_column, inplace=True)
        df.reset_index(inplace=True)

        # Group and return
        columns = [group_column]
        columns.extend(self.supply.columns)
        access_df = df[columns].groupby(group_column).sum().reset_index()
        return Access(
            access_df,
            id_column=group_column,
        )


class EquityComputer:
    def __init__(self, access: Access, demographic: Demographic):
        self._access = access
        self._demographic = demographic

    @property
    def access(self) -> Access:
        return self._access

    @access.setter
    def access(self, access: Access):
        self._access = access

    @property
    def demographic(self) -> Demographic:
        return self._demographic

    def in_poverty(self, access_column: str, poverty_line: float) -> pandas.Series:
        """Compute the number of individuals in poverty in any given demographic.

        Parameters
        ----------
        access_column : str
            The access column to compare the poverty line to
        poverty_line : float
            The poverty line

        Returns
        -------
        pandas.Series
            A series with each row consisting of a demogrphic group, containing
            the number of that group in poverty.
        """
        # Count the number of people in poverty
        df = self.access.data.join(self.demographic.data)
        return df[df[access_column] < poverty_line][self.demographic.columns].sum()

    def fgt(self, access_column: str, poverty_line: float, alpha: float) -> pandas.Series:
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

        Returns
        -------
        pandas.Series
            A series with an index for each demographic column, containing the
            specified measure.
        """
        df = self.access.data.join(self.demographic.data)

        # Keep the total of each population group
        n = self.demographic.data.sum().rename("n")

        df["_delta"] = poverty_line - df[access_column]
        # We only do the math the set of those in poverty
        df = df[df["_delta"] > 0]
        df["_delta"] = df["_delta"] / poverty_line
        df["_delta"] = df["_delta"].pow(alpha)
        df[self.demographic.columns] = df[self.demographic.columns].multiply(df["_delta"], axis="index")
        totals = df[self.demographic.columns].sum().rename("count")
        totals = pandas.concat([totals, n], axis="columns")
        totals["fgt"] = totals["count"] / totals["n"]
        return totals["fgt"]

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
        df[self.demographic.columns] = df[self.demographic.columns].multiply(df[access_column], axis="index")
        return df[self.demographic.columns].sum()


def _get_nth(df, o, n, cost):
    df = df.sort_values(by=cost, ascending=True, na_position="last")
    df["_cumsum"] = df[o].cumsum()
    df = df[df["_cumsum"] >= n]
    return df[cost].min()
