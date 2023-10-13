import pathlib
import pandas
import pytest

from traccess import Supply, Cost, AccessComputer

DATA_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent / "docs" / "source" / "_static" / "data"

COSTS_CSV = DATA_DIRECTORY / "test_data_1_costs.csv"
COSTS_FROM_ID_COLUMN = "o"
COSTS_TO_ID_COLUMN = "d"

SUPPLY_CSV = DATA_DIRECTORY / "test_data_1_supply.csv"
SUPPLY_ID_COLUMN = "dd"


@pytest.fixture
def cost_csv_filepath():
    yield COSTS_CSV


@pytest.fixture
def supply_dataframe():
    df = pandas.DataFrame({"zone": [1, 2, 3, 4, 5], "employment": [200, 100, 300, 400, 250]})
    yield df


@pytest.fixture
def supply_csv_filepath():
    yield SUPPLY_CSV


@pytest.fixture
def access_object():
    supply = Supply.from_csv(SUPPLY_CSV, SUPPLY_ID_COLUMN)
    cost = Cost.from_csv(COSTS_CSV, COSTS_FROM_ID_COLUMN, COSTS_TO_ID_COLUMN)
    access = AccessComputer(supply, cost)
    yield access
