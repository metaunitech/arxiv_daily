from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class PaperSummaryResults(Base):
    __tablename__ = 'paper_summary_results'
    __table_args__ = {'schema': 'arxiv_daily'}

    idx = Column(Integer, primary_key=True, autoincrement=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_modified_at = Column(DateTime(timezone=True), onupdate=func.now())
    entry_id = Column(String)
    title = Column(String)
    chinese_title = Column(String)
    summary = Column(String)
    primary_category = Column(String)
    publish_time = Column(DateTime(timezone=True))
    step1_brief_summary = Column(String)
    step2_method_summary = Column(String)
    step3_whole_paper_summary = Column(String)
    whole_summary_chinese = Column(String)
    innovation_type = Column(String)