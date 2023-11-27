from modules.models.database import SingletonDatabase
from modules.database.db_models import PaperSummaryResults
from loguru import logger
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import exists
from sqlalchemy.sql import func


class RawDataStorage(SingletonDatabase):
    """
    Inheriting from SingletonDatabase.
    """

    def __init__(self, db_config_path: Path):
        super().__init__(db_config_path)

    @staticmethod
    def _entry_exists(session, entry_id):
        return session.query(exists().where(PaperSummaryResults.entry_id == entry_id)).scalar()

    def upload_paper_raw_data(self, entry_id, title, summary, primary_category, publish_time):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                logger.info(f"{entry_id} already exists")
                # Update existing entry
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "title": title,
                    "summary": summary,
                    "primary_category": primary_category,
                    "publish_time": publish_time,
                    "last_modified_at": func.now()
                })
            else:
                logger.info(f"{entry_id} not yet exists")
                # Insert new entry
                new_entry = PaperSummaryResults(
                    entry_id=entry_id,
                    title=title,
                    summary=summary,
                    primary_category=primary_category,
                    publish_time=publish_time
                )
                session.add(new_entry)
                session.commit()

    def upload_step1_brief_summary(self, entry_id, step1_brief_summary):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "step1_brief_summary": step1_brief_summary,
                    "last_modified_at": func.now()
                })
                session.commit()

    def upload_step2_method_summary(self, entry_id, step2_method_summary):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "step2_method_summary": step2_method_summary,
                    "last_modified_at": func.now()
                })
                session.commit()

    def upload_step3_whole_paper_summary(self, entry_id, step3_whole_paper_summary):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "step3_whole_paper_summary": step3_whole_paper_summary,
                    "last_modified_at": func.now()
                })
                session.commit()

    def upload_whole_summary_chinese(self, entry_id, whole_summary_chinese):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "whole_summary_chinese": whole_summary_chinese,
                    "last_modified_at": func.now()
                })
                session.commit()

    def upload_innovative_type(self, entry_id, innovation_type):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "innovation_type": innovation_type,
                    "last_modified_at": func.now()
                })
                session.commit()

    def upload_chinese_title(self, entry_id, chinese_title):
        with self.session as session:
            if self._entry_exists(session, entry_id):
                session.query(PaperSummaryResults).filter_by(entry_id=entry_id).update({
                    "chinese_title": chinese_title,
                    "last_modified_at": func.now()
                })
                session.commit()
