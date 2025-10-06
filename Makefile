.PHONY: venv fmt lint test demo clean

VENV?=.venv
PYTHON?=python3

venv:
$(PYTHON) -m venv $(VENV)
$(VENV)/bin/pip install --upgrade pip
$(VENV)/bin/pip install -e .[dev]

fmt:
$(PYTHON) -m black serdiff tests
$(PYTHON) -m ruff check serdiff tests --fix

lint:
$(PYTHON) -m ruff check serdiff tests

test:
$(PYTHON) -m pytest

demo:
ser-diff --before samples/SER_before.xml --after samples/SER_after.xml --table SER --out-prefix reports/demo_SER --jira DEMO-SER
ser-diff --before samples/EXPOSURE_before.xml --after samples/EXPOSURE_after.xml --table EXPOSURE --out-prefix reports/demo_EXPOSURE --jira DEMO-EXP

clean:
rm -rf $(VENV)
rm -rf reports/demo_*
