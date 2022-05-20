"""
Tests for ibeam.src.gateway_client
"""
import os
import pytest
import random
import string
import types

from unittest import mock

from ibeam.src.gateway_client import SECRETS_SOURCE_ENV
from ibeam.src.gateway_client import SECRETS_SOURCE_FS
from ibeam.src.gateway_client import GatewayClient


@mock.patch('ibeam.src.gateway_client.input')
@mock.patch('ibeam.src.gateway_client.getpass')
def test_init_prompt(mock_input, mock_getpass):
    """
    GatewayClient.__init__ test stdout/stdin prompts for
    secrets.
    """

    # call fake_input when input and getpass are called
    def fake_input(s):
        return 'fake ' + s + 'response'
    mock_input.side_effect = fake_input
    mock_getpass.side_effect = fake_input

    # test init w/o any setup, which should write prompts to
    # stdout and should read stdin for the values
    client = GatewayClient(
        http_handler=None, inputs_handler=None, two_fa_handler=None)

    assert client.account == 'fake Account: response'
    assert client.password == 'fake Password: response'
    assert client.key == 'fake Key: response'


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
            env={
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

    for t in tests:
        # GatewayClient init variables
        account = None
        password = None
        key = None

        # generate random secret values
        for k in ibeam_fields:
            setattr(t, k, rnd())

        # setup test state based on the t.source value
        if t.source is None:
            # passing init values directly
            account = t.IBEAM_ACCOUNT
            password = t.IBEAM_PASSWORD
            key = t.IBEAM_KEY

            # noop test_setup
            def test_setup(t, lappend='', rappend=''):
                return mock.patch.dict(os.environ, {})

        elif t.source == SECRETS_SOURCE_ENV:
            # test_setup sets the source and copies the
            # secrets into the environment
            def test_setup(t, lappend='', rappend=''):
                environ = t.initial_env
                for k in ibeam_fields:
                    environ[k] = lappend + getattr(t, k) + rappend
                return mock.patch.dict(os.environ, environ)
        elif t.source == SECRETS_SOURCE_FS:
            # test_setup sets the source and copies the
            # secrets onto the filesystem, setting the
            # filepath into the environment
            def test_setup(t, lappend='', rappend=''):
                environ = t.initial_env
                for k in ibeam_fields:
                    environ[k] = os.path.join(tmpdir, k)
                    with open(environ[k], 'wt', encoding='UTF-8') as fh:
                        fh.write(lappend + getattr(t, k) + rappend)
                return mock.patch.dict(os.environ, environ)
        else:
            pytest.fail(f'unhandled test test source: {t.source}')

        # test via the GatewayClient init routine
        with test_setup(t):

            # test init which will call secret_value
            client = GatewayClient(
                http_handler=None, inputs_handler=None, two_fa_handler=None,
                account=account, password=password, key=key)

            # test the env or fs read values
            assert client.account == t.IBEAM_ACCOUNT
            assert client.password == t.IBEAM_PASSWORD
            assert client.key == t.IBEAM_KEY

        # test secret_value w/ left appended text
        if t.source is not None:
            with test_setup(t, lappend='\t'):

                # read the test values from the fs
                if t.source == SECRETS_SOURCE_FS:
                    fs_val = {}
                    for k in ibeam_fields:
                        with open(os.environ[k],
                                  mode='rt', encoding='UTF-8') as fh:
                            fs_val[k] = fh.read()

                # test secret_value
                for k in ibeam_fields:
                    val = client.secret_value(
                        name=k, lstrip='\t')

                    assert val == getattr(t, k)
                    assert not val.startswith('\t')

                    if t.source == SECRETS_SOURCE_ENV:
                        assert os.environ[k].startswith('\t')
                    elif t.source == SECRETS_SOURCE_FS:
                        assert fs_val[k].startswith('\t')

        # test secret_value w/ right appended text
        if t.source is not None:
            with test_setup(t, rappend='\t'):

                # read the test values from the fs
                if t.source == SECRETS_SOURCE_FS:
                    fs_val = {}
                    for k in ibeam_fields:
                        with open(os.environ[k],
                                  mode='rt', encoding='UTF-8') as fh:
                            fs_val[k] = fh.read()

                # test secret_value
                for k in ibeam_fields:
                    val = client.secret_value(
                        name=k, rstrip='\t')

                    assert val == getattr(t, k)
                    assert not val.endswith('\t')

                    if t.source == SECRETS_SOURCE_ENV:
                        assert os.environ[k].endswith('\t')
                    elif t.source == SECRETS_SOURCE_FS:
                        assert fs_val[k].endswith('\t')

        # test secret_value w/o any text that needs
        # stripping
        if t.source is not None:
            with test_setup(t):

                # read the test values from the fs
                if t.source == SECRETS_SOURCE_FS:
                    fs_val = {}
                    for k in ibeam_fields:
                        with open(os.environ[k],
                                  mode='rt', encoding='UTF-8') as fh:
                            fs_val[k] = fh.read()

                # test secret_value
                for k in ibeam_fields:
                    val = client.secret_value(name=k)

                    assert val == getattr(t, k)

                    if t.source == SECRETS_SOURCE_ENV:
                        assert os.environ[k] == val
                    elif t.source == SECRETS_SOURCE_FS:
                        assert fs_val[k] == val
