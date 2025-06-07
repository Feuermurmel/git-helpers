.PHONY: venv
venv:
	python3 -m venv --clear venv
	venv/bin/pip install --editable '.[dev]'
