import unittest
import os
from test import test_spotify_helper
from test import test_playlist_cleaner
from test import test_integrity_manager
from test import test_config_validator
from test import test_main
from test import test_integration


def run_test_suite():

    # by default, the name and result of each executed fixture is shown
    verbosity_level = 3
    if 'COVERAGE' in os.environ.keys() and os.environ['COVERAGE'] in [ 'true', 'TRUE', '1' ]:
        # only the overall result is relevant when tests are run solely for measuring code coverage
        verbosity_level = 0

    test_runner = unittest.TextTestRunner(verbosity=verbosity_level)
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    for mod in [
        test_spotify_helper,
        test_playlist_cleaner,
        test_integrity_manager,
        test_config_validator,
        test_main,
        test_integration
    ]:
        test_suite.addTests(test_loader.loadTestsFromModule(mod))
    test_run = test_runner.run(test_suite)
    print_test_results(test_run)


def print_test_results(test_run):
    row_length = 32

    def print_test_table_headings():
        num_spaces = row_length - 10
        print('Tests%sCount' % (' ' * num_spaces))

    def print_test_table_row(label, num):
        num_spaces = row_length - len(label) - len(str(num))
        print('%s%s%d' % (label, ' ' * num_spaces, num))

    def print_line_of_chars(char):
        print(char * row_length)

    result = 'PASSED' if test_run.wasSuccessful() else 'FAILED'
    num_passed = test_run.testsRun - len(test_run.errors) - len(test_run.failures)

    print('\nTest suite %s' % result)
    print_line_of_chars('-')
    print_test_table_headings()
    print_line_of_chars('-')
    print_test_table_row('Passed', num_passed)
    print_test_table_row('  Expectedly Passed', num_passed - len(test_run.unexpectedSuccesses))
    print_test_table_row('  Unexpectedly Passed', len(test_run.expectedFailures))
    print_line_of_chars(' ')
    print_test_table_row('Failed', len(test_run.failures))
    print_test_table_row('  Expectedly Failed', len(test_run.expectedFailures))
    print_test_table_row('  Unexpectedly Failed', len(test_run.failures) - len(test_run.expectedFailures))
    print_line_of_chars(' ')
    print_test_table_row('Encountered Errors', len(test_run.errors))
    print_test_table_row('Skipped', len(test_run.skipped))
    print_line_of_chars('-')
    print_test_table_row('TOTAL', test_run.testsRun)


if __name__ == '__main__':
    run_test_suite()
