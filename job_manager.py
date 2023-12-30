from flask import Flask, jsonify, request
import os
from pathlib import Path
from loguru import logger
from configs import CONFIG_DATA
from main_flow import ReportTypes
from flask_apscheduler import APScheduler
# from apscheduler.schedulers.blocking import BlockingScheduler
from modules.rpa_utils.general_utils import md5_hash
from modules.database.job_management import JobRecordManagement
import json

db_config_path = CONFIG_DATA.get("DB", {}).get("config_path")
assert db_config_path, 'DB_Config is not provided in config file.'
db_config_path = Path(db_config_path)

# DB INSTANCE
JobRecordManagement_instance = JobRecordManagement(db_config_path)

os.environ['FLAGS_eager_delete_tensor_gb'] = "0.0"
app = Flask(__name__)
app.config['SCHEDULER_API_ENABLED'] = True

# Scheduler INSTANCE
schedule = APScheduler()
schedule.init_app(app)
schedule.start()


def run_func_wrapper(report_type, kwargs, id, max_retries):
    retry_count = 0
    while retry_count < max_retries:
        try:
            report_type.run_func(**kwargs)
            break  # 任务成功执行，退出循环
        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            retry_count += 1
            # 在任务执行失败时插入新任务
            retry_job_id = f"retry_{id}_attempt_{retry_count}"
            logger.info(f"Inserting retry job id: {retry_job_id}")
            schedule.add_job(func=run_func_wrapper, kwargs={'report_type': report_type, 'kwargs': kwargs, 'id': id,
                                                            'max_retries': max_retries}, id=retry_job_id,
                             max_instances=1, coalesce=False)


@app.route('/')
def hello_world():
    return "HERE"


@app.route('/generate_report', methods=['POST'])
def generate_reports():
    data = request.json
    jobType = data.get('jobType')
    kwargs = data.get('kwargs', {})
    job_cycle_kwargs = data.get('jobCycleKwargs', {})

    if jobType not in ReportTypes.__members__:
        return jsonify({'message': 'Invalid jobType'}), 400

    report_type = ReportTypes[jobType]

    _default_job_cycle_kwargs = report_type.default_job_cycle_kwargs
    job_cycle_kwargs = _default_job_cycle_kwargs if not job_cycle_kwargs else job_cycle_kwargs

    for arg_name in report_type.mandatory_arg_names:
        if arg_name not in kwargs:
            return jsonify({'message': f'Missing mandatory argument: {arg_name}'}), 400

    id = jobType + "_" + md5_hash(json.dumps(kwargs, ensure_ascii=False))
    logger.info(f"Starts to add job id: {id}. KWARGS: {json.dumps(kwargs, ensure_ascii=False, indent=2)}")
    # schedule.add_job(func=report_type.run_func, kwargs=kwargs, id=id, **job_cycle_kwargs)
    schedule.add_job(func=run_func_wrapper,
                     kwargs={'report_type': report_type, 'kwargs': kwargs, "id": id, 'max_retries': 20}, id=id,
                     **job_cycle_kwargs,
                     max_instances=1, coalesce=False)

    return jsonify({'message': 'Job added successfully'})


@app.route('/all_supported_reports', methods=['GET'])
def get_all_reports():
    return jsonify({'job_types': dict(ReportTypes.__members__)})


@app.route('/start_job', methods=['POST'])
def run_job():
    schedule.start()
    return jsonify({'message': 'All job started.'})


@app.route('/check_current_jobs', methods=['GET'])
def check_current_jobs():
    jobs = schedule.get_jobs()
    job_list = []
    for job in jobs:
        job_info = {
            'id': job.id,
            'name': job.name,
            'func': job.func.__name__,
            'kwargs': job.kwargs,
        }
        job_list.append(job_info)

    return jsonify({'jobs': job_list})


@app.route('/remove_job', methods=['POST'])
def remove_jobs():
    data = request.json
    to_remove_ids = data.get('jobs_ids', [])
    for _id in to_remove_ids:
        schedule.remove_job(_id)
        logger.success(f'{_id} removed.')
    return jsonify({'success': to_remove_ids})


if __name__ == '__main__':
    app.run("0.0.0.0", port=6160)  # 再启动Flask服务
