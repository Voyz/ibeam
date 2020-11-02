import os
from pathlib import Path

from invoke import task

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


def _copy_directory(from_path, to_path, c):
    c.run(f'robocopy {from_path} {to_path} /MIR /np /nfl /njh /njs /ndl /nc /ns /XD {from_path}/.git')


@task
def copyPackages(c):
    copy_clientportal(c)
    copy_chrome_driver(c)


@task
def copy_clientportal(c):
    source_path = os.environ['IBEAM_GATEWAY_DIR']

    if not os.path.exists(source_path):
        raise RuntimeError(f'IBEAM_GATEWAY_DIR module not found: {source_path}')

    _copy_directory(source_path, os.path.join(PROJECT_ROOT, 'copy_cache/clientportal.gw'), c)


@task
def copy_chrome_driver(c):
    source_path = Path(os.environ['IBEAM_CHROME_DRIVER_PATH']).parent
    print(source_path)

    if not os.path.exists(source_path):
        raise RuntimeError(f'IBEAM_CHROME_DRIVER_PATH module not found: {source_path}')

    _copy_directory(source_path, os.path.join(PROJECT_ROOT, 'copy_cache/chrome_driver'), c)


@task
def copySourcesToDocker(c):
    c.run(f'docker cp {os.path.join(PROJECT_ROOT, "ibeam")} ibeam:/srv', hide='out')
