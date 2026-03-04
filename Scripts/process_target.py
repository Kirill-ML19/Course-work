import os 
from dotenv import load_dotenv
from Data.loader import Loader
from Data.target.validator import Validator
from Data.features.client import Client

load_dotenv()
def load_validate_targets():
    '''
    Args:
        None
    
    Return:

    '''
    loader = Loader(os.getenv('DATASET_PATH'))
    raw_data = loader.df

    client = Client()
    validate = Validator(raw_data)
    targets, vk_ids = validate.build
    return targets, vk_ids