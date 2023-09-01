from pandas import DataFrame

"""What do I need to know here
    - 
"""

class Supply(DataFrame):

    def __init__(self, data=None, *args, id_column="id", **kwargs):
        super().__init__(data, *args, **kwargs)


    def generalized_cost(self):
        raise NotImplementedError
    
    
    def intrazonal(self):
        raise NotImplementedError
    
