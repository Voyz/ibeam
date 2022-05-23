import os
import sys
from pathlib import Path

_this_filedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, str(Path(_this_filedir).parent.parent))

from ibeam_proxy_server.src.proxy_server import db, User
from getpass import getpass
import secrets
import logging

_LOGGER = logging.getLogger('ibeam')

if __name__ == "__main__":
    db.create_all()
    action = input('Add Account(A), Delete Account(D), Show Accounts(S)\n')
    if action == 'A':
        account = input('Enter IBKR account: ')
        password = getpass('Enter IBKR password: ')
        api_key = secrets.token_hex(40)
        new_user = User(api_key=api_key, account=account, password=password)
        db.session.add(new_user)
        db.session.commit()
        print(f'Registered new IBKR account and X-API-Key:{api_key}')
    elif action == 'D':
        account = input('Enter IBKR account: ')
        users = User.query.filter_by(account=account).all()
        print(f'Found {len(users)} records for IBKR account {account}')
        for user in users:
            db.session.delete(user)
        db.session.commit()
        print(f'Deleted X-API-Key and password for IBKR account {account}')
    elif action == 'S':
        users = User.query.all()
        for user in users:
            print(user)