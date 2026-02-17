import vk_api
from Data.features.client import Client
from functools import lru_cache
from typing import List

class VKValidator(Client):

    '''
    Vk Validator makes requests through the VK API that determine the user's account status. 
    '''

    def __init__(self)->None:
        super().__init__()

    @lru_cache
    def _is_acessible(self, users_id: str)->List:
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
