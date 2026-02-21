"""
Tests for the COUNT_TIMEOUT_AS_FAILED feature in ibeam.src.handlers.login_handler.LoginHandler.

Covers GitHub issue #274: login timeouts were not counted toward IBEAM_MAX_FAILED_AUTH.
"""

import unittest
from unittest import mock

from selenium.common import TimeoutException

from ibeam.src.handlers.login_handler import AttemptException, LoginHandler


def make_login_handler(count_timeout_as_failed=True, max_failed_auth=3):
    """
    Build a LoginHandler with all heavy dependencies mocked out.
    Only the fields relevant to timeout-counting logic are set to real values.
    """
    handler = LoginHandler.__new__(LoginHandler)

    # Minimal attribute setup matching __init__ assignments
    handler.secrets_handler = mock.MagicMock()
    handler.two_fa_handler = mock.MagicMock()
    handler.driver_factory = mock.MagicMock()
    handler.targets = mock.MagicMock()

    handler.base_url = 'https://localhost:5000'
    handler.route_auth = '/sso/Login'
    handler.two_fa_select_target = None
    handler.strict_two_fa_code = False
    handler.max_immediate_attempts = 1
    handler.oauth_timeout = 30
    handler.max_presubmit_buffer = 30
    handler.min_presubmit_buffer = 0
    handler.max_failed_auth = max_failed_auth
    handler.outputs_dir = '/tmp'
    handler.use_paper_account = False
    handler.count_timeout_as_failed = count_timeout_as_failed

    handler.failed_attempts = 0
    handler.presubmit_buffer = handler.min_presubmit_buffer

    return handler


def call_handle_timeout_exception(handler):
    """
    Call handle_timeout_exception() with all Selenium side-effects mocked away.
    Returns whatever the method returns (normally None), or re-raises AttemptException.
    """
    fake_exception = TimeoutException('test timeout')
    fake_driver = mock.MagicMock()
    fake_targets = mock.MagicMock()

    with mock.patch('ibeam.src.handlers.login_handler.EC') as mock_ec, \
         mock.patch('ibeam.src.handlers.login_handler.WebDriverWait') as mock_wait, \
         mock.patch('ibeam.src.handlers.login_handler.save_screenshot') as mock_screenshot, \
         mock.patch('ibeam.src.handlers.login_handler.exception_to_string', return_value=''):

        # Simulate the page-load check succeeding (page_loaded_correctly = True)
        mock_wait.return_value.until.return_value = mock.MagicMock()

        return handler.handle_timeout_exception(
            fake_exception,
            fake_targets,
            fake_driver,
            website_version=2,
            route_auth=handler.route_auth,
            base_url=handler.base_url,
            outputs_dir=handler.outputs_dir,
        )


class TestTimeoutCountingEnabled(unittest.TestCase):
    """Tests for count_timeout_as_failed=True (the default)."""

    def test_timeout_counts_as_failed_when_enabled(self):
        """
        When count_timeout_as_failed=True, a TimeoutException during login
        increments failed_attempts.
        """
        handler = make_login_handler(count_timeout_as_failed=True, max_failed_auth=3)
        self.assertEqual(handler.failed_attempts, 0)

        call_handle_timeout_exception(handler)

        self.assertEqual(handler.failed_attempts, 1)

    def test_timeout_does_not_count_as_failed_when_disabled(self):
        """
        When count_timeout_as_failed=False, a TimeoutException does NOT
        increment failed_attempts.
        """
        handler = make_login_handler(count_timeout_as_failed=False, max_failed_auth=3)
        self.assertEqual(handler.failed_attempts, 0)

        call_handle_timeout_exception(handler)

        self.assertEqual(handler.failed_attempts, 0)

    def test_timeout_triggers_shutdown_at_max_failed_auth(self):
        """
        When count_timeout_as_failed=True and failed_attempts reaches
        max_failed_auth, handle_timeout_exception raises AttemptException
        with cause='shutdown'.
        """
        handler = make_login_handler(count_timeout_as_failed=True, max_failed_auth=3)
        handler.failed_attempts = 2  # one more timeout should hit the limit

        with self.assertRaises(AttemptException) as ctx:
            call_handle_timeout_exception(handler)

        self.assertEqual(ctx.exception.cause, 'shutdown')
        self.assertEqual(handler.failed_attempts, 3)

    def test_timeout_does_not_trigger_shutdown_when_disabled(self):
        """
        When count_timeout_as_failed=False, even many timeouts do NOT
        trigger shutdown (no AttemptException is raised).
        """
        handler = make_login_handler(count_timeout_as_failed=False, max_failed_auth=3)

        # Simulate more timeouts than max_failed_auth
        for _ in range(5):
            call_handle_timeout_exception(handler)  # must not raise

        self.assertEqual(handler.failed_attempts, 0)

    def test_failed_attempts_resets_on_success(self):
        """
        After timeouts increment failed_attempts, a successful login
        (step_success) resets failed_attempts to 0.
        """
        handler = make_login_handler(count_timeout_as_failed=True, max_failed_auth=5)

        # Simulate two timeouts
        call_handle_timeout_exception(handler)
        call_handle_timeout_exception(handler)
        self.assertEqual(handler.failed_attempts, 2)

        # step_success resets the counter (and raises AttemptException cause='success')
        with self.assertRaises(AttemptException) as ctx:
            handler.step_success()

        self.assertEqual(ctx.exception.cause, 'success')
        self.assertEqual(handler.failed_attempts, 0)

    def test_timeout_counting_disabled_when_max_failed_auth_zero(self):
        """
        When max_failed_auth=0, timeouts do NOT increment failed_attempts
        even if count_timeout_as_failed=True, because max_failed_auth=0
        means the feature is disabled.
        """
        handler = make_login_handler(count_timeout_as_failed=True, max_failed_auth=0)

        call_handle_timeout_exception(handler)

        self.assertEqual(handler.failed_attempts, 0)


