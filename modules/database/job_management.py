from modules.models.database import SingletonDatabase
from modules.database.db_models import JobRecord
from pathlib import Path


class JobRecordException(Exception):
    pass


class JobRecordManagement(SingletonDatabase):
    """
        Inheriting from SingletonDatabase.
        """

    def __init__(self, db_config_path: Path):
        super().__init__(db_config_path)

    def add_job(self, report_name, report_type, report_func_name, report_kwargs):
        with self.session as session:
            job = JobRecord(
                job_status='ADDED',
                report_type=report_type,
                report_func=report_func_name,
                report_kwargs=report_kwargs,
                report_name=report_name
            )
            session.add(job)
            session.commit()
        return job.idx

    def update_job_status(self, job_idx, status):
        with self.session as session:
            job = session.query(JobRecord).filter_by(idx=job_idx).first()
            if job:
                job.job_status = status
                session.commit()
            else:
                raise JobRecordException(f"JobRecord with idx={job_idx} not found.")

    def search_job(self, report_type, report_func_name, report_kwargs):
        with self.session as session:
            job = session.query(JobRecord.idx).filter_by(
                report_type=report_type,
                report_func=report_func_name,
                report_kwargs=report_kwargs
            ).first()
            if job:
                return job.idx
            else:
                return None

    def set_job_finish(self, job_idx, report_idx=None):
        with self.session as session:
            job = session.query(JobRecord).filter_by(idx=job_idx).first()
            if job:
                job.job_status = 'FINISHED'
                job.report_idx = report_idx
                session.commit()
            else:
                raise JobRecordException(f"JobRecord with idx={job_idx} not found.")
