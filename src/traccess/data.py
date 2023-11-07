from abc import ABC, abstractmethod

import pandas


class AbstractDataSet(ABC):
    def __init__(self, dataframe: pandas.DataFrame, id_column="id"):
        self._data = dataframe
        self._data.set_index(id_column, inplace=True)

        self._id = id_column

    @property
    def columns(self):
        return [i for i in self._data.columns]

    @property
    def data(self) -> pandas.DataFrame:
        return self._data

    @data.setter
    def data(self, data: pandas.DataFrame):
        self._data = data

    def normalize(self, columns=None, min=0.0, max=1.0):
        """Normalize one or more columns between a range

        This method scales a column based on its minimum
        and maximum values.

        Parameters
        ----------
        columns : list, optional
            The list of columns to normalise. If None, all columns are used, by default None
        min : float, optional
            The minimum of the scaled range, by default 0
        max : float, optional
            The maximum of the scaled range, by default 1
        """
        if columns == None:
            columns = self._data.columns

        for c in columns:
            self._data[c] = (self._data[c] - self._data[c].min()) / (
                self._data[c].max() - self._data[c].min()
            ) * (max - min) + min

    @classmethod
    def from_csv(cls, csv_filepath, id_column="id", **kwargs):
        """Create a Supply object from a csv file

        Parameters
        ----------
        csv_filepath : str or path
            The filepath of the CSV to parse
        id_column : str, optional
            The column used as the reference id, by default "id"

        Returns
        -------
        Supply
            A supply object containing opportunities or land use data
        """
        dataframe = pandas.read_csv(csv_filepath, **kwargs)
        return cls(dataframe, id_column)


class AbstractMatrix(ABC):
    def __init__(
        self, dataframe: pandas.DataFrame, from_id="from_id", to_id="to_id"
    ) -> None:
        self._data = dataframe
        self._data.set_index([from_id, to_id], inplace=True)

        self._from_id = from_id
        self._to_id = to_id

    @property
    def columns(self):
        return self._data.columns

    @property
    def data(self):
        return self._data

    @classmethod
    def from_csv(cls, csv_filepath, from_id="i", to_id="j", **kwargs):
        dataframe = pandas.read_csv(csv_filepath, **kwargs)
        return cls(dataframe, from_id, to_id)

    @classmethod
    def from_parquet(cls, parquet_filepath, from_id="i", to_id="j", **kwargs):
        dataframe = pandas.read_parquet(parquet_filepath, **kwargs)
        return cls(dataframe, from_id, to_id)


class Access(AbstractDataSet):
    pass


class Cost(AbstractMatrix):
    def quantile(self, quantile: float, use_to_id=False) -> pandas.DataFrame:
        """Compute the quantile cost values across all origins or destinations

        Parameters
        ----------
        quantile : float
            The quantile to compute (0 to 1)
        use_to_id : bool, optional
            If true, group by the destination column instead of the origin, by default False

        Returns
        -------
        pandas.DataFrame
            A dataframe with an index for each id and the quantile value
        """
        if use_to_id:
            return self.data.groupby(self._to_id).quantile(quantile)
        else:
            return self.data.groupby(self._from_id).quantile(quantile)

    def median(self, use_to_id=False) -> pandas.DataFrame:
        """Compute the median cost values across all origins or destinations.

        This function is a shorthand for `Cost.quantile(quantile=0.5)`

        Parameters
        ----------
        use_to_id : bool, optional
            If true, group by the destination column instead of the origin, by default False

        Returns
        -------
        pandas.DataFrame
            A dataframe with an index for each id and a median value
        """
        return self.quantile(0.5, use_to_id)


class Demand(AbstractDataSet):
    pass


class Supply(AbstractDataSet):
    def generalized_cost(self):
        raise NotImplementedError

    def intrazonal(self):
        raise NotImplementedError


class Demographic(AbstractDataSet):
    def something(self):
        raise NotImplementedError
