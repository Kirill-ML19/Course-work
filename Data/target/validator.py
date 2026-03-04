import pandas as pd
import numpy as np 
import ast
import vk_api
import time
from Data.target.VkValidator import VKValidator
from typing import List

class Validator(VKValidator):

    '''
    Dataset validation and preprocessing pipeline.

    This class is responsible for:

    1. Parsing personality analysis results
    2. Extracting Big Five psychological traits
    3. Building structured feature dataset
    4. Filtering inaccessible VK users

    Processing stages:

        Raw dataset
            ↓
        Parsing serialized analysis results
            ↓
        Target extraction (Big Five model)
            ↓
        VK profile accessibility validation
            ↓
        Clean dataset construction
    '''

    def __init__(self, dataset: pd.DataFrame)->None:
        '''
        Initialize Validator.

        Args:
            dataset (pd.DataFrame):
                Original dataset containing analysis results.

        Attributes:
            dataset (pd.DataFrame):
                Stored dataset reference.
        '''
        super().__init__()
        self.dataset =  dataset

            
    @property
    def build(self)->tuple[pd.DataFrame, List[int]]:
        '''
        Execute dataset preprocessing pipeline.

        Pipeline stages:

        1. Parse serialized analysis results
        2. Build Big Five feature matrix
        3. Remove inaccessible VK accounts
        4. Extract VK user identifiers

        Returns:
            tuple:
                clean_df (pd.DataFrame):
                    Preprocessed dataset.

                vk_id (List[int]):
                    List of valid VK user identifiers.
        '''
        parsed_result = self.dataset['result'].apply(self._parsing)
        data = self._build(parsed_result)
        clean_df = self._filter_vk_id(data)
        vk_id = self.get_vk_id(clean_df['vk_id'])
        return clean_df, vk_id
    
    def _parsing(self, result_str:str)->dict:
        '''
        This function parses the string representation of the personality analysis result and extracts data according to the Big Five model.

        Parametrs:
            result_str (str): a string with serialized data

        Return:
            Dict[str, object]
            dictionary with parsing results
            {
                'big_five': Dict[str, float | np.nan]
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
            
    def _build(self, parsed_result: pd.Series)->pd.DataFrame:
        '''        
        Construct structured feature dataset.

        The function converts parsed psychological traits into
        numerical feature matrix representation.

        Processing steps:

        1. Extract Big Five trait vectors
        2. Convert to DataFrame format
        3. Remove incomplete feature rows
        4. Merge with metadata columns
        5. Aggregate duplicate VK users keeping latest record

        Returns:
            pd.DataFrame:
                Cleaned feature dataset.
        '''
        columns = [result['big_five'] for result in parsed_result]
        big_five_df = pd.DataFrame(columns)
        big_five_df = big_five_df.drop(columns=big_five_df.columns[-1])

        if not big_five_df.empty:
            big_five_df = big_five_df.dropna(axis=0, how='any', subset=big_five_df.columns[big_five_df.isna().any()].tolist())
        df_final = pd.concat([self.dataset[['vk_id','completion_date']], big_five_df], axis=1)
        df_final = df_final.sort_values('completion_date').groupby('vk_id').last().reset_index()
        df_final = df_final.drop(columns='completion_date')
        return df_final
        
    def _filter_vk_id(self, dataframe:pd.DataFrame, retries: int = 3)->pd.DataFrame:
        '''
        Filter VK users with inaccessible or deleted profiles.

        The function removes users if:

        - Account is deleted or deactivated
        - Profile is closed and inaccessible

        Batch validation is used to reduce API requests.

        Args:
            dataframe (pd.DataFrame):
                Target dataset.

            retries (int):
                Number of retry attempts in case of VK API failure.

        Returns:
            pd.DataFrame:
                Dataset containing only accessible VK users.
        '''
        vk_ids = dataframe['vk_id'].tolist()
        inaccessible_ids = set()

        for attempt in range(retries):
            try:
                chunk_size = 1000
                for i in range(0, len(vk_ids), chunk_size):
                    chunk = vk_ids[i: i+chunk_size]
                    users = self._is_acessible(','.join(map(str, chunk)))

                    for user in users:
                        if user is None:
                            continue

                        if 'deactivated' in user or (user.get('is_closed') and not user.get('can_access_closed')):
                            inaccessible_ids.add(user.get('id'))
                    time.sleep(0.3)
                if inaccessible_ids:
                    dataframe = dataframe[~dataframe['vk_id'].isin(inaccessible_ids)]
                return dataframe.reset_index(drop=True)
            except vk_api.exceptions.ApiError as e:
                time.sleep(1)
                if attempt == retries - 1:
                    raise
        return dataframe.reset_index(drop=True)
    
    def get_vk_id(self,vk_id:pd.Series)->List[int]:
        '''
        Extract VK identifiers from dataset.

        Args:
            vk_id (pd.Series):
                Column containing VK user identifiers.

        Returns:
            List[int]:
                List of VK user IDs.
        '''
        return vk_id.tolist()