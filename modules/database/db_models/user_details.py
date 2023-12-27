from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class UserDetails(Base):
    __tablename__ = 'user_details'
    __table_args__ = {'schema': 'arxiv_daily'}

    idx = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    entity = Column(String)
    user_type = Column(String)
    user_type_start_ts = Column(DateTime(timezone=True))
    user_type_end_ts = Column(DateTime(timezone=True), default=datetime.max)
    platform = Column(String)
    is_banned = Column(Boolean, default=False)
    # User account details
    user_platform_id = Column(String)  # group_chat_idx if entity is GroupChat.
    user_platform_name = Column(String)
