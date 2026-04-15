import os
import logging
from dotenv import load_dotenv
from Scripts.process_target import load_validate_targets
from Database.Postgresql.crud import CRUD
from Database.Postgresql.session import engine

df_targets, vk_ids = load_validate_targets()

load_dotenv()
logging.basicConfig(level=logging.INFO)

def db():

    CRUD.create_tables(engine)
    
    crud = CRUD(client_vk_id=int(os.getenv('VK_ID')), vk_users=vk_ids, targets=df_targets)
    crud.insert_targets()
db()
