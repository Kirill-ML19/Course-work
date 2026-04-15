from sqlalchemy import Integer, ForeignKey, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from Database.Postgresql.base import Base
from typing import List

class Client(Base):
    __tablename__ = 'clients'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    vk_users: Mapped[List['VkUser']] = relationship(
        'VkUser',
        back_populates='client',
        lazy='joined',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_client_vk_id', 'vk_id'),
    )

class VkUser(Base):
    __tablename__ = 'vk_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int] = mapped_column(Integer, nullable=False)

    client_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey('clients.id', ondelete='CASCADE'),   
        nullable=False
    )

    client: Mapped['Client'] = relationship('Client', back_populates='vk_users')
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
        Index('idx_vk_users_client_id', 'client_id'),
        UniqueConstraint('client_id', 'vk_id', name='uq_client_vk'),
    )

class NodeFeatures(Base):
    __tablename__ = 'node_features'

    id: Mapped[int] = mapped_column(primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('vk_users.id'), unique=True, nullable=False)
    friends_count: Mapped[int] = mapped_column(Integer, default=0)
    male_friends: Mapped[int] = mapped_column(Integer, default=0)  
    female_friends: Mapped[int] = mapped_column(Integer, default=0)
    unknown_friends: Mapped[int] = mapped_column(Integer, default=0)  
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    likes_total: Mapped[int] = mapped_column(Integer, default=0)
    average_likes: Mapped[float] = mapped_column(Float, default=0.0)
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