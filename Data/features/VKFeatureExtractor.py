import time
import logging
from dotenv import load_dotenv
from collections import Counter, defaultdict
from vk_api.vk_api import VkApiMethod 
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Generator, Any
from Data.features.API_Gateway import API_Gateway
from Data.features.types import GroupFeatures, PhotoFeatures, MutualFriendsItems, LikesItemsFeatures, MutualGroupsItems, MutualCitiesItems, MutualEducationItems, NodeFeatures, FriendshipFeaturesItems
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
logging.basicConfig(level=logging.INFO)

class VKFeaturesExtractor(API_Gateway):

    '''
    A feature extractor that computes node and edge features for a graph of VK users.

    This class inherits from API_Gateway to access raw VK API data and transforms it
    into structured numerical and categorical features suitable for graph analysis,
    machine learning models, or social network visualization.


    Features include:
        - Node features: friends, photos, groups, likes, education, etc.
        - Edge features: mutual friends, friendship status, likes on photos, mutual groups, common city, mutual education attributes.

    Attributes:
        users_id (List[int]): List of VK user IDs to process (set internally for uniqueness).
    '''

    def __init__(self, users_id: List[int])->None:
        '''
        Initializes the feature extractor with a list of VK user IDs.

        Args:
            users_id: List[int] - List of VK user IDs to extract features for.

        Raises:
            ValueError: If users_id is empty.
        '''
        super().__init__()
        if not users_id:
            raise ValueError("users_id list cannot be empty")
        self.users_id = users_id

    def _friends_features(self, user_id:int)->Dict[str, int]:
        '''
        Extracts friend-based features.

        Parametrs:
            user_id: int - VK user id.

        Returns:
            Dict[str, int]
                {
                    'friends_count': int,
                    'male_count': int,
                    'female_count': int,
                    'unknown_count': int
                }
        '''
        response = self._get_friends(user_id)
        users = response.get('items', [])
        male = female = unknown = 0
        for user in users:
            s = user.get('sex', 0)
            if s == 1:
                female += 1
            elif s == 2:
                male += 1
            else:
                unknown += 1
        return {
            'friends_count': response.get('count', 0),
            'male_count': male,
            'female_count': female,
            'unknown_count': unknown
        }

    def _groups_features(self,user_id: int)->GroupFeatures:
        '''
        Extracts group-based features:
            total photos
        
        Parametrs:
            user_id: int - VK user ID.
        
        Returns:
            GroupFeatures
                Dictionary with structure:
                    {
                        'group_count': int
                        'average_member': float
                    }

        '''
        response = self._get_groups(user_id)
        groups = response.get('items', [])
        member_sum = sum(group.get('members_count', 0) for group in groups)
        count = response.get('count', 0)
        avg = member_sum / count if count > 0 else 0.0
        return {
            'groups_count': count,
            'average_member': round(avg, 2)
        }

    def _photo_features(self, user_id: int)->PhotoFeatures:
        '''
        Extracts photo-based features:
            total photos
            total likes
            average number of likes 

        Parameters:
            user_id : int - VK user id.

        Returns:
            Dict[str, int]
                {
                    'photo_count': int,
                    'likes_total': int,
                    'average_likes': float
                }
        '''
        response = self._get_photo(user_id)
        items = response.get('items', [])
        photo_count = response.get('count', 0)
        likes_total = sum(photo.get('likes', {}).get('count', 0) for photo in items)
        avg = likes_total / photo_count if photo_count > 0 else 0.0
        return {
            'photo_count': photo_count,
            'likes_total': likes_total,
            'average_likes': round(avg, 2)
        }
    
    def _extract_for_user(self, user_id: int, local_vk: VkApiMethod = None)->NodeFeatures:
        '''
        Extracts base features for a single user using local vk session.

        Args:
            user_id: int - VK user ID from whom data is collected.
            local_vk: VkApiMethod - Local VK API session.

        Returns:
            NodeFeatures
                Dictionary with structure:
                    user_id: int - VK user ID from whom data is collected.
                    friends_count: int - Quantity of friends.
                    male_count: int - Quantity of male friends.
                    female_count: int - Quantity of femalw friends.
                    unknown_count: int - Number of friends whose gender is unspecified.
                    photo_count: int - Number of photos the user has.
                    likes_total: int - The total number of likes a user has.
                    average_likes: float - Average number of likes per photo.
                    groups_count: int - Number of groups.
                    average_member: float - Average number of users in a group.

        '''
        features = {'user_id': user_id}
        try:
            features.update(self._friends_features(user_id))
            features.update(self._photo_features(user_id))
            features.update(self._groups_features(user_id))
        except Exception as e:
            logging.warning(f'Error extracting features for {user_id}: {e}')
        return features
        
    def node_attributes(self, max_workers: int = 3)->Generator[NodeFeatures, None, None]:
        '''
        This method collects all the features for the user that will be attributes of the node in the graph.

        Args:
            max_worker: int, optional - Number of parallel workers. Defaults to 5.

        Yields:
            NodeFeatures
        '''
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._extract_for_user, user_id) for user_id in self.users_id]
            for future in as_completed(futures):
                try:
                    yield future.result()
                except Exception as e:
                    logging.error(f'Thread error: {e}')
    
    def _mutual_friends_features(self)->List[MutualFriendsItems]:
        '''
        Extracts the count of mutual friends with other users.

        Args:
            user_id (int): Target user ID to check for mutual friends.

        Returns:
            List[MutualFriendsItems]
                A list of dictionaries with structure: 
                    user_id: int - Another user's ID.
                    count_mutual_friends: int - Number of mutual friends.
        
        Raises:
            Exception: Logs error and returns fallback with empty items.
        '''
        friends_map = {}
        for user_id in self.users_id:
            response = self._get_friends(user_id).get('items', [])
            friends_map[user_id] = {f['id'] for f in response if f.get('id')}

        result = {uid: {} for uid in self.users_id}

        for i, u1 in enumerate(self.users_id):
            for u2 in self.users_id[i+1:]:
                mutual = len(friends_map[u1] & friends_map[u2])
                result[u1][u2] = mutual
                result[u2][u1] = mutual 

        return result

    def _friendship_features(self)->List[FriendshipFeaturesItems]:
        '''
        Extracts friendship status with other users.

        Args:
            user_id: int - Target user ID.

        Returns:
            List[FriendshipFeaturesItems]
                A list of dictionary with structure:
                    user_id: int - Another user's ID. 
                    friend_status: int - friendship status between users. 
        
        Raises:
            Exceptions: This method catches all exceptions internally and prints an error message.
        '''
        result = {uid: {} for uid in self.users_id}

        for i, u1 in enumerate(self.users_id):
            other_users = self.users_id[i+1:]
            if not other_users:
                continue

            responses = self._get_friendship(u1, other_users)

            for resp in responses:
                u2 = resp.get('user_id')
                status = resp.get('friend_status', 0)
                result[u1][u2] = status
                result[u2][u1] = status

        return result

        
    def _likes_features(self)->List[LikesItemsFeatures]:
        '''
        Compute the number of likes each other user has given to the target user's photos.
        
        Args:
            user_id: int - Target user ID.

        Returns:
            List[LikesItemsFeatures]
                A list of dictionaries with structure:
                    user_id : int - Another user's ID.
                    count_likes: int - Number of likes between users.
        
        Raises:
                        Exceptions: This method catches all exceptions internally and prints an error message.
        '''
        result = {uid: {} for uid in self.users_id}

        for user_id in self.users_id:

            photos = self._get_photo(user_id).get('items', [])
            photo_ids = [p['id'] for p in photos if p.get('id')]

            if not photo_ids:
                for other in self.users_id:
                    if other != user_id:
                        result[user_id][other] = 0
                continue

            all_likes = Counter()
            batch_size = 25

            for i in range(0, len(photo_ids), batch_size):
                batch_ids = photo_ids[i:i + batch_size]
                batch_response = self._get_likes(user_id, batch_ids)

                for resp in batch_response:
                    for liker in resp.get('items', []):
                        liker_id = liker.get('id')
                        if liker_id in self.users_id:
                            all_likes[liker_id] += 1

            for other in self.users_id:
                if other == user_id:
                    continue
                result[user_id][other] = all_likes.get(other, 0)

        return result
    
    def _mutual_groups_features(self)->List[MutualGroupsItems]:
        '''
        This method calculates the number of users grouped together between the target user and all other users.

        Args:
            user_id: int - The ID of the target user.

        Returns:
            MutualGroupsFeatures 
                A dictionary containing:
                    - user_id: int - The target user ID.
                    - items: List[Dict[str, int]] - A list of dictionaries, each with:
                        - user_id: int - ID of another user.
                        - count_mutual_groups: int - Number of groups shared with target.
        
        Raises:
            This method catches all exceptions internally and returns an empty item list for the target user in case of failure. No exceptions are propagated.
        '''
        groups_map = {}

        for user_id in self.users_id:
            response = self._get_groups(user_id)
            groups = response.get("items", [])
            group_ids = {g["id"] for g in groups if g.get("id")}
            groups_map[user_id] = group_ids

        result = {uid: {} for uid in self.users_id}

        for i, u1 in enumerate(self.users_id):
            for u2 in self.users_id[i + 1:]:

                mutual_count = len(
                    groups_map.get(u1, set()) &
                    groups_map.get(u2, set())
                )

                result[u1][u2] = mutual_count
                result[u2][u1] = mutual_count 

        return result
    
    def _common_city_features(self)->List[MutualCitiesItems]:
        '''
        This method calculates whether other users are in the same city as the primary user (user_id).

        Args:
            user_id (int): ID of the primary VK user for whom the feature should be calculated.

        Returns:
            MutualCitiesFeatures
                A dictionary containing:
                    user_id: int - The target user ID.
                    items: A list of dictionaries, with each:
                        user_id: int - ID other user.
                        common_city: int - (1  - if the user's city matches the city of another user, else -  0)

        Raises:
            Exception: Any runtime errors (API, network, parsing, etc.) are logged and return a fallback structure with common_city=0 for everyone.
        '''
        users_info = self._get_mutual_cities(self.users_id)

        city_map = {
            u['id']: u.get('city', {}).get('id')
            for u in users_info
        }

        result = {uid: {} for uid in self.users_id}

        for i, u1 in enumerate(self.users_id):
            for u2 in self.users_id[i+1:]:
                common = 1 if city_map[u1] == city_map[u2] else 0
                result[u1][u2] = common
                result[u2][u1] = common

        return result

    def _mutual_education_features(self)->List[MutualEducationItems]:
        '''
        Calculates common educational characteristics between the target user and other users (same university, faculty).

        Args:
            user_id: int - Target user's ID.

        Returns:
            MutualEducationFeatures
                A dictionary containing:
                    user_id: int - Target user's ID.
                    items: A list of dictionaries with each:
                        user_id: int - Another user's ID.
                        common_university: int - (if the same university - 1, else - 0)
                        common_faculty: int - (if the same faculty - 1, else - 0)
        
        Raises:
            Exception: Any runtime errors (API, network, parsing, etc.) are logged and return a fallback structure with common_university=0 and common_faculty=0 for everyone.
        '''
        batch_size = 25
        education_map = {}

        for i in range(0, len(self.users_id), batch_size):
            batch = self.users_id[i:i + batch_size]
            responses = self._get_education(batch)

            for idx, resp in enumerate(responses):
                uid = batch[idx]
                education_map[uid] = {
                    "university": resp.get("university"),
                    "faculty": resp.get("faculty"),
                }

        result = {uid: {} for uid in self.users_id}

        for i, u1 in enumerate(self.users_id):
            edu1 = education_map.get(u1, {})

            for u2 in self.users_id[i + 1:]:
                edu2 = education_map.get(u2, {})

                common_univ = (
                    1
                    if edu1.get("university")
                    and edu1.get("university") == edu2.get("university")
                    else 0
                )

                common_fac = (
                    1
                    if edu1.get("faculty")
                    and edu1.get("faculty") == edu2.get("faculty")
                    else 0
                )

                result[u1][u2] = {
                    "common_university": common_univ,
                    "common_faculty": common_fac,
                }

                result[u2][u1] = {
                    "common_university": common_univ,
                    "common_faculty": common_fac,
                }

        return result
    
    def build_edge_features(self):

        mutual_friends = self._mutual_friends_features()
        mutual_groups = self._mutual_groups_features()
        city = self._common_city_features()
        education = self._mutual_education_features()
        friendship = self._friendship_features()

        edges = []

        for i, u1 in enumerate(self.users_id):
            for u2 in self.users_id[i+1:]:

                edges.append({
                    "source": u1,
                    "target": u2,
                    "features": {
                        "mutual_friends": mutual_friends[u1][u2],
                        "mutual_groups": mutual_groups[u1][u2],
                        "common_city": city[u1][u2],
                        "common_university": education[u1][u2]["common_university"],
                        "common_faculty": education[u1][u2]["common_faculty"],
                        "friend_status": friendship[u1][u2],
                    }
                })

        return edges