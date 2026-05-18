codespell:
	codespell -w $(shell git ls-files | grep -v swirlc/antlr)

codespell-check:
	codespell $(shell git ls-files | grep -v swirlc/antlr)

coverage.xml: testcov
	coverage xml

coverage-report: testcov
	coverage report

format:
	ruff check --fix swirlc tests
	black swirlc tests

format-check:
	ruff check swirlc tests
	black --diff --check swirlc tests

pyupgrade:
	pyupgrade --py3-only --py310-plus $(shell git ls-files | grep .py | grep -v swirlc/antlr)

test:
	python -m pytest -rs ${PYTEST_EXTRA}

testcov:
	python -m pytest -rs --cov --cov-report= ${PYTEST_EXTRA}
