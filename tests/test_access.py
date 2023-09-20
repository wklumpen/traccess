import traccess


class TestAccess:
    def test_cumulative_cutoff(self, access_object: traccess.Access):
        df = access_object.cumulative_cutoff(access_object.cost.columns, [29, 2])
        assert df.loc[1]["oj"] == 16.0
