COVERAGE_FILE := .coverage
PACKAGE_DIR := timer_trigger_revoke
TEST_DIR := tests
UNIT_TEST_DIR := ${TEST_DIR}/unit
TEST_CACHE_DIR := .pytest_cache

test:
	echo "Running unit tests";
	pytest ${UNIT_TEST_DIR} --cov=${PACKAGE_DIR} --full-trace -vv;
lint:
	echo "Running linter (any error will result in non-zero exit code)";
	pylint -j 0 ${PACKAGE_DIR}/ ${TEST_DIR}/;
coverage: test
	echo "Generating code coverage documentation";
	coverage html;
clean:
	echo "Removing artifacts"
	rm -rf ${COVERAGE_FILE}
	rm -rf ${DIST_DIR}
	rm -rf ${TEST_CACHE_DIR}
clean_cache:
	find . -type d -name __pycache__ -exec rm -r {} \+
.PHONY: clean
