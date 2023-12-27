from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserHistory(Base):
    __tablename__ = 'user_history'
    __table_args__ = {'schema': 'arxiv_daily'}

    idx = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_modified_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Action related
    from_entity_idx = Column(String)
    from_entity_type = Column(String)
    to_entity_idx = Column(String)
    to_entity_type = Column(String)
    action = Column(String)
    action_init_ts = Column(DateTime(timezone=True), server_default=func.now())
    action_finished_ts = Column(DateTime(timezone=True))
    action_kwargs = Column(String)
    action_status = Column(String)
