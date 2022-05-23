import os
from ibeam.src import var

def get_path_under_outputs_dir(filename: str):
    return os.path.abspath(os.path.join(os.path.abspath(var.OUTPUTS_DIR), filename))

SQLITE_DB_PATH = os.environ.get('IBEAM_SQLITE_DB_PATH',
                                get_path_under_outputs_dir('ibeam.db'))
"""Path to the sqlite db file."""

PROXY_SERVER_HTTP = os.environ.get('IBEAM_PROXY_SERVER_HTTP', '0.0.0.0:8080')
"""Http endpoint to the proxy server."""

PROXY_SERVER_LOG_PATH = os.environ.get('IBEAM_PROXY_SERVER_LOG_PATH',
                                       get_path_under_outputs_dir('proxy_server.log'))
"""Path to the proxy server log."""

PROXY_SERVER_PIDFILE_PATH = os.environ.get('IBEAM_PROXY_SERVER_PIDFILE_PATH',
                                           get_path_under_outputs_dir('proxy_server.pid'))
"""Path to the proxy server pidfile."""

MAINTENANCE_PIDFILE_PATH = os.environ.get('IBEAM_MAINTENANCE_PIDFILE_PATH',
                                          get_path_under_outputs_dir('maintenance.pid'))
"""Path to the maintenance pidfile."""
