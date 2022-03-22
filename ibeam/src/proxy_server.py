import json
import os
import daemon
from pidlockfile import PIDLockFile
import logging
import psutil
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy

from ibeam.src.gateway_client import GatewayClient, create_gateway_client
from ibeam.src.http_handler import HttpHandler
from ibeam.src import var, two_fa_selector
from ibeam.src.inputs_handler import InputsHandler
from ibeam.src.process_utils import start_maintenance_daemon, stop_maintenance_daemon

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

server = Flask(__name__)
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
server.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + var.SQLITE_DB_PATH
db = SQLAlchemy(server)

class User(db.Model):
    api_key = db.Column(db.String(80), primary_key=True)
    account = db.Column(db.String(80), unique=False, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)

    def __repr__(self):
        return "<User api_key: {0}, account: {1}, password: {2}>" \
                    .format(self.api_key, self.account, self.password)

def require_api_key(api_method):
    @wraps(api_method)

    def check_api_key(*args, **kwargs):
        apikey = request.headers.get('X-API-Key')
        if User.query.filter_by(api_key=apikey).count() > 0:
            return api_method(*args, **kwargs)
        else:
            return jsonify({"message": "ERROR: Unauthorized"}), 401

    return check_api_key

def get_user(request):
    apikey = request.headers.get('X-API-Key')
    user = User.query.filter_by(api_key=apikey).first()
    return user
    os.environ['IBEAM_ACCOUNT'] = user.account
    os.environ['IBEAM_PASSWORD'] = user.password

@server.route('/status', methods=['GET'])
@require_api_key
def get_ibeam_status():
    user = get_user(request)
    api_key_account = user.account
    is_gateway_running = False
    is_gateway_authenticated = False
    client = create_gateway_client(skip_account_check=True)
    is_gateway_running = client.tickle()
    status = client.get_status()
    is_gateway_authenticated = True if status[2] else False
    authenticated_account = ''
    if is_gateway_authenticated:
        userinfo = json.loads(client.user())
        authenticated_account = userinfo['username']
    if os.path.exists(var.MAINTENANCE_PIDFILE_PATH):
        m_pid = int(open(var.MAINTENANCE_PIDFILE_PATH).read())
        is_maintenance_running = True if psutil.pid_exists(m_pid) else False
    else:
        is_maintenance_running = False
    return jsonify({
           "inputs_dir": var.INPUTS_DIR,
           "gateway_dir": var.GATEWAY_DIR,
           "driver_path": var.CHROME_DRIVER_PATH,
           "api_key_account": api_key_account,
           "authenticated_account": authenticated_account,
           "is_gateway_running": is_gateway_running,
           "is_gateway_authenticated": is_gateway_authenticated,
           "is_maintenance_running": is_maintenance_running}), 200

@server.route('/init', methods=['POST'])
@require_api_key
def init_ibeam():
    user = get_user(request)
    client = create_gateway_client(account=user.account, password=user.password)
    success, _ = client.start_and_authenticate()
    if success:
        start_maintenance_daemon(user.account, user.password)
        return jsonify({"message": "OK: Gateway started, authenticated and being maintained."}), 200
    else:
        return jsonify({"message": "ERROR"}), 200

@server.route('/reset', methods=['POST'])
@require_api_key
def reset_ibeam():
    client = create_gateway_client(skip_account_check=True)
    success = client.kill()
    if success:
        stop_maintenance_daemon()
        return jsonify({"message": "OK: Gateway reset."}), 200
    else:
        return jsonify({"message": "ERROR"}), 200

@server.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@require_api_key
def forward_request(path):
    client = create_gateway_client(skip_account_check=True)
    httpresponse = client.forward_request(request)
    _LOGGER.info(httpresponse.getheaders())
    flaskresponse = Response(httpresponse.read(), 
                             status = httpresponse.status,
                             headers = httpresponse.getheaders(),
                             direct_passthrough = True)
    # When forwarding request, internally urllib does not use keep-alive but httpresponse
    # has Transfer-Encoding=chunked header which conflicts with Content-Length added in
    # flaskresponse. websocket forwarding is not supported yet.
    flaskresponse.headers['Transfer-Encoding'] = ''
    return flaskresponse
