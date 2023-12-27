from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ReportDetails(Base):
    __tablename__ = 'report_details'
    __table_args__ = {'schema': 'arxiv_daily'}

    idx = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    local_storage_path = Column(String)
    report_name = Column(String)
    report_type = Column(String)
    topic = Column(String)
    report_info = Column(String)
    is_removed = Column(Boolean, default=False)
