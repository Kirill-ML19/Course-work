from typing import List
from Database.Postgresql.session import Session as DBSession 
from Database.Postgresql.base import Base
from sqlalchemy.exc import IntegrityError
from Database.Postgresql.model import Client, VkUser, NodeFeatures
from Data.features.VKFeatureExtractor import VKFeaturesExtractor
import logging

logging.basicConfig(level=logging.INFO)

class CRUD():

    def __init__(self, client_vk_id: int, vk_users:List[int] )->None:
        '''
        Initializing a CRUD operation for a specific client and a list of its VK users.

        Args:
            client_vk_id: int - VK client ID.
            vk_users: List[int] - List of VK IDs of users to add.
        '''
        self.client_vk_id = client_vk_id
        self.vk_users = vk_users

    @staticmethod
    def create_tables(engine)->None:
        """
        Creates all tables defined in models if they do not exist.

        Args:
            engine: SQLAlchemy engine instance.

        """
        Base.metadata.create_all(bind=engine)
        logging.info("Tables checked/created successfully.")

    def insert_client(self)->None:
        '''
        Adds a new client to the clients table using their VK ID.

        The function opens a database session, creates a Client object with the specified
        VK ID, and attempts to save it. If a client with the same VK ID already exists,
        an IntegrityError exception is caught, the transaction is rolled back,
        and a warning is written to the log.
        
        Returns:
            None
        
        Raises:
            IntegrityError - unique data duplication error.
        
        '''
        with DBSession() as db_session:
            client = Client(vk_id = self.client_vk_id)
            db_session.add(client)
            try:
                db_session.commit()
                logging.info(f'Client with vk_id={self.client_vk_id} created.')
            except IntegrityError:
                db_session.rollback()
                logging.warning('The client has already been added to the table')

    def insert_vk_users(self)->None:
        '''
        Adds a list of VK users for the client identified by self.client_vk_id.

        If a client with the specified VK ID doesn't exist in the clients table, it is created.
        Then, for each VK ID from self.vk_users, a record is created in the vk_users table,
        linked to the client data via the client_id foreign key.
        All operations are performed in a single transaction: either all are applied,
        or the transaction is rolled back if necessary.

        Ards:
            None

        Returns:
            None

        Logging:
            - INFO if users were successfully added.
            - ERROR if an IntegrityError occurs (the exception is rethrown).
        '''
        with DBSession() as db_session:
            client = db_session.query(Client).filter(Client.vk_id == self.client_vk_id).first()
            if not client:
                client = Client(vk_id =self.client_vk_id)
                try:
                    db_session.flush()
                except IntegrityError:
                    db_session.rollback()


            for vk_user in self.vk_users:
                new_vk_user = VkUser(vk_id = vk_user, client_id = client.id)
                db_session.add(new_vk_user)

            try:
                db_session.commit()
                logging.info(f'Added {len(self.vk_users)} VK users for client vk_id={self.client_vk_id}')
            except IntegrityError as e:
                db_session.rollback()
                logging.error(f'Failed to insert VK users for client {self.client_vk_id}: {e}')
                raise
            
            

    def insert_node_features(self, max_worker: int = 3)->None:
        """
        Inserts or updates node features into the 'node_features' table for all users in extractor.users_id.

        Assumes Client with vk_id = client_vk_id exists (your token/user ID).
        Assumes VkUser records for extractor.users_id already exist under this client.
        If NodeFeatures for a VkUser exists, updates it; otherwise, inserts new.

        Args:
            max_workers: int - Number of threads for parallel data collection.

        Raises:
            ValueError: If Client or VkUser not found.
            Exception: Logs and skips if feature extraction or insert fails for a user.
        """
        extractor = VKFeaturesExtractor(self.vk_users)

        with DBSession() as db_session:

            client = db_session.query(Client).filter(Client.vk_id == self.client_vk_id).first()
            if not client:
                raise ValueError(f"Client with vk_id {self.client_vk_id} not found.")

            for features in extractor.node_attributes(max_worker=max_worker):
                    vk_id = features.get('user_id')
                    if not vk_id:
                        logging.warning()
                        continue
                    try:

                        vk_user = db_session.query(VkUser).filter(
                            VkUser.vk_id == vk_id,
                            VkUser.client_id == client.id
                        ).first()
                        if not vk_user:
                            logging.warning(f"VkUser with vk_id {vk_id} not found for client {self.client_vk_id}, skipping insert.")
                            continue

                        node_feat = db_session.query(NodeFeatures).filter(NodeFeatures.vk_user_id == vk_user.id).first()

                        if node_feat:
                            node_feat.friends_count = features.get('friends_count', 0)
                            node_feat.male_friends = features.get('male_count', 0)
                            node_feat.female_friends = features.get('female_count', 0)
                            node_feat.unknown_friends = features.get('unknown_count', 0)
                            node_feat.photo_count = features.get('photo_count', 0)
                            node_feat.likes_total = features.get('likes_total', 0)
                            node_feat.average_likes = features.get('average_likes', 0.0)
                            node_feat.groups_count = features.get('groups_count', 0)
                            node_feat.average_member = features.get('average_member', 0.0)
                            logging.info(f"Updated node features for vk_id {vk_id}")
                        else:
                            node_feat = NodeFeatures(
                                vk_user_id=vk_user.id,
                                friends_count=features.get('friends_count', 0),
                                male_friends=features.get('male_count', 0),
                                female_friends=features.get('female_count', 0),
                                unknown_friends=features.get('unknown_count', 0),
                                photo_count=features.get('photo_count', 0),
                                likes_total=features.get('likes_total', 0),
                                average_likes=features.get('average_likes', 0.0),
                                groups_count=features.get('groups_count', 0),
                                average_member=features.get('average_member', 0.0)
                            )
                            db_session.add(node_feat)
                            logging.info(f"Inserted node features for vk_id {vk_id}")

                        db_session.commit()
                    except Exception as e:
                        db_session.rollback()
                        logging.error(f"Error processing node features for vk_id {vk_id}: {e}")