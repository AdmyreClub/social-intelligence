from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Strategy(Base):
    __tablename__ = 'strategies'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    lists = relationship('List', back_populates='strategy')

class List(Base):
    __tablename__ = 'lists'
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    name = Column(String(255), nullable=False)
    profiles = relationship('Profile', back_populates='list')

class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)  # Auto-incrementing primary key for the database
    ig_pk = Column(String(255), nullable=False, unique=True)  # Instagram 'pk' stored as 'ig_pk'
    username = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=True)
    is_private = Column(Boolean, default=False)
    profile_pic_url = Column(String(255), nullable=True)
    profile_pic_url_hd = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    media_count = Column(Integer)
    follower_count = Column(Integer)
    following_count = Column(Integer)
    biography = Column(Text)
    external_url = Column(String(255), nullable=True)
    account_type = Column(Integer)
    is_business = Column(Boolean, default=False)
    public_email = Column(String(255), nullable=True)
    contact_phone_number = Column(String(255), nullable=True)
    public_phone_country_code = Column(String(50), nullable=True)
    business_contact_method = Column(String(50), nullable=True)
    business_category_name = Column(String(255), nullable=True)
    category_name = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    creation_date = Column(DateTime)  # Assuming 'date' from JSON can be converted to DateTime
    former_usernames = Column(Text)
    verified_date = Column(DateTime, nullable=True)  # Assuming this might be present and in DateTime format

    def __repr__(self):
        return f"<Profile(username='{self.username}', full_name='{self.full_name}', is_verified={self.is_verified})>"

class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id'), nullable=False)
    media_url = Column(String(255), nullable=False)
    media_type = Column(String(50), nullable=False)  # 'image', 'video', etc.
    caption = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=False)
    profile = relationship('Profile', back_populates='media')

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey('media.id'), nullable=False)
    text = Column(Text, nullable=False)
    commenter_id = Column(Integer, nullable=False)
    posted_at = Column(DateTime, nullable=False)
    media = relationship('Media', back_populates='comments')

Media.comments = relationship('Comment', order_by=Comment.id, back_populates='media')
