import traccess


class TestSupply:
    def test_load_from_csv(self, supply_csv_filepath):
        supply = traccess.Supply.from_csv(supply_csv_filepath, id_column="dd")
        assert supply.columns[0] == "oj"
        assert supply.data.loc[2]["oj2"] == 1

    def test_load_from_parquet(self, supply_dataframe, tmp_path):
        parquet_path = tmp_path / "supply.parquet"
        supply_dataframe.to_parquet(parquet_path)

        supply = traccess.Supply.from_parquet(parquet_path, id_column="zone")

        assert supply.columns[0] == "employment"
        assert supply.data.loc[3]["employment"] == 300
