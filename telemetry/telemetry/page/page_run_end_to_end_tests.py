# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import tempfile
import unittest
import shutil
import sys
import tempfile

from telemetry import benchmark
from telemetry import decorators
from telemetry.core import browser_finder
from telemetry.core import exceptions
from telemetry.core import user_agent
from telemetry.core import util
from telemetry.page import page as page_module
from telemetry.page import page_set
from telemetry.page import page_test
from telemetry.page import test_expectations
from telemetry.results import results_options
from telemetry.unittest_util import options_for_unittests
from telemetry.unittest_util import system_stub
from telemetry.user_story import user_story_runner
from telemetry.util import exception_formatter as exception_formatter_module
from telemetry.value import scalar
from telemetry.value import string


# pylint: disable=bad-super-call

SIMPLE_CREDENTIALS_STRING = """
{
  "test": {
    "username": "example",
    "password": "asdf"
  }
}
"""
class DummyTest(page_test.PageTest):
  def ValidatePage(self, *_):
    pass


def SetUpUserStoryRunnerArguments(options):
  parser = options.CreateParser()
  user_story_runner.AddCommandLineArgs(parser)
  options.MergeDefaultValues(parser.get_default_values())
  user_story_runner.ProcessCommandLineArgs(parser, options)

class EmptyMetadataForTest(benchmark.BenchmarkMetadata):
  def __init__(self):
    super(EmptyMetadataForTest, self).__init__('')

class StubCredentialsBackend(object):
  def __init__(self, login_return_value):
    self.did_get_login = False
    self.did_get_login_no_longer_needed = False
    self.login_return_value = login_return_value

  @property
  def credentials_type(self):
    return 'test'

  def LoginNeeded(self, *_):
    self.did_get_login = True
    return self.login_return_value

  def LoginNoLongerNeeded(self, _):
    self.did_get_login_no_longer_needed = True


def GetSuccessfulPageRuns(results):
  return [run for run in results.all_page_runs if run.ok or run.skipped]


class FakeExceptionFormatterModule(object):
  @staticmethod
  def PrintFormattedException(
      exception_class=None, exception=None, tb=None, msg=None):
    pass


