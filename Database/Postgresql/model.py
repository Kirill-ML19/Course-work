from sqlalchemy import Integer, ForeignKey, Float, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from Database.Postgresql.base import Base
from typing import List
from datetime import datetime



class VkUser(Base):
    __tablename__ = 'vk_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    node_features: Mapped['NodeFeatures'] = relationship(
        'NodeFeatures',
        back_populates='vk_user', 
        uselist=False,
        cascade='all, delete-orphan'
    )

    targets: Mapped['Targets'] = relationship(
        'Targets',
        back_populates='vk_user',
        uselist=False,
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_vk_users_vk_id', 'vk_id'),
    )

class NodeFeatures(Base):
    __tablename__ = 'node_features'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('vk_users.id'), unique=True, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    gender: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    friends_count: Mapped[int] = mapped_column(Integer, default=0)
    male_friends: Mapped[int] = mapped_column(Integer, default=0)  
    female_friends: Mapped[int] = mapped_column(Integer, default=0)
    unknown_friends: Mapped[int] = mapped_column(Integer, default=0)  
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    photo_likes_count: Mapped[int] = mapped_column(Integer, default=0)
    average_photo_likes: Mapped[float] = mapped_column(Float, default=0.0)
    photo_comments_count: Mapped[int] = mapped_column(Integer, default=0)
    average_photo_comments: Mapped[float] = mapped_column(Float, default=0.0)
    photo_reposts_count: Mapped[int] = mapped_column(Integer, default=0)
    average_photo_reposts: Mapped[float] = mapped_column(Float, default=0.0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    post_likes_count: Mapped[int] = mapped_column(Integer, default=0)
    average_post_likes: Mapped[float] = mapped_column(Float, default=0.0)
    post_comments_count: Mapped[int] = mapped_column(Integer, default=0)
    average_post_comments: Mapped[float] = mapped_column(Float, default=0.0)
    post_views_count: Mapped[int] = mapped_column(Integer, default=0)
    average_post_views: Mapped[float] = mapped_column(Float, default=0.0)
    post_reposts_count: Mapped[int] = mapped_column(Integer, default=0)
    average_post_reports: Mapped[float] = mapped_column(Float, default=0.0)
    groups_count: Mapped[int] = mapped_column(Integer, default=0)
    average_member: Mapped[float] = mapped_column(Float, default=0.0)

    vk_user: Mapped['VkUser'] = relationship('VkUser', back_populates='node_features')

    __table_args__ = (
        Index('idx_node_features_vk_user_id', 'vk_user_id'),
    )

class Targets(Base):
    __tablename__ = 'targets'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('vk_users.id', ondelete='CASCADE'), unique=True, nullable=False)
    Extraversion: Mapped[float] = mapped_column(Float, default=0)
    Agreeableness: Mapped[float] = mapped_column(Float, default=0)
    Conscientiousness: Mapped[float] = mapped_column(Float, default=0)
    Neuroticism: Mapped[float] = mapped_column(Float, default=0)
    Openness: Mapped[float] = mapped_column(Float, default=0)

    vk_user: Mapped['VkUser'] = relationship('VkUser', back_populates='targets')

class RawDate(Base):
    __tablename__ = 'raw_date'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int] = mapped_column(Integer, nullable=False)
    Completion_date: Mapped[datetime] = mapped_column(DateTime)
    Extraversion: Mapped[float] = mapped_column(Float, default=0)
    Agreeableness: Mapped[float] = mapped_column(Float, default=0)
    Conscientiousness: Mapped[float] = mapped_column(Float, default=0)
    Neuroticism: Mapped[float] = mapped_column(Float, default=0)
    Openness: Mapped[float] = mapped_column(Float, default=0)

