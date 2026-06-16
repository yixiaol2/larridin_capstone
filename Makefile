.PHONY: setup lint format test sample-panel sample-analysis robustness dashboard clean

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
STREAMLIT ?= $(PYTHON) -m streamlit
PROJECT_PYTHONPATH ?= src

setup:
	$(PIP) install -e ".[dev]"

lint:
	$(RUFF) check src tests scripts

format:
	$(RUFF) format src tests scripts

test:
	$(PYTEST) tests

sample-panel:
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(PYTHON) scripts/bootstrap_from_samples.py

sample-analysis:
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(PYTHON) scripts/run_baseline_analysis.py --panel data/processed/analytic_panel.csv

robustness:
	test -f data/processed/analytic_panel.csv || (echo "Run make sample-panel before make robustness."; exit 1)
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(PYTHON) -c "import pandas as pd; from ai_impact_research.analysis.robustness import missingness_summary; print(missingness_summary(pd.read_csv('data/processed/analytic_panel.csv')).to_string(index=False))"

dashboard:
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(STREAMLIT) run src/ai_impact_research/dashboard/app.py

clean:
	rm -rf data/processed/*.csv .pytest_cache .ruff_cache .mypy_cache
