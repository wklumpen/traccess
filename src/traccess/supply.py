import pandas


class Supply:
    def __init__(self, dataframe: pandas.DataFrame, id_column="id"):
        self._data = dataframe
        self._data.set_index(id_column, inplace=True)

        self._id = id_column

    @property
    def columns(self):
        return self._data.columns

    @property
    def data(self) -> pandas.DataFrame:
        return self._data

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

    def generalized_cost(self):
        raise NotImplementedError

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
            self._data[c] = (self._data[c] - self._data[c].min()) / (self._data[c].max() - self._data[c].min()) * (
                max - min
            ) + min

    def intrazonal(self):
        raise NotImplementedError