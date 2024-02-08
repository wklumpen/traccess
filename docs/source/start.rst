Getting Started
===============
In this section we describe the basic structure of `traccess` and how you can
use it to quickly compute access and equity metrics.

There are two main types of objects in Traccess: data objects and computer
objects. Data objects hold specific types of information and data, such as the
:py:class:`~traccess.data.Demographic` object which holds information on various
populations. Computer objects use these data sets to compute metrics of access
(:py:class:`~traccess.access.AccessComputer`) and equity
(:py:class:`~traccess.access.EquityComputer`).


Computing Access
----------------
To compute access, you will at minimum need to define a
:py:class:`~traccess.data.Supply` dataset and a :py:class:`~traccess.data.Cost`
matrix. If you want a very simple example of how those look, you can download a
small :download:`example supply file <_static/data/test_data_1_supply.csv>` and
:download:`example cost file <_static/data/test_data_1_costs.csv>`.

Loading from CSV
****************

Here's a minimum working example, where we load in two CSV files, specify the
columns which indicate origin and destination zones, and create an
:py:class:`~traccess.access.AccessComputer` object. We are now ready to compute
access to opportunities.

.. code-block:: python

   from traccess import AccessComputer, Cost, Supply

   supply = Supply.from_csv("supply.csv", id_column="id")
   cost = Cost.from_csv("costs.csv", from_id="o", to_id="d")

   ac = AccessComputer(supply, cost)

.. note::

    When you load from a CSV or Parquet file, you can pass along any arguments
    that you might normally send to `Pandas.read_csv()` or
    `Pandas.read_parquet()`. This is especially useful when you want to specify
    `dtypes` for your ID columns.

.. note::
    The dataframe associated with each object is stored in `<object>.data`. So for
    example, `supply.data` returns the dataframe containing supply information.

Passing DataFrames Directly
***************************

If you already have a pandas `DataFrame` object you can pass it directly to the
constructor:

.. code-block:: python

   supply = Supply(dataframe, id_column="origin_id")

Compute Accecss Metrics
***********************
Now that you have the appropriate data loaded and computer object set, you can
compute any number of access metrics:

.. code-block:: python

   second_closest = ac.cost_to_closest(cost_column="c", supply_columns=["oj2"], n=2)
   cutoff45 = ac.cumulative_cutoff(cost_column=["c"], cutoffs=[45])

Each of these produces an :py:class:`~traccess.access.Access` object which can
be fed into an :py:class:`~traccess.access.EquityComputer` for further analysis,
or the data can be accessed directly using `<Access>.data`.

