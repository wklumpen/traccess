import traccess


class TestCost:
    def test_load_from_csv(self, cost_csv_filepath):
        cost = traccess.Cost.from_csv(cost_csv_filepath, "o", "d")
        assert cost.data.loc[(1, 3), "c"] == 20
