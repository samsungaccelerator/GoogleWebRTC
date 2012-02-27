#!/usr/bin/env python
#-*- coding: utf-8 -*-
# Copyright (c) 2012 The WebRTC project authors. All Rights Reserved.
#
# Use of this source code is governed by a BSD-style license
# that can be found in the LICENSE file in the root of the source
# tree. An additional intellectual property rights grant can be found
# in the file PATENTS.  All contributing project authors may
# be found in the AUTHORS file in the root of the source tree.

"""This script grabs and reports coverage information.

   It grabs coverage information from the latest Linux 32-bit build and
   pushes it to the coverage tracker, enabling us to track code coverage
   over time. This script is intended to run on the 32-bit Linux slave.

   This script requires an access.token file in the current directory, as
   generated by the request_oauth_permission.py script. It also expects a file
   customer.secret with a single line containing the customer secret. The
   customer secret is an OAuth concept and is received when one registers the
   application with the App Engine running the dashboard.

   The script assumes that all coverage data is stored under
   /home/<build bot user>/www.
"""

__author__ = 'phoglund@webrtc.org (Patrik Höglund)'

import os
import re
import time

import constants
import dashboard_connection


class FailedToParseCoverageHtml(Exception):
  pass


class CouldNotFindCoverageDirectory(Exception):
  pass


def _find_latest_32bit_debug_build(www_directory_contents, coverage_www_dir):
  """Finds the latest 32-bit coverage directory in the directory listing.

     Coverage directories have the form Linux32bitDBG_<number>. There may be
     other directories in the list though, for instance for other build
     configurations.
  """

  # This sort ensures we will encounter the directory with the highest number
  # first.
  www_directory_contents.sort(reverse=True)

  for entry in www_directory_contents:
    match = re.match('Linux32DBG_\d+', entry)
    if match is not None:
      return entry

  raise CouldNotFindCoverageDirectory('Error: Found no 32-bit '
                                      'debug build in directory %s.' %
                                      coverage_www_dir)


def _grab_coverage_percentage(label, index_html_contents):
  """Extracts coverage from a LCOV coverage report.

     Grabs coverage by assuming that the label in the coverage HTML report
     is close to the actual number and that the number is followed by a space
     and a percentage sign.
  """
  match = re.search('<td[^>]*>' + label + '</td>.*?(\d+\.\d) %',
                    index_html_contents, re.DOTALL)
  if match is None:
    raise FailedToParseCoverageHtml('Missing coverage at label "%s".' % label)

  try:
    return float(match.group(1))
  except ValueError:
    raise FailedToParseCoverageHtml('%s is not a float.' % match.group(1))


def _report_coverage_to_dashboard(dashboard, now, line_coverage,
                                  function_coverage):
  parameters = {'date': '%d' % now,
                'line_coverage': '%f' % line_coverage,
                'function_coverage': '%f' % function_coverage
               }

  dashboard.send_post_request(constants.ADD_COVERAGE_DATA_URL, parameters)


def _main():
  dashboard = dashboard_connection.DashboardConnection(constants.CONSUMER_KEY)
  dashboard.read_required_files(constants.CONSUMER_SECRET_FILE,
                                constants.ACCESS_TOKEN_FILE)

  www_dir_contents = os.listdir(BUILD_BOT_COVERAGE_WWW_DIRECTORY)
  latest_build_directory = _find_latest_32bit_debug_build(www_dir_contents,
                                                          coverage_www_dir)

  index_html_path = os.path.join(coverage_www_dir, latest_build_directory,
                                 'index.html')
  index_html_file = open(index_html_path)
  whole_file = index_html_file.read()

  line_coverage = _grab_coverage_percentage('Lines:', whole_file)
  function_coverage = _grab_coverage_percentage('Functions:', whole_file)
  now = int(time.time())

  _report_coverage_to_dashboard(dashboard, now, line_coverage,
                                function_coverage)


if __name__ == '__main__':
  _main()