# TODO: remove test cases that use real browsers and replace with a
# user_story_runner or shared_page_state unittest that tests the same logic.
class PageRunEndToEndTests(unittest.TestCase):
  # TODO(nduca): Move the basic "test failed, test succeeded" tests from
  # page_test_unittest to here.

  def setUp(self):
    self._user_story_runner_logging_stub = None

  def SuppressExceptionFormatting(self):
    user_story_runner.exception_formatter = FakeExceptionFormatterModule
    self._user_story_runner_logging_stub = system_stub.Override(
      user_story_runner, ['logging'])

  def RestoreExceptionFormatter(self):
    user_story_runner.exception_formatter = exception_formatter_module
    if self._user_story_runner_logging_stub:
      self._user_story_runner_logging_stub.Restore()
      self._user_story_runner_logging_stub = None

  def tearDown(self):
    self.RestoreExceptionFormatter()

  def testRaiseBrowserGoneExceptionFromRestartBrowserBeforeEachPage(self):
    self.SuppressExceptionFormatting()
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    ps.pages.append(page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir()))
    ps.pages.append(page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir()))

    class Test(page_test.PageTest):
      def __init__(self, *args):
        super(Test, self).__init__(*args)
        self.run_count = 0
      def RestartBrowserBeforeEachPage(self):
        old_run_count = self.run_count
        self.run_count += 1
        if old_run_count == 0:
          raise exceptions.BrowserGoneException(None)
        return self._needs_browser_restart_after_each_page

    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    test = Test()
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)
    self.assertEquals(2, test.run_count)
    self.assertEquals(1, len(GetSuccessfulPageRuns(results)))
    self.assertEquals(1, len(results.failures))

  def testHandlingOfCrashedTabWithExpectedFailure(self):
    self.SuppressExceptionFormatting()
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    expectations.Fail('chrome://crash')
    page1 = page_module.Page('chrome://crash', ps)
    ps.pages.append(page1)

    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(DummyTest(), ps, expectations, options, results)
    self.assertEquals(1, len(GetSuccessfulPageRuns(results)))
    self.assertEquals(0, len(results.failures))

  def testCredentialsWhenLoginFails(self):
    self.SuppressExceptionFormatting()
    credentials_backend = StubCredentialsBackend(login_return_value=False)
    did_run = self.runCredentialsTest(credentials_backend)
    assert credentials_backend.did_get_login == True
    assert credentials_backend.did_get_login_no_longer_needed == False
    assert did_run == False

  def testCredentialsWhenLoginSucceeds(self):
    credentials_backend = StubCredentialsBackend(login_return_value=True)
    did_run = self.runCredentialsTest(credentials_backend)
    assert credentials_backend.did_get_login == True
    assert credentials_backend.did_get_login_no_longer_needed == True
    assert did_run

  def runCredentialsTest(self, credentials_backend):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    did_run = [False]

    try:
      with tempfile.NamedTemporaryFile(delete=False) as f:
        page = page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir(),
        credentials_path=f.name)
        page.credentials = "test"
        ps.pages.append(page)

        f.write(SIMPLE_CREDENTIALS_STRING)

      class TestThatInstallsCredentialsBackend(page_test.PageTest):
        def __init__(self, credentials_backend):
          super(TestThatInstallsCredentialsBackend, self).__init__()
          self._credentials_backend = credentials_backend

        def DidStartBrowser(self, browser):
          browser.credentials.AddBackend(self._credentials_backend)

        def ValidatePage(self, *_):
          did_run[0] = True

      test = TestThatInstallsCredentialsBackend(credentials_backend)
      options = options_for_unittests.GetCopy()
      options.output_formats = ['none']
      options.suppress_gtest_report = True
      SetUpUserStoryRunnerArguments(options)
      results = results_options.CreateResults(EmptyMetadataForTest(), options)
      user_story_runner.Run(test, ps, expectations, options, results)
    finally:
      os.remove(f.name)

    return did_run[0]

  def testUserAgent(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    page = page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir())
    ps.pages.append(page)
    ps.user_agent_type = 'tablet'

    class TestUserAgent(page_test.PageTest):
      def ValidatePage(self, _1, tab, _2):
        actual_user_agent = tab.EvaluateJavaScript('window.navigator.userAgent')
        expected_user_agent = user_agent.UA_TYPE_MAPPING['tablet']
        assert actual_user_agent.strip() == expected_user_agent

        # This is so we can check later that the test actually made it into this
        # function. Previously it was timing out before even getting here, which
        # should fail, but since it skipped all the asserts, it slipped by.
        self.hasRun = True # pylint: disable=W0201

    test = TestUserAgent()
    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)

    self.assertTrue(hasattr(test, 'hasRun') and test.hasRun)

  # Ensure that user_story_runner forces exactly 1 tab before running a page.
  @decorators.Enabled('has tabs')
  def testOneTab(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    page = page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir())
    ps.pages.append(page)

    class TestOneTab(page_test.PageTest):
      def __init__(self):
        super(TestOneTab, self).__init__()
        self._browser = None

      def DidStartBrowser(self, browser):
        self._browser = browser
        self._browser.tabs.New()

      def ValidatePage(self, *_):
        assert len(self._browser.tabs) == 1

    test = TestOneTab()
    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)

  # Ensure that user_story_runner allows the test to customize the browser
  # before it launches.
  def testBrowserBeforeLaunch(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    page = page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir())
    ps.pages.append(page)

    class TestBeforeLaunch(page_test.PageTest):
      def __init__(self):
        super(TestBeforeLaunch, self).__init__()
        self._did_call_will_start = False
        self._did_call_did_start = False

      def WillStartBrowser(self, platform):
        self._did_call_will_start = True
        # TODO(simonjam): Test that the profile is available.

      def DidStartBrowser(self, browser):
        assert self._did_call_will_start
        self._did_call_did_start = True

      def ValidatePage(self, *_):
        assert self._did_call_did_start

    test = TestBeforeLaunch()
    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)

  def testRunPageWithStartupUrl(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    expectations = test_expectations.TestExpectations()
    page = page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir())
    page.startup_url = 'about:blank'
    ps.pages.append(page)

    class Measurement(page_test.PageTest):
      def __init__(self):
        super(Measurement, self).__init__()
        self.browser_restarted = False

      def CustomizeBrowserOptionsForSinglePage(self, ps, options):
        self.browser_restarted = True
        super(Measurement, self).CustomizeBrowserOptionsForSinglePage(ps,
                                                                      options)
      def ValidateAndMeasurePage(self, page, tab, results):
        pass

    options = options_for_unittests.GetCopy()
    options.page_repeat = 2
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    if not browser_finder.FindBrowser(options):
      return
    test = Measurement()
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)
    self.assertEquals('about:blank', options.browser_options.startup_url)
    self.assertTrue(test.browser_restarted)

  # Ensure that user_story_runner calls cleanUp when a page run fails.
  def testCleanUpPage(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    page = page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir())
    ps.pages.append(page)

    class Test(page_test.PageTest):
      def __init__(self):
        super(Test, self).__init__()
        self.did_call_clean_up = False

      def ValidatePage(self, *_):
        raise exceptions.IntentionalException

      def CleanUpAfterPage(self, page, tab):
        self.did_call_clean_up = True


    test = Test()
    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)
    assert test.did_call_clean_up

  # Ensure skipping the test if page cannot be run on the browser
  def testPageCannotRunOnBrowser(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()

    class PageThatCannotRunOnBrowser(page_module.Page):

      def __init__(self):
        super(PageThatCannotRunOnBrowser, self).__init__(
            url='file://blank.html', page_set=ps,
            base_dir=util.GetUnittestDataDir())

      def CanRunOnBrowser(self, _):
        return False

      def ValidatePage(self, _):
        pass

    class Test(page_test.PageTest):
      def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.will_navigate_to_page_called = False

      def ValidatePage(self, *args):
        pass

      def WillNavigateToPage(self, _1, _2):
        self.will_navigate_to_page_called = True

    test = Test()
    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(test, ps, expectations, options, results)
    self.assertFalse(test.will_navigate_to_page_called)
    self.assertEquals(0, len(GetSuccessfulPageRuns(results)))
    self.assertEquals(0, len(results.failures))

  def _testMaxFailuresOptionIsRespectedAndOverridable(self, max_failures=None):
    self.SuppressExceptionFormatting()
    class TestPage(page_module.Page):
      def __init__(self, *args, **kwargs):
        super(TestPage, self).__init__(*args, **kwargs)
        self.was_run = False

      def RunNavigateSteps(self, action_runner): # pylint: disable=W0613
        self.was_run = True
        raise Exception('Test exception')

    class Test(page_test.PageTest):
      def ValidatePage(self, *args):
        pass

    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    for ii in range(5):
      ps.pages.append(TestPage(
          'file://blank.html', ps, base_dir=util.GetUnittestDataDir()))

    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    expected_max_failures = 2
    if not max_failures is None:
      options.max_failures = max_failures
      expected_max_failures = max_failures
    SetUpUserStoryRunnerArguments(options)
    results = results_options.CreateResults(EmptyMetadataForTest(), options)
    user_story_runner.Run(Test(max_failures=2),
                    ps, expectations, options, results)
    self.assertEquals(0, len(GetSuccessfulPageRuns(results)))
    # Runs up to max_failures+1 failing tests before stopping, since
    # every tests after max_failures failures have been encountered
    # may all be passing.
    self.assertEquals(expected_max_failures + 1, len(results.failures))
    for ii in range(len(ps.pages)):
      if ii <= expected_max_failures:
        self.assertTrue(ps.pages[ii].was_run)
      else:
        self.assertFalse(ps.pages[ii].was_run)

  def testMaxFailuresOptionIsRespected(self):
    self._testMaxFailuresOptionIsRespectedAndOverridable()

  def testMaxFailuresOptionIsOverridable(self):
    self._testMaxFailuresOptionIsRespectedAndOverridable(1)

  def testRunPageWithProfilingFlag(self):
    ps = page_set.PageSet()
    expectations = test_expectations.TestExpectations()
    ps.pages.append(page_module.Page(
        'file://blank.html', ps, base_dir=util.GetUnittestDataDir()))

    class Measurement(page_test.PageTest):
      pass

    options = options_for_unittests.GetCopy()
    options.output_formats = ['none']
    options.suppress_gtest_report = True
    options.reset_results = None
    options.upload_results = None
    options.results_label = None
    options.output_dir = tempfile.mkdtemp()
    options.profiler = 'trace'
    try:
      SetUpUserStoryRunnerArguments(options)
      results = results_options.CreateResults(EmptyMetadataForTest(), options)
      user_story_runner.Run(Measurement(), ps, expectations, options, results)
      self.assertEquals(1, len(GetSuccessfulPageRuns(results)))
      self.assertEquals(0, len(results.failures))
      self.assertEquals(0, len(results.all_page_specific_values))
      self.assertTrue(os.path.isfile(
          os.path.join(options.output_dir, 'blank_html.json')))
    finally:
      shutil.rmtree(options.output_dir)
