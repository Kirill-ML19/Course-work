from typing import TypedDict, List, Dict, NotRequired

class FriendItem(TypedDict, total = False):
    id: int
    track_code: str
    sex: int
    first_name: str
    last_name: str
    can_access_closed: bool
    is_closed: bool

class FriendResponse(TypedDict):
    count: int
    items: List[FriendItem]

class PhotoSize(TypedDict, total = False):
    height: int
    width: int
    type: str
    url: str

class CountObject(TypedDict, total = False):
    count: int

class LikesObject(CountObject, total = False):
    user_likes: int

class OrigPhoto(TypedDict, total=False):
    height: int
    width: int
    type: str
    url: str

class PhotoItem(TypedDict, total=False):
    id: int
    owner_id: int
    album_id: int
    date: int
    text: str
    can_comment: int

    sizes: List[PhotoSize]
    square_crop: str
    web_view_token: str

    likes: LikesObject
    comments: CountObject
    reposts: CountObject
    tags: CountObject

    orig_photo: OrigPhoto


class PhotoResponse(TypedDict):
    count: int
    items: List[PhotoItem]

class PhotoFeatures(TypedDict):
    photo_count: int
    likes_total: int
    average_likes: float

class GroupItem(TypedDict, total = False):
    id: int
    members_count: int
    name: str
    screen_name: str
    is_closed: int
    type: str
    is_admin: int
    is_member: int
    is_advertiser: int
    photo_50: str
    photo_100: str
    photo_200: str


class GroupResponse(TypedDict):
    count: int 
    items: List[GroupItem]

class GroupFeatures(TypedDict):
    group_count: int
    average_member: float

class FriendshipResponse(TypedDict):
    friend_status: int
    user_id: int

class MutualFriendsItems(TypedDict):
    user_id: int
    count_mutual_friends: int

class LikesItemsResponse(TypedDict):
    id: int
    type: str
    first_name: str
    last_name: str
    can_access_closed: bool
    is_closed: bool

class LikesResponse(TypedDict):
    count: int
    items: LikesItemsResponse

class LikesItemsFeatures(TypedDict):
    user_id: int
    count_likes: int

class MutualGroupResponse(TypedDict):
    count: int
    items: List[int]

class MutualGroupsItems(TypedDict):
    user_id: int
    count_mutual_groups: int

class MutualCityItems(TypedDict):
        id: int
        title: str

class MutualCitiesResponse(TypedDict):
    id: int
    city: MutualCityItems
    first_name: str
    last_name: str
    can_access_closed: bool
    is_closed: bool

class MutualCitiesItems(TypedDict):
    user_id: int
    common_city: int

class MutualEducationResponse(TypedDict):
    id: int
    university: NotRequired[int]
    university_name: NotRequired[str]
    faculty: NotRequired[int]
    faculty_name: NotRequired[str]
    graduation: NotRequired[int]
    education_form: NotRequired[str]
    first_name: str
    last_name: str
    can_access_closed: bool
    is_closed: bool

class MutualEducationItems(TypedDict):
    user_id: int
    common_university: int
    common_faculty: int

class FriendshipFeaturesItems(TypedDict):
    user_id: int
    friend_status: int

class NodeFeatures(TypedDict):
    user_id: int
    friends_count: int
    male_count: int
    female_count: int
    unknown_count: int
    photo_count: int
    likes_total: int
    average_likes: float
    groups_count: int
    average_member: float
