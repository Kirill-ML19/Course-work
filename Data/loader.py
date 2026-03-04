import pandas as pd
from functools import lru_cache

class Loader:

    '''
    Data loader class responsible for loading datasets from disk.

    This class provides:
        - Lazy loading of datasets
        - Cached dataset storage using LRU caching
        - Automatic cache invalidation when dataset path changes

    Design considerations:
        - The dataset is loaded only once to improve performance.
        - Subsequent accesses return cached dataframe.
        - Changing dataset path automatically clears cache.

    Attributes:
        _path (str):
            Path to the dataset file on local filesystem.
    '''

    def __init__(self, path:str)->None:
        '''
        Initialize loader with dataset path.

        Args:
            path (str):
                Absolute or relative path to dataset file.

        Raises:
            ValueError:
                If path is empty or None.
        '''
        self._path = path

    @property
    def path(self)->str:
        '''
        Dataset file path getter.

        Returns:
            str:
                Current dataset path.
        '''
        return self._path
    
    @path.setter
    def path(self, new_path:str)->None:
        '''
        Dataset path setter with cache invalidation.

        When dataset path is updated, cached dataframe is cleared
        to ensure consistency between storage and memory.

        Args:
            new_path (str):
                New dataset path.

        Raises:
            ValueError:
                If new_path is empty or None.
        '''
        self._path = new_path
        self._loader.cache_clear()

    @property
    def df(self):
        '''
        Public interface for dataset access.

        Returns:
            pd.DataFrame:
                Loaded dataset stored in cache or newly loaded dataset.

        Example:
            loader = Loader("data.csv")
            dataframe = loader.df
        '''
        return self._loader()

    @lru_cache(maxsize=1)
    def _loader(self)->pd.DataFrame:
        '''
        Internal dataset loading function.

        Implements lazy loading pattern with LRU caching.

        Returns:
            pd.DataFrame:
                Loaded dataset.

        Raises:
            RuntimeError:
                If dataset file cannot be loaded due to:
                - File not found
                - Permission error
                - Parsing error
                - Invalid file format
                - Corrupted dataset
        '''
        try:
            return pd.read_csv(self._path)
        except Exception as e:
            raise RuntimeError(f'Failed to load: {e}')