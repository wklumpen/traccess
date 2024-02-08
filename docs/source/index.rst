.. traccess documentation master file, created by
   sphinx-quickstart on Thu Aug 31 16:08:44 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Traccess
========
Transportation access and equity computations.

Traccess offers a set of fast and convenient functions to calculate multiple
transport accessibility measures. Given a pre-computed travel cost matrix, and
using data sets on land use supply, demand, and demographics, the package
computes accessibility levels using multiple accessibility measures, such as:
cumulative opportunities, minimum travel cost to closest *n* number of activities,
gravity-based (with different decay functions) and different floating catchment
area methods.

The package also contains a number of different methods for computing
distributive and sufficientarian equity measures to compare the level of access
provided across demographic groups.

Installation
------------

Traccess is currently available via PyPI

.. code-block::

   pip install traccess

Computing Access to Opportunities
---------------------------------

Computing accecss to opportunities requires both a supply (land use) source
containing area-coded counts of locations, and a cost matrix which represents
the cost of travel from any zone to any other.

You can specify ID columns on load to use arbitrary values as origins and
destinations.

.. code-block:: python

   from traccess import AccessComputer, Cost, Supply

   supply = Supply.from_csv("supply.csv", id_column="id")
   cost = Cost.from_csv("costs.csv", from_id="o", to_id="d")

   ac = AccessComputer(supply, cost)

   access = ac.cost_to_closest(cost_column="c", supply_columns=["oj2"], n=2)

   print(access.data)

Computing Transport Poverty Measures
------------------------------------

.. code-block:: python

   from traccess import AccessComputer, Cost, Demographic, EquityComputer, Supply

   supply = Supply.from_csv("supply.csv", id_column="id")
   cost = Cost.from_csv("costs.csv", from_id="o", to_id="d")
   demographics = Demographic.from_csv("demographics.csv", id_column="dd")

   ac = AccessComputer(supply, cost)

   access = ac.cost_to_closest(cost_column="c", supply_columns=["oj2"], n=2)

   ec = EquityComputer(access, demographics)

   fgt_df = ec.fgt_poverty(access_column="oj", poverty_line=10.0, alpha=1)

   print(fgt_df)

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   reference

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
