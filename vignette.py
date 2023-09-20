from traccess import Supply, Cost, Access

supply = Supply.from_csv("docs/source/_static/data/test_data_1_supply.csv", id_column="dd")
cost = Cost.from_csv("docs/source/_static/data/test_data_1_costs.csv", from_id="o", to_id="d")

access = Access(supply, cost)

print(access.cumulative_cutoff(access.cost.columns, [29, 2]))
