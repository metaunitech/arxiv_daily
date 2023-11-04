from flask import Flask, jsonify, request, abort
import os

os.environ['FLAGS_eager_delete_tensor_gb'] = "0.0"
app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run("0.0.0.0", port=62620)
