import traccess


class TestSupply:
    def test_load_from_csv(self, supply_csv_filepath):
        supply = traccess.Supply.from_csv(supply_csv_filepath, id_column="dd")
        assert supply.columns[0] == "oj"
        assert supply.data.loc[2]["oj2"] == 1
