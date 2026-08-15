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
    
    crud = CRUD()
    crud.insert_raw_date(rawdates=df_targets)
    crud.insert_vk_users()
    crud.insert_node_features(max_worker=5)
db()