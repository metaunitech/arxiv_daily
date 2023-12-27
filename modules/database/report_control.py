from modules.models.database import SingletonDatabase
from modules.database.db_models import UserDetails, ReportDetails, ReportHistory
from loguru import logger
from sqlalchemy.sql import func
from pathlib import Path
from datetime import datetime, timedelta


class ReportControlException(Exception):
    pass


class ReportControl(SingletonDatabase):
    """
    Inheriting from SingletonDatabase.
    """

    def __init__(self, db_config_path: Path):
        super().__init__(db_config_path)

    def register_report(self, report_name, local_storage_path: Path, report_type, topic, report_info):
        try:
            with self.session as session:
                report = ReportDetails(
                    local_storage_path=local_storage_path.absolute(),
                    report_name=report_name,
                    report_type=report_type,
                    topic=topic,
                    report_info=report_info
                )
                session.add(report)
                session.commit()
        except Exception as e:
            raise ReportControlException(f"Failed to register report: {str(e)}")

    def remove_report(self, report_idx):
        try:
            with self.session as session:
                report = session.query(ReportDetails).get(report_idx)
                if report:
                    report.is_removed = True
                    session.commit()
                else:
                    raise ReportControlException(f"Report with idx={report_idx} does not exist.")
        except Exception as e:
            raise ReportControlException(f"Failed to remove report: {str(e)}")

    def search_report(self, creation_date=None, topic=None, report_type=None, is_deleted=False):
        try:
            with self.session as session:
                query = session.query(ReportDetails)
                if creation_date:
                    query = query.filter(func.date_trunc('day', ReportDetails.created_at) == creation_date.date())
                if topic:
                    query = query.filter(ReportDetails.topic == topic)
                if report_type:
                    query = query.filter(ReportDetails.report_type == report_type)
                if is_deleted:
                    query = query.filter(ReportDetails.is_removed == is_deleted)
                reports = query.all()
                return [report.__dict__ for report in reports]
        except Exception as e:
            raise ReportControlException(f"Failed to search reports: {str(e)}")

    def send_report_to_user(self, report_idx, to_user_id, platform, from_user_id):
        try:
            with self.session as session:
                user_details = session.query(UserDetails).filter_by(user_platform_id=to_user_id,
                                                                    platform=platform).first()
                if user_details:
                    report_action = ReportHistory(
                        report_idx=report_idx,
                        from_entity_idx='',  # Add appropriate values here
                        from_entity_type='',  # Add appropriate values here
                        to_entity_idx=to_user_id,
                        to_entity_type=user_details.entity,
                        action='send',
                        platform=platform,
                        action_finished_ts=datetime.now()
                    )
                    session.add(report_action)
                    session.commit()
                else:
                    raise ReportControlException(
                        f"User details with user_platform_id={report_idx} and platform={platform} do not exist.")
        except Exception as e:
            raise ReportControlException(f"Failed to send report to user: {str(e)}")

    def send_report_to_group_chat(self, report_idx, to_group_chat_idx, platform, from_user_id):
        try:
            with self.session as session:
                # Retrieve to_entity_idx from UserDetails table
                user_details = session.query(UserDetails).filter_by(user_platform_id=to_group_chat_idx,
                                                                    platform=platform).first()
                if user_details:
                    # Perform actions to send report to group chat
                    report_action = ReportHistory(
                        report_idx=report_idx,
                        from_entity_idx='',  # Add appropriate values here
                        from_entity_type='',  # Add appropriate values here
                        to_entity_idx=user_details.idx,
                        to_entity_type=user_details.entity,
                        action='send',
                        platform=platform,
                        action_finished_ts=datetime.now()
                    )
                    session.add(report_action)
                    session.commit()
                else:
                    raise ReportControlException(
                        f"User details with user_platform_id={to_group_chat_idx} and platform={platform} do not exist.")

        except Exception as e:
            raise ReportControlException(f"Failed to send report to group chat: {str(e)}")
