import pytest
import pandas as pd

@pytest.fixture
def supply_dataframe():
    df = pd.DataFrame({
        "zone": [1, 2, 3, 4, 5],
        "employment": [200, 100, 300, 400, 250]
    })
    yield df