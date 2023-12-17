import hashlib

from flask import Flask, jsonify, request, abort
import os
from loguru import logger

os.environ['FLAGS_eager_delete_tensor_gb'] = "0.0"
app = Flask(__name__)


@app.route('/')
def hello_world():
    "ef2b7f81fe3d89cb25103a856c50fd91"
    return "HERE"


@app.route('/validate', methods=['GET'])
def validate():
    signature = request.args.get("signature")
    timestamp = request.args.get("timestamp")
    nonce = request.args.get("nonce")
    token = '833020fan'  # 替换为你的令牌

    tmpArr = [token, timestamp, nonce]
    tmpArr.sort()
    tmpStr = ''.join(tmpArr)
    tmpStr = hashlib.sha1(tmpStr.encode()).hexdigest()

    if tmpStr == signature:
        return request.args.get('echostr', 'HERE')
    else:
        return 'Invalid signature'


if __name__ == '__main__':
    app.run("0.0.0.0", port=62620)
