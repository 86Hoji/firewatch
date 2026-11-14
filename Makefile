PY ?= python

pipeline:
	$(PY) -m pipeline.run_all

serve:
	$(PY) -m uvicorn api.main:app --port 8000

test:
	$(PY) -m pytest -q

.PHONY: pipeline serve test
