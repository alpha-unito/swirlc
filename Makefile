codespell:
	codespell -w $(shell git ls-files | grep -v swirl/antlr)

codespell-check:
	codespell $(shell git ls-files | grep -v swirl/antlr)

coverage.xml: testcov
	coverage xml

coverage-report: testcov
	coverage report

flake8:
	flake8 --exclude swirl/antlr swirl tests

format:
	black swirl tests

format-check:
	black --diff --check swirl tests

pyupgrade:
	pyupgrade --py3-only --py38-plus $(shell git ls-files | grep .py | grep -v swirl/antlr)

test:
	python -m pytest -rs ${PYTEST_EXTRA}

testcov:
	python -m pytest -rs --cov --cov-report= ${PYTEST_EXTRA}
