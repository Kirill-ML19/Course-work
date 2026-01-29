import pandas as pd

def loader(path:str)->pd.DataFrame:
    '''
    This function loads a dataset

    Parametrs:
        path (str): the path where the CSV file is located
    Return:
        pd.DataFrame - dataset
    '''
    DataFrame = pd.read_csv(path)
    return DataFrame