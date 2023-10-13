from traccess import Supply, Cost, AccessComputer, Demographic, EquityComputer

supply = Supply.from_csv("docs/source/_static/data/test_data_1_supply.csv", id_column="dd")
cost = Cost.from_csv("docs/source/_static/data/test_data_1_costs.csv", from_id="o", to_id="d")
demographics = Demographic.from_csv("docs/source/_static/data/test_data_1_demographics.csv", id_column="dd")

ac = AccessComputer(supply, cost)

access = ac.cost_to_closest(cost_column="c", supply_columns=["oj2"], n=2)

print(access.data)

# ec = EquityComputer(access, demographics)

# # print(ec.fgt(access_column="oj", poverty_line=10.0, alpha=1))

# wa = ec.weighted_average(access_column="oj")

# print(wa.loc["li"] / wa.loc["total"])
