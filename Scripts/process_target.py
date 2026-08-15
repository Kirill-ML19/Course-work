import os 
import pandas as pd
from dotenv import load_dotenv
from Data.loader import Loader
from Data.target.validator import Validator
from typing import Tuple, List

load_dotenv()

def load_validate_targets()->Tuple[pd.DataFrame, List[int]]:
    '''
    Args:
        None
    
    Return:

    '''
    loader = Loader(os.getenv('DATASET_PATH'))
    raw_data = loader.df

    validate = Validator(raw_data)
    targets, vk_ids = validate.build
    return targets, vk_ids