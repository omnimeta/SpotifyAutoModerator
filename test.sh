#!/bin/sh
# Run entire test suite:  ./test.sh
# Run specific test files:  ./test.sh <TEST_FILE_NAME_1> <TEST_FILE_NAME_2> ...
# Example:  ./test.sh test_playlist_scanner.py test_integrity_manager.py

COVERAGE_DIR="coverage" # where HTML reports and badges are stored

function save_coverage_badge() {
  if [ -f "${COVERAGE_DIR}/badge.svg" ]; then
    rm ${COVERAGE_DIR}/badge.svg
  fi
  printf "\n%s\n" "Generating a new test coverage badge based on this test run"
  coverage-badge -o "${COVERAGE_DIR}/badge.svg"
}

if [ ! -d "${COVERAGE_DIR}" ]; then
  mkdir ${COVERAGE_DIR}
fi

if [ -z "${1}" ]; then
  # just to up the tension a bit
  printf "Running the entire test suite (test/test_suite.py)\n"
  sleep 2
  printf "Good luck...\n\n"
  sleep 3

  python3 -m coverage run --include=src/* test/test_suite.py
  TEST_AND_COVERAGE_EXIT_CODE="${?}"
  printf "\n%s\n%s\n" "Coverage report:" "----------------------------------------------"
  python3 -m coverage report
  python3 -m coverage html -d ${COVERAGE_DIR}
  save_coverage_badge
  exit ${TEST_AND_COVERAGE_EXIT_CODE}
fi

ARGUMENTS=""
for FILENAME in ${@}; do
  ARGUMENTS="${ARGUMENTS} test/${FILENAME}"
done
python3 -m unittest -v ${ARGUMENTS} 
