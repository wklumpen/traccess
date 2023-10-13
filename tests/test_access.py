import traccess


class TestAccessComputer:
    def test_cumulative_cutoff(self, access_object: traccess.AccessComputer):
        df = access_object.cumulative_cutoff(access_object.cost.columns, [29, 2]).data
        assert df.loc[1]["oj"] == 16.0

    def test_cost_to_closest(self, access_object: traccess.AccessComputer):
        df = access_object.cost_to_closest("c", ["oj2"], n=2).data
        assert df.loc[3]["oj2"] == 20.0
