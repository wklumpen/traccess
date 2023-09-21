from traccess import Supply, Cost, Access

supply = Supply.from_csv("docs/source/_static/data/test_data_1_supply.csv", id_column="dd")
cost = Cost.from_csv("docs/source/_static/data/test_data_1_costs.csv", from_id="o", to_id="d")

access = Access(supply, cost)

df = access.cost_to_closest(cost_column="c", supply_columns=["oj", "oj2"], n=1)


print(df)