class TestTimeoutCountingViaLogin(unittest.TestCase):
    """
    Integration-style tests that exercise the full login() flow by mocking
    start_up_browser, load_page, and attempt so that a TimeoutException
    propagates to the outer except block in login().
    """

    def _make_login_handler_for_login_flow(self, count_timeout_as_failed=True, max_failed_auth=3):
        handler = make_login_handler(
            count_timeout_as_failed=count_timeout_as_failed,
            max_failed_auth=max_failed_auth,
        )
        return handler

    def test_login_raises_attempt_exception_shutdown_when_timeout_hits_max(self):
        """
        When count_timeout_as_failed=True and a TimeoutException is raised
        during login() and failed_attempts reaches max_failed_auth,
        handle_timeout_exception raises AttemptException(cause='shutdown')
        which is re-raised out of login() (lines 516-517 of login_handler.py).
        """
        handler = self._make_login_handler_for_login_flow(
            count_timeout_as_failed=True, max_failed_auth=1
        )

        fake_driver = mock.MagicMock()
        fake_display = mock.MagicMock()

        with mock.patch('ibeam.src.handlers.login_handler.start_up_browser',
                        return_value=(fake_driver, fake_display)), \
             mock.patch('ibeam.src.handlers.login_handler.shut_down_browser'), \
             mock.patch.object(handler, 'load_page',
                               side_effect=TimeoutException('outer timeout')), \
             mock.patch('ibeam.src.handlers.login_handler.EC'), \
             mock.patch('ibeam.src.handlers.login_handler.WebDriverWait') as mock_wait, \
             mock.patch('ibeam.src.handlers.login_handler.save_screenshot'), \
             mock.patch('ibeam.src.handlers.login_handler.exception_to_string',
                        return_value=''):

            # Simulate page-load check succeeding inside handle_timeout_exception
            mock_wait.return_value.until.return_value = mock.MagicMock()

            # AttemptException(cause='shutdown') is re-raised out of login()
            # when the timeout counter reaches max_failed_auth
            with self.assertRaises(AttemptException) as ctx:
                handler.login()

        self.assertEqual(ctx.exception.cause, 'shutdown')
        self.assertEqual(handler.failed_attempts, 1)

    def test_login_returns_shutdown_false_when_timeout_below_max(self):
        """
        When count_timeout_as_failed=True but failed_attempts has not yet
        reached max_failed_auth, login() returns (False, False).
        """
        handler = self._make_login_handler_for_login_flow(
            count_timeout_as_failed=True, max_failed_auth=5
        )

        fake_driver = mock.MagicMock()
        fake_display = mock.MagicMock()

        with mock.patch('ibeam.src.handlers.login_handler.start_up_browser',
                        return_value=(fake_driver, fake_display)), \
             mock.patch('ibeam.src.handlers.login_handler.shut_down_browser'), \
             mock.patch.object(handler, 'load_page',
                               side_effect=TimeoutException('outer timeout')), \
             mock.patch('ibeam.src.handlers.login_handler.EC'), \
             mock.patch('ibeam.src.handlers.login_handler.WebDriverWait') as mock_wait, \
             mock.patch('ibeam.src.handlers.login_handler.save_screenshot'), \
             mock.patch('ibeam.src.handlers.login_handler.exception_to_string',
                        return_value=''):

            mock_wait.return_value.until.return_value = mock.MagicMock()

            success, shutdown = handler.login()

        self.assertFalse(success)
        self.assertFalse(shutdown)
        self.assertEqual(handler.failed_attempts, 1)


if __name__ == '__main__':
    unittest.main()
