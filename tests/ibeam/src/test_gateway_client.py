"""
Tests for ibeam.src.gateway_client
"""
import ibeam.src.var
import os
import pytest
import random
import socket
import string
import types

from contextlib import closing

from unittest import mock

from ibeam.src.gateway_client import SECRETS_SOURCE_ENV
from ibeam.src.gateway_client import SECRETS_SOURCE_FS
from ibeam.src.gateway_client import GatewayClient


def next_free_port(host='127.0.0.1'):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((host, 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


@mock.patch('ibeam.src.gateway_client.input')
@mock.patch('ibeam.src.gateway_client.getpass')
def test_init_prompt(mock_input, mock_getpass):
    """
    GatewayClient.__init__ test stdout/stdin prompts for
    secrets.
    """

    # record os.environ for later restoration
    restore_env = dict(os.environ)

    try:
        # clear os.environ for testing, restore at the end
        os.environ.clear()

        # call fake_input when input and getpass are called
        def fake_input(s):
            return 'fake ' + s + 'response'
        mock_input.side_effect = fake_input
        mock_getpass.side_effect = fake_input

        # test init w/o any setup, which should write prompts to
        # stdout and should read stdin for the values
        ibeam.src.var.IBEAM_HEALTH_SERVER_PORT = next_free_port()

        client = GatewayClient(
            http_handler=None, inputs_handler=None, two_fa_handler=None)

        try:
            assert client.account == 'fake Account: response'
            assert client.password == 'fake Password: response'
            assert client.key == 'fake Key: response'
        finally:
            client.kill()
    finally:
        os.environ.update(restore_env)

def test_secret_value(tmpdir):
    """
    GatewayClient.secret_value tests both via init and when
    directly called
    """

    # rnd generates a random value w/o any control
    # characters
    def rnd(n=16):
        c = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(c) for i in range(n))

    # basic tests to run include specifying the secrets
    # directly, reading them from the environment, and
    # reading them from the filesystem
    tests = [
        types.SimpleNamespace(
            name='passed values',
            source=None,
            initial_env={
            },
        ),
        types.SimpleNamespace(
            name='env values w/o IBEAM_SECRETS_SOURCE',
            source=SECRETS_SOURCE_ENV,
            initial_env={
            },
        ),
        types.SimpleNamespace(
            name='env values w/ IBEAM_SECRETS_SOURCE',
            source=SECRETS_SOURCE_ENV,
            initial_env={
                'IBEAM_SECRETS_SOURCE': SECRETS_SOURCE_ENV,
            },
        ),
        types.SimpleNamespace(
            name='fs values w/ IBEAM_SECRETS_SOURCE',
            source=SECRETS_SOURCE_FS,
            initial_env={
                'IBEAM_SECRETS_SOURCE': SECRETS_SOURCE_FS,
            },
        ),
    ]

    # names of the secret values
    ibeam_fields = [
        'IBEAM_ACCOUNT',
        'IBEAM_PASSWORD',
        'IBEAM_KEY',
    ]

    for test in tests:
        # GatewayClient init variables
        account = None
        password = None
        key = None

        # generate random secret values
        for field in ibeam_fields:
            setattr(test, field, rnd())

        # setup test state based on the test.source value
        if test.source is None:
            # passing init values directly
            account = test.IBEAM_ACCOUNT
            password = test.IBEAM_PASSWORD
            key = test.IBEAM_KEY

            # noop test_setup
            def test_setup(test, lappend='', rappend=''):
                return mock.patch.dict(os.environ, {})

        elif test.source == SECRETS_SOURCE_ENV:
            # test_setup sets the source and copies the
            # secrets into the environment
            def test_setup(test, lappend='', rappend=''):
                environ = test.initial_env
                for field in ibeam_fields:
                    environ[field] = lappend + getattr(test, field) + rappend
                return mock.patch.dict(os.environ, environ)
        elif test.source == SECRETS_SOURCE_FS:
            # test_setup sets the source and copies the
            # secrets onto the filesystem, setting the
            # filepath into the environment
            def test_setup(test, lappend='', rappend=''):
                environ = test.initial_env
                for field in ibeam_fields:
                    environ[field] = os.path.join(tmpdir, field)
                    with open(environ[field], 'wt', encoding='UTF-8') as fh:
                        fh.write(lappend + getattr(test, field) + rappend)
                return mock.patch.dict(os.environ, environ)
        else:
            pytest.fail(f'unhandled test test source: {test.source}')

        # test via the GatewayClient init routine
        with test_setup(test):

            # test init which will call secret_value
            ibeam.src.var.IBEAM_HEALTH_SERVER_PORT = next_free_port()

            client = GatewayClient(
                http_handler=None, inputs_handler=None, two_fa_handler=None,
                account=account, password=password, key=key)

            try:
                # test the env or fs read values
                assert client.account == test.IBEAM_ACCOUNT
                assert client.password == test.IBEAM_PASSWORD
                assert client.key == test.IBEAM_KEY

                # test secret_value w/ left appended text
                if test.source is not None:
                    with test_setup(test, lappend='\t'):

                        # read the test values from the fs
                        if test.source == SECRETS_SOURCE_FS:
                            fs_val = {}
                            for field in ibeam_fields:
                                with open(os.environ[field],
                                          mode='rt', encoding='UTF-8') as fh:
                                    fs_val[field] = fh.read()

                        # test secret_value
                        for field in ibeam_fields:
                            val = client.secret_value(
                                name=field, lstrip='\t')

                            assert val == getattr(test, field)
                            assert not val.startswith('\t')

                            if test.source == SECRETS_SOURCE_ENV:
                                assert os.environ[field].startswith('\t')
                            elif test.source == SECRETS_SOURCE_FS:
                                assert fs_val[field].startswith('\t')

                # test secret_value w/ right appended text
                if test.source is not None:
                    with test_setup(test, rappend='\t'):

                        # read the test values from the fs
                        if test.source == SECRETS_SOURCE_FS:
                            fs_val = {}
                            for field in ibeam_fields:
                                with open(os.environ[field],
                                          mode='rt', encoding='UTF-8') as fh:
                                    fs_val[field] = fh.read()

                        # test secret_value
                        for field in ibeam_fields:
                            val = client.secret_value(
                                name=field, rstrip='\t')

                            assert val == getattr(test, field)
                            assert not val.endswith('\t')

                            if test.source == SECRETS_SOURCE_ENV:
                                assert os.environ[field].endswith('\t')
                            elif test.source == SECRETS_SOURCE_FS:
                                assert fs_val[field].endswith('\t')

                # test secret_value w/o any text that needs
                # stripping
                if test.source is not None:
                    with test_setup(test):

                        # read the test values from the fs
                        if test.source == SECRETS_SOURCE_FS:
                            fs_val = {}
                            for field in ibeam_fields:
                                with open(os.environ[field],
                                          mode='rt', encoding='UTF-8') as fh:
                                    fs_val[field] = fh.read()

                        # test secret_value
                        for field in ibeam_fields:
                            val = client.secret_value(name=field)

                            assert val == getattr(test, field)

                            if test.source == SECRETS_SOURCE_ENV:
                                assert os.environ[field] == val
                            elif test.source == SECRETS_SOURCE_FS:
                                assert fs_val[field] == val

            finally:
                client.kill()
