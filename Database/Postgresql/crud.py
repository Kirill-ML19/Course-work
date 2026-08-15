import pandas as pd
from typing import List
from Database.Postgresql.session import Session as DBSession 
from Database.Postgresql.base import Base
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from Database.Postgresql.model import VkUser, NodeFeatures, Targets, RawDate
from Data.features.VKFeatureExtractor import VKFeaturesExtractor
from Data.target.VkValidator import VKValidator
import logging

logging.basicConfig(level=logging.INFO)

class CRUD:

    def __init__(self)->None:
        '''
        Initializing a CRUD operation for a specific client and a list of its VK users.

        Args:
            client_vk_id: int - VK client ID.
            vk_users: List[int] - List of VK IDs of users to add.
        '''
        self.session = DBSession
        self.validator = VKValidator().time_validation

    @staticmethod
    def create_tables(engine)->None:
        """
        Creates all tables defined in models if they do not exist.

        Args:
            engine: SQLAlchemy engine instance.

        """
        try:
            Base.metadata.create_all(bind=engine)
            logging.info("Tables checked/created successfully.")
        except SQLAlchemyError as e:
            logging.error(f'Error creating/verifying database tables: {e}')

    def insert_raw_date(self, rawdates: pd.DataFrame)->None:
        '''
        '''
        batch_size = 1000
        rawdates = rawdates.rename(columns={
            'completion_date': 'Completion_date',
            'Экстраверсия–интроверсия': 'Extraversion',
            'Привязанность–обособленность': 'Agreeableness',
            'Самоконтроль–импульсивность': 'Conscientiousness',
            'Эмоциональная_устойчивость–эмоциональная_неустойчивость': 'Neuroticism',
            'Экспрессивность–практичность': 'Openness'
        })
        records = rawdates.to_dict(orient='records')

        with self.session() as db_session:
            try:
                for i in range(0, len(records), batch_size):
                    batch = records[i: i+batch_size]
                    db_session.bulk_insert_mappings(RawDate, batch)
                    db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise 

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
        batch_size = 1000
        valid_vk_ids = []
        vk_users = []

        with self.session() as db_session:
            response = db_session.query(RawDate).all()
            vk_ids = [vk_user.vk_id for vk_user in response]
            for i in range(0, len(vk_ids), batch_size):
                batch_vk_id = ",".join(map(str, vk_ids[i: i + batch_size]))
                valid_users = self.validator(batch_vk_id)
                valid_vk_ids.extend(valid_users)
            stmt = (
                select(
                    RawDate.vk_id,
                    RawDate.Extraversion,
                    RawDate.Agreeableness,
                    RawDate.Conscientiousness,
                    RawDate.Neuroticism,
                    RawDate.Openness
                )
                .where(RawDate.vk_id.in_(valid_vk_ids))
                .distinct(RawDate.vk_id)
                .order_by(RawDate.vk_id, desc(RawDate.Completion_date))
            )
            valid_responses = db_session.execute(stmt).mappings().all()
            for valid_response in valid_responses:
                user = VkUser(vk_id=valid_response['vk_id'])
                targets = Targets(
                    Extraversion = valid_response['Extraversion'],
                    Agreeableness = valid_response['Agreeableness'],
                    Conscientiousness = valid_response['Conscientiousness'],
                    Neuroticism = valid_response['Neuroticism'],
                    Openness = valid_response['Openness']
                )
                user.targets = targets
                vk_users.append(user)
            for i in range(0, len(vk_users), batch_size):
                try:
                    batch = vk_users[i: i+batch_size]
                    db_session.add_all(batch)
                    db_session.commit()
                    logging.info('The VK user patch has been successfully inserted into the table.')
                except IntegrityError as e:
                    db_session.rollback()
                    logging.error(f'Error inserting VK user patch: {e}')
    
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
        with self.session() as db_session:
            subq = select(VkUser.vk_id).join(NodeFeatures, VkUser.id == NodeFeatures.vk_user_id)
            stmt = select(VkUser.vk_id).where(VkUser.vk_id.not_in(subq))
            vk_users = [vk_user[0] for vk_user in db_session.execute(statement=stmt)]
            #vk_users = [vk_user[0] for vk_user in db_session.execute(statement=select(VkUser.vk_id)).all()]
            extractor = VKFeaturesExtractor(users_id=vk_users)
            
            for features in extractor.node_attributes(max_workers=max_worker):
                    vk_id = features.get('user_id')
                    if not vk_id:
                        logging.warning()
                        continue
                    try:
                        vk_user = db_session.query(VkUser).filter(VkUser.vk_id == vk_id).first()
                        if not vk_user:
                            logging.warning(f"VkUser with vk_id {vk_id} not found, skipping insert.")
                            continue

                        node_feat = db_session.query(NodeFeatures).filter(NodeFeatures.vk_user_id == vk_user.id).first()

                        if node_feat:
                            node_feat.age = features.get('age')
                            node_feat.gender = features.get('gender', 0)
                            node_feat.followers = features.get('followers', 0)
                            node_feat.friends_count = features.get('friends_count', 0)
                            node_feat.male_friends = features.get('male_count', 0)
                            node_feat.female_friends = features.get('female_count', 0)
                            node_feat.unknown_friends = features.get('unknown_count', 0)
                            node_feat.photo_count = features.get('photo_count', 0)
                            node_feat.photo_likes_count = features.get('photo_likes_count', 0)
                            node_feat.average_photo_likes = features.get('average_photo_likes', 0.0)
                            node_feat.photo_comments_count = features.get('photo_comments_count', 0)
                            node_feat.average_photo_comments = features.get('average_photo_comments', 0.0)
                            node_feat.photo_reposts_count = features.get('photo_reposts_count', 0)
                            node_feat.average_photo_reposts = features.get('average_photo_reposts', 0.0)
                            node_feat.post_count = features.get('posts_count', 0)
                            node_feat.post_likes_count = features.get('post_likes_count', 0)
                            node_feat.average_post_likes = features.get('average_post_likes', 0.0)
                            node_feat.post_comments_count = features.get('post_comments_count', 0)
                            node_feat.average_post_comments = features.get('average_post_comments', 0.0)
                            node_feat.post_views_count = features.get('post_views_count', 0)
                            node_feat.average_post_views = features.get('average_post_views', 0.0)
                            node_feat.post_reposts_count = features.get('post_reposts_count', 0)   # в модели поле post_reports_count
                            node_feat.average_post_reports = features.get('average_post_reposts', 0.0)
                            node_feat.groups_count = features.get('groups_count', 0)
                            node_feat.average_member = features.get('average_member', 0.0)
                        else:
                            node_feat = NodeFeatures(
                                vk_user_id=vk_user.id,
                                age=features.get('age'),
                                gender=features.get('gender', 0),
                                followers=features.get('followers', 0),
                                friends_count=features.get('friends_count', 0),
                                male_friends=features.get('male_count', 0),
                                female_friends=features.get('female_count', 0),
                                unknown_friends=features.get('unknown_count', 0),
                                photo_count=features.get('photo_count', 0),
                                photo_likes_count=features.get('photo_likes_count', 0),
                                average_photo_likes=features.get('average_photo_likes', 0.0),
                                photo_comments_count=features.get('photo_comments_count', 0),
                                average_photo_comments=features.get('average_photo_comments', 0.0),
                                photo_reposts_count=features.get('photo_reposts_count', 0),
                                average_photo_reposts=features.get('average_photo_reposts', 0.0),
                                post_count=features.get('posts_count', 0),
                                post_likes_count=features.get('post_likes_count', 0),
                                average_post_likes=features.get('average_post_likes', 0.0),
                                post_comments_count=features.get('post_comments_count', 0),
                                average_post_comments=features.get('average_post_comments', 0.0),
                                post_views_count=features.get('post_views_count', 0),
                                average_post_views=features.get('average_post_views', 0.0),
                                post_reposts_count=features.get('post_reposts_count', 0),
                                average_post_reports=features.get('average_post_reposts', 0.0),
                                groups_count=features.get('groups_count', 0),
                                average_member=features.get('average_member', 0.0)
                            )
                        db_session.add(node_feat)
                        logging.info(f"Inserted node features for vk_id {vk_id}")
                        db_session.commit()
                    except Exception as e:
                        db_session.rollback()
                        logging.error(f"Error processing node features for vk_id {vk_id}: {e}")