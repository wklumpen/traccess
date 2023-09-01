import traccess

class TestSupply:
    
    def test_supply_initialization(self, supply_dataframe):
        supply = traccess.Supply(supply_dataframe)
        assert supply.columns[0] == "zone"
        assert supply.columns[1] == "employment"