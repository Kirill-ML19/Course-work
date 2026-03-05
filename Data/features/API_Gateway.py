import vk_api
import time
import threading
from typing import List, Dict, Any
from Data.features.client import Client
from vk_api import VkApi
from vk_api.vk_api import VkApiMethod
from Data.features.types import FriendResponse, PhotoResponse, GroupResponse, FriendshipResponse, LikesResponse, MutualGroupResponse, MutualCitiesResponse, MutualEducationResponse

class API_Gateway(Client):

    def __init__(self)->None:
        super().__init__()
        self._api_lock = threading.Lock()
        self._last_call_time = 0
        self._min_interval = 0.35
    
    def _call_vk_method(self, method: str, params: dict = None, retries: int = 3)->Any:
        for attempt in range(retries):
            try:
                with self._api_lock:
                    now = time.monotonic()
                    elapsed = now - self._last_call_time
                    if elapsed < self._min_interval:
                        time.sleep(self._min_interval - elapsed)
                    response = self.session.method(method, params)
                    self._last_call_time = time.monotonic()
                return response
            except vk_api.exceptions.ApiError as e:
                if e.code == 6:
                    delay = 0.35 * (2 ** attempt) + (hash(str(params)) % 10) / 100
                    time.sleep(delay)
                    continue
                else:
                    print(f'VK API error in {method}: {e}')
                    raise
            except vk_api.exceptions.ApiHttpError as e:
                if e.response.status_code == 500:
                    if attempt < retries - 1:
                        delay = 1.5 * (attempt + 1)
                        print(f'HTTP 500. Retry {attempt+1}/{retries}. Sleep {delay:.2f}s')
                        time.sleep(delay)
                        continue 
                    raise
        else:
            raise RuntimeError(f'Failed after {retries} retries for method {method} with params {params}')

    def _get_friends(self,user_id:int)->FriendResponse:
        '''
        This Method gets a complete list of VK user's friends with basic demographic data.

        Args:
            user_id : int - VK user ID whose friends should be retrieved.
            retries : int, (default=3) - Number of retry attempts if a rate limit error occurs.

        Returns:
            FriendsResponse
                Dictionary with:
                    count : int - total number of friends 
                    items : List[FriendItem] - List of friend objects. Each object may contain:

                    Required fields:
                        id : int - VK user ID.
                    Optional fields:
                        sex : int - (0=unknown, 1=female, 2=male)
                        first_name: str - First name of the user. 
                        last_name: str - Last name of the user.
                        is_closed: bool - Whether the profile is private.
                        can_access_closed : bool - Whether the token owner can access private profile.
                        track_code : str - Internal VK tracking code (not always present).

        Raises:
            vk_api.exceptions.ApiError
                If VK API returns an error other than rate limit.

            RuntimeError
                If the request fails after the specified number of retries.
        '''
        all_items = []
        offset = 0
        count = 5000
        while True:
            params = {
                'user_id': user_id,
                'fields': 'sex',
                'count': count,
                'offset': offset
            }
            response = self._call_vk_method('friends.get', params)
            items = response.get('items', [])
            all_items.extend(items)
            if len(items) < count:
                break
            offset += count
        return {'count': len(all_items), 'items': all_items}

    def _get_mutual_friends(self, user_id: int, other_user_ids: List[int])->Dict[int, List[int]]:
        '''
        This method returns the number of mutual friends between users.

        Args:
            user_id: int - VK user ID.
            other_user: int - Other VK user ID.
            retries: int (default = 3) - Number of retry attempts if a rate limit error occurs.

        Returns:
            List[int] - List of mutual friends. 

        Raises:
            vk_api.exceptions.ApiError
                If VK API returns an error other than rate limit.

            RuntimeError
                If the request fails after the specified number of retries.
        '''
        other_user = list(set(other_user_ids[other_user_ids.index(user_id):]) - {user_id})  

        if not other_user:
            return {}

        result = {uid: [] for uid in other_user} 
        chunk_size = 100
        chunks = [other_user[i:i + chunk_size] for i in range(0, len(other_user), chunk_size)]
        query_iterations = 5

        for i in range(0, len(chunks), query_iterations):
            batch = chunks[i: i + query_iterations]
            code = '''
            var chunks = Args.chunks.split("|");
            var results = [];
            var j = 0;
            while (j < chunks.length) {
                var target_uids = chunks[j];
                var response = API.friends.getMutual({
                    "source_uid": Args.user_id,
                    "target_uids": target_uids
                });
                results = results + [response];
                j = j + 1;
            }
            return results;
            '''
            chunks_str = '|'.join(','.join(map(str, ch)) for ch in batch)
            params = {'code': code, 'user_id': user_id, 'chunks': chunks_str}
            batch_responses = self._call_vk_method('execute', params)
            for resp_list in batch_responses:
                for resp in resp_list:
                    other_id = resp.get('id')
                    mutual = resp.get('common_friends', [])
                    result[other_id] = mutual
        return result

    def _get_friendship(self, user_id: int, other_user_ids: List[int])->List[FriendshipResponse]:
        '''
        This method checks if there is a friendship between the users.

        Args:
            user_id: int - VK user ID.
            user_ids: List[int] - A list of users whose friendship status needs to be checked.
            retries: int (default = 3) - Number of retry attempts if a rate limit error occurs.
        
        Returns:
            List[FriendshipResponse]
                List of Dictionaries with structure:
                    friend_status: int - (
                        0 - The user is not a friend.
                        1 - The request has been sent to the user.
                        2 - There is an incoming request from the user.
                        3 - The user is a friend.
                    )
                    user_id: int - VK user ID.
        
        Raises:
            vk_api.exceptions.ApiError
                If VK API returns an error other than rate limit.

            RuntimeError
                If the request fails after the specified number of retries.
        '''
        if not other_user_ids:
            return []
        items = []
        chunk_size = 100
        chunks = [other_user_ids[i:i + chunk_size] for i in range(0, len(other_user_ids), chunk_size)]
        query_iterations = 25

        for i in range(0, len(chunks), query_iterations):
            batch = chunks[i:i + query_iterations]
            code = '''
            var chunks = Args.chunks.split("|");
            var results = [];
            var j = 0;
            while (j < chunks.length) {
                var user_ids = chunks[j];
                var response = API.friends.areFriends({
                    "user_id": Args.user_id,
                    "user_ids": user_ids
                });
                results = results + [response];
                j = j + 1;
            }
            return results;
            '''
            chunks_str = '|'.join(','.join(map(str, ch)) for ch in batch)
            params = {'code': code, 'user_id': user_id, 'chunks': chunks_str}
            batch_responses = self._call_vk_method('execute', params)
            for resp_list in batch_responses:
                items.extend(resp_list)
        return items

    def _get_groups(self,user_id:int)->GroupResponse:
        '''
        This method gets the number of user groups using VK API.

        Args:
            user_id: int - VK user ID.
            retries: int (default = 3) - Number of retry attempts if a rate limit error occurs.

        Returns: 
            GroupResponse
                Dictionary with:
                    count: int - total number of groups.
                    items: List[int] - List of group id.
        Raises:
            vk_api.exceptions.ApiError
                If VK API returns an error other than rate limit.

            RuntimeError
                If the request fails after the specified number of retries.
        '''
        all_items = []
        offset = 0
        count = 1000
        while True:
            params = {
                'user_id': user_id,
                'extended': 1,
                'fields': 'members_count',
                'offset': offset,
                'count': count
            }
            response = self._call_vk_method('groups.get', params)
            items = response.get('items', [])
            all_items.extend(items)
            if len(items) < count:
                break
            offset += count
        return {'count': len(all_items), 'items': all_items} 
        
    def _get_photo(self, user_id: int)->PhotoResponse:
        '''
        Retrieves all photos from the user's wall album using VK API.

        Args:
            user_id : int - VK user ID whose photos should be retrieved.
            retries : int, (default=3) - Number of retry attempts for a single request if a rate limit error occurs.

        Returns:
            PhotosResponse
                Dictionary containing:
                    count : int - Total number of photos retrieved for the user.
                    items : List[PhotoItem]
                        List of photo objects. Each photo may include:
                            id : int - Photo ID.
                            owner_id : int - ID of the photo owner.
                            album_id : int - Album identifier.
                            date : int - Unix timestamp of photo creation.
                            text : str - Caption or description of the photo.
                            sizes : List[PhotoSize] - Available photo resolutions with URLs.
                            likes : LikesObject - Like statistics (count, user_likes).
                            comments : CountObject - Number of comments.
                            reposts : CountObject - Number of reposts.
                            tags : CountObject - Number of tags.
                            orig_photo : OrigPhoto - Original high-resolution photo metadata.

        Raises:
            vk_api.exceptions.ApiError
                Raised if a VK API error occurs other than rate limit (error code 6).
            RuntimeError
                Raised if the request fails after the specified number of retriRaises:
            vk_api.exceptions.ApiError
                If VK API returns an error other than rate limit.

            RuntimeError
                If the request fails after the specified number of retries.es.
        '''
        all_items = []
        offset = 0
        count = 1000
        while True:
            params = {
                'owner_id': user_id,
                'album_id': 'wall',
                'extended': 1,
                'offset': offset,
                'count': count
            }
            response = self._call_vk_method('photos.get', params)
            items = response.get('items', [])
            all_items.extend(items)
            if len(items) < count:
                break
            offset += count
        return {'count': len(all_items), 'items': all_items}   
    
    def _get_likes(self, user_id: int, photo_ids: List[int])->List[LikesResponse]:
        '''
        Batch retrieval of likes for multiple photos using VKScript execute.
        
        Args:
            user_id: int - Owner user ID.
            photo_ids: List[int] - List of photo IDs (up to 25 per call).
            retries: int - Retry attempts.
        
        Returns:
            List[LikesResponse]
                List of dictionary with structure:
                    count: int - number of likes.
                    items: Dict
                        Dictionary of likes object. Each photo include:
                            id: int - unique identifier of the object that was liked.
                            type: str - type of object that liked.
                            first_name: str - name of user.
                            last_name: str - surname of user.
                            can_access_closed: bool - the ability to obtain data from a given user.
                            is_closed: bool - whether the user has a private profile or not.
            
        Raises:
            ValueError - If more than 25 photo_ids.
            vk_api.exceptions.ApiError - VK errors.
            RuntimeError - After retries fail.
        '''
        
        if len(photo_ids) > 25:
            raise ValueError('Max 25 photo_ids per batch')
        
        code = """
        var photo_ids = Args.photo_ids.split(",");
        var results = [];
        var i = 0;
        while (i < photo_ids.length) {
            var item_id = parseInt(photo_ids[i]);
            var response = API.likes.getList({
                "type": "photo",
                "owner_id": Args.user_id,
                "item_id": item_id,
                "filter": "likes",
                "extended": 1
            });
            results = results + [response];
            i = i + 1;
        }
        return results;
        """
        photo_ids_str = ','.join(map(str, photo_ids))
        params = {'code': code, 'user_id': user_id, 'photo_ids': photo_ids_str}
        return self._call_vk_method('execute', params)
    
    def _get_mutual_groups(self,user_ids: List[int])->List[MutualGroupResponse]:
        '''
        This method gets groups for multiple VK users.

        Args:
            local_session: VkApi - An authenticated VK API session.
            user_ids: List[int] - List of VK user IDs (max 25).
            retries: int, optional - Number of retry attempts on rate limit error. Defaults to 3.

        Returns:
            List[MutualGroupResponse] 
                A list of response dictionaries for each user. Each dictionary contains:
                    - count (int): Total number of groups for the user.
                    - items (List[int]): List of group IDs.

        Raises:
            ValueError: If `user_ids` contains more than 25 elements.
            vk_api.exceptions.ApiError: If a non-retryable VK API error occurs.
            RuntimeError: If the request fails after the specified number of retries.
        '''
        if len(user_ids) > 25:
            raise ValueError('Max 25 user_ids per batch')
        code = """
        var user_ids = Args.user_ids.split(",");
        var results = [];
        var i = 0;
        while (i < user_ids.length) {
            var user_id = parseInt(user_ids[i]);
            var count = 1000;
            var offset = 0;
            var all_items = [];
            var response = API.groups.get({
                "user_id": user_id,
                "extended": 0,
                "count": count,
                "offset": offset
            });
            var total = response.count;
            all_items = all_items + response.items;
            var pages = 0;
            while (offset + count < total && pages < 3) {
                offset = offset + count;
                response = API.groups.get({
                    "user_id": user_id,
                    "extended": 0,
                    "count": count,
                    "offset": offset
                });
                all_items = all_items + response.items;
                pages = pages + 1;
            }
            results = results + [{"count": all_items.length, "items": all_items}];
            i = i + 1;
        }
        return results;
        """
        user_ids_str = ','.join(map(str, user_ids))
        params = {'code': code, 'user_ids': user_ids_str}
        return self._call_vk_method('execute', params)
    
    def _get_mutual_cities(self, user_ids:List[int])->List[MutualCitiesResponse]:
        '''
        Retrieves city information for a batch of VK users.

        Args:
            user_ids (List[int]): List of VK user IDs to retrieve city information for. Maximum allowed length is 25 (VK execute limit).
            retries (int, optional): Number of retry attempts in case of rate limit errors (code 6). Defaults to 3.

        Returns:
            MutualCitiesResponse 
                List of dictionaries, where each dictionary represents a user and contains:
                    id: int - User ID (added manually for convenience).
                    city: Dict - Dictionary with structure:
                        id: int - City ID.
                        title: str - City name. 
                    first_name: str - User's first name.
                    last_name: str - User's last name.
                    can_access_closed: bool - Whether the token owner can access the closed profile.
                    is_closed: bool - Whether the user's profile is closed.

        Raises:
            ValueError: If len(user_ids) > 25.
            vk_api.exceptions.ApiError: If VK API returns an error other than rate limit (code 6).
            RuntimeError: If all retry attempts fail.
        '''
        result = []
        batch_size = 1000  

        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]

            response = self._call_vk_method(
                "users.get",
                {
                    "user_ids": ",".join(map(str, batch)),
                    "fields": "city"
                }
            )

            result.extend(response)

        return result
    
    def _get_education(self, user_ids: List[int])->List[MutualEducationResponse]:
        '''
        This method makes API requests to VK servers, extracting information about the user's education.

        Args:
            user_ids: List[int] - List of VK user IDs (max 25).
            retries: int, optional - Number of retry attempts on rate limit error. Defaults to 3.
        
        Returns:
            List[MutualEducationResponse]
                A list of response dictionaries for each user. Each dictionary contains:
                    id: int - User ID.
                    university: NotRequired[int] - University ID.
                    university_name: NotRequired[int] - University name.
                    faculty: NotRequired[int] - Faculty ID.
                    faculty_name: NotRequired[str] - Faculty name. 
                    graduation: NotRequired[int] - Graduation year.
                    education_form: NotRequired[str] - Form of education.
                    first_name: str - User's first name.
                    last_name: str - User's last name.
                    can_access_closed: bool - Whether the token owner can access the closed profile.
                    is_closed: bool - Whether the user's profile is closed.
        
        Raises:
            ValueError: If len(user_ids) > 25.
            vk_api.exceptions.ApiError: If VK API returns an error other than rate limit (code 6).
            RuntimeError: If all retry attempts fail.
        '''
        if len(user_ids) > 25:
            raise ValueError('Max 25 user_ids per batch')
        code = '''
        var user_ids = Args.user_ids.split(',');
        var results = [];
        var i = 0;
        while (i < user_ids.length) {
            var user_id = parseInt(user_ids[i]);
            var response = API.users.get({
                'user_ids': user_id,
                'fields': 'education'
            });
            results = results + [response[0]];
            i = i + 1;
        }
        return results;
        '''
        user_ids_str = ','.join(map(str, user_ids))
        params = {'code': code, 'user_ids': user_ids_str}
        responses = self._call_vk_method('execute', params)
        for idx, resp in enumerate(responses):
            resp['id'] = user_ids[idx]
        return responses