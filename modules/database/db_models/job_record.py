from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class JobRecord(Base):
    __tablename__ = 'job_record'
    __table_args__ = {'schema': 'arxiv_daily'}

    idx = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_modified_ts = Column(DateTime(timezone=True), onupdate=func.now())
    job_status = Column(String)
    report_type = Column(String)
    report_func = Column(String)
    report_kwargs = Column(String)
    report_name = Column(String)
    report_idx = Column(Integer)
