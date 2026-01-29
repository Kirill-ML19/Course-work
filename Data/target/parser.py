import pandas as pd
import numpy as np 
import ast
from typing import Dict

def parsing(result_str: str)->pd.Series:
    '''
    This function parses the string representation of the personality analysis result and extracts data according to the Big Five model.

    Parametrs:
        result_str (str): a string with serialized data

    Return:
        Dict[str, object]
        dictionary with parsing results
        {
            'big_five': Dict[strm, float | np.nan]
            'additional_info': Dict[str, dict]
            'has_additional_info': bool
        }
    '''
    try:
        data = ast.literal_eval(result_str)
        if isinstance(data, list) and len(data) > 0:
            big_five = data[0]
            traits = [trait for trait in big_five.keys()]
            filter_result = {}
            for trait in traits:
                if trait in big_five:
                    try:
                        filter_result[trait] = float(big_five[trait])
                    except (ValueError, TypeError):
                        filter_result[trait] = np.nan
            return {'big_five': filter_result}
        else:
            return {'big_five': {}}
    except Exception as e:
        print(f'Error of parsing {e}')
        return {'big_five': {}}