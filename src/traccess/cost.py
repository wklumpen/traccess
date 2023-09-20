import pandas


class Cost:
    def __init__(self, dataframe: pandas.DataFrame, from_id="i", to_id="j") -> None:
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
