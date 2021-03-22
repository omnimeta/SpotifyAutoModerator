#!/bin/sh
# To generate coverage report and html:  ./coverage.sh <TEST_FILE_NAME>
# Example:  ./coverage.sh test_spotify_helper.py

COVERAGE_DIR="coverage" # where HTML reports and badges are stored

function save_coverage_badge() {
  if [ -f "${COVERAGE_DIR}/badge.svg" ]; then
    rm ${COVERAGE_DIR}/badge.svg
  fi
  printf "\n%s\n" "Generating a new test coverage badge based on this test run"
  coverage-badge -o ${COVERAGE_DIR}/badge.svg
}

if [ ! -d "${COVERAGE_DIR}" ]; then
  mkdir ${COVERAGE_DIR}
fi

SRC="${1}"
if [ -z "${SRC}" ]; then
  COVERAGE="true" python3 -m coverage run --include=src/* test/test_suite.py
  TEST_AND_COVERAGE_EXIT_CODE="${?}"
  printf "\n%s\n%s\n" "Coverage report:" "----------------------------------------------"
  python3 -m coverage report
  python3 -m coverage html -d ${COVERAGE_DIR}
  save_coverage_badge
  exit ${TEST_AND_COVERAGE_EXIT_CODE}
fi

python3 -m coverage run --include=src/* test/${1}
python3 -m coverage report
python3 -m coverage html -d ${COVERAGE_DIR}
