import vk_api
import datetime 
from Data.features.client import Client
from functools import lru_cache
from typing import List, Dict

class VKValidator(Client):

    '''
    Vk Validator makes requests through the VK API that determine the user's account status. 
    '''

    def __init__(self)->None:
        super().__init__()

    @lru_cache
    def is_acessible(self, users_id: str)->List[Dict]:
        '''
        Filters users with closed/deleted accounts, using batching for speed.

        Parametrs:
            user_id: int - VK user ID.
        
        Returns:
            bool - If the user has an open account, then True will be returned; if the account is closed or deleted, then False will be returned.
        
        Raises:

        '''
        try:
            response = self.vk.users.get(user_ids=users_id)
            return response
        except vk_api.exceptions.ApiError as e:
            if e.code in (18, 30):
                return []
            raise

    def time_validation(self, users_id: str)->List[int]:
        '''
        '''
        valid_users = []
        valid_time = datetime.datetime.strptime("01-01-2026 00:00:00 +0300", "%d-%m-%Y %H:%M:%S %z")
        try:
            responses = self.vk.users.get(user_ids = users_id, fields = 'last_seen')
            for response in responses:
                if response.get('last_seen',None)!=None:
                    last_seen_time = datetime.datetime.fromtimestamp(response['last_seen']['time'], tz=datetime.timezone.utc)
                    if last_seen_time > valid_time:
                        valid_users.append(response['id'])
            return valid_users
        except vk_api.exceptions.ApiError as e:
            if e.code(18, 30):
                return []
            raise