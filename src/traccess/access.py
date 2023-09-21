import numpy
import pandas

from .cost import Cost
from .supply import Supply


class Access:
    def __init__(self, supply: Supply, cost: Cost, demand=None):
        self._supply = supply
        self._cost = cost
        self._demand = demand

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

    def cost_to_closest(self, cost_column: str, supply_columns: list[str], n=1):
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
                .apply(get_nth, o=c, n=n, cost=cost_column)
            )
            columns.append(result)

        if len(columns) > 1:
            final = pandas.concat(columns, axis="columns", join="outer")
        else:
            final = columns[0]

        final.columns = supply_columns

        return final

    def cumulative_cutoff(
        self, cost_columns: list[str], cutoffs: list[float], use_destination=True
    ) -> pandas.DataFrame:
        if isinstance(cost_columns, str):
            cost_columns = [cost_columns]
        if isinstance(cutoffs, float):
            cutoffs = [cutoffs]

        if len(cost_columns) != len(cutoffs):
            raise ValueError("Cost and cutoff columns must be the same length")

        if use_destination == True:
            join_column = self.cost._to_id
            group_column = self.cost._from_id
        else:
            join_column = self.cost._from_id
            group_column = self.cost._to_id

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
        df = df.reset_index().set_index(group_column)

        # Group and return
        return df[self.supply.columns].groupby(group_column).sum()


def get_nth(df, o, n, cost):
    df = df.sort_values(by=cost, ascending=True, na_position="last")
    df["_cumsum"] = df[o].cumsum()
    df = df[df["_cumsum"] >= n]
    return df[cost].min()
