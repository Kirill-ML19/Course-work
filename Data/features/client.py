import os
import vk_api
from dotenv import load_dotenv

load_dotenv()

class Client:
    def __init__(self)->None:
        self.session = vk_api.VkApi(token=os.getenv('ACCESS_TOKEN_VK'))
        self.vk = self.session.get_api()