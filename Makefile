codespell:
	codespell -w $(shell git ls-files | grep -v swirlc/antlr)

codespell-check:
	codespell $(shell git ls-files | grep -v swirlc/antlr)

coverage.xml: testcov
	coverage xml

coverage-report: testcov
	coverage report

flake8:
	flake8 --exclude swirlc/antlr swirlc tests

format:
	black swirlc tests

format-check:
	black --diff --check swirlc tests

pyupgrade:
	pyupgrade --py3-only --py38-plus $(shell git ls-files | grep .py | grep -v swirlc/antlr)

test:
	python -m pytest -rs ${PYTEST_EXTRA}

testcov:
	python -m pytest -rs --cov --cov-report= ${PYTEST_EXTRA}
