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


@app.route('/')
def hello_world():
    "ef2b7f81fe3d89cb25103a856c50fd91"
    return "HERE"


@app.route('/generate_report', methods=['POST'])
def generate_reports():
    data = request.json

    jobType = data.get('jobType')
    kwargs = data.get('kwargs', {})

    if jobType not in ReportTypes.__members__:
        return jsonify({'message': 'Invalid jobType'}), 400

    report_type = ReportTypes[jobType]

    for arg_name in report_type.mandatory_arg_names:
        if arg_name not in kwargs:
            return jsonify({'message': f'Missing mandatory argument: {arg_name}'}), 400

    id = jobType + "_" + md5_hash(json.dumps(kwargs, ensure_ascii=False))

    schedule.add_job(func=report_type.run_func, kwargs=kwargs, id=id)
    return jsonify({'message': 'Job added successfully'})


@app.route('/all_supported_reports', methods=['POST'])
def get_all_reports():
    pass


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


if __name__ == '__main__':
    app.run("0.0.0.0", port=62620)  # 再启动Flask服务
