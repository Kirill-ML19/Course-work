import pandas as pd
from functools import lru_cache

class Loader:

    '''
    A loader that loads the target dataframe.
    '''

    def __init__(self, path:str)->None:
        self._path = path

    @property
    def path(self)->str:
        '''
        This is a getter method that returns the path to the dataset.
        '''
        return self._path
    
    @path.setter
    def path(self, new_path:str)->None:
        '''
        This is a setter method that sets a new path to the dataset.
        '''
        self._path = new_path
        self._loader.cache_clear()

    @property
    def df(self):
        '''
        This is a public method that returns the result of the _loader function.
        '''
        return self._loader()

    @lru_cache(maxsize=1)
    def _loader(self)->pd.DataFrame:
        '''
        This function loads a dataset

        Return:
            pd.DataFrame - dataset
        
        Raises:
            RuntimeError
                If the path specified is incorrect.
        '''
        try:
            return pd.read_csv(self._path)
        except Exception as e:
            raise RuntimeError(f'Failed to load: {e}')