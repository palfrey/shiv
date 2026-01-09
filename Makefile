requirements.txt: requirements.in
	uv pip compile --python-version 3.11 --no-strip-extras requirements.in -o requirements.txt

.venv/bin/activate:
	uv venv

.PHONY: sync
sync: requirements.txt .venv/bin/activate
	uv pip sync --strict requirements.txt

install-pre-commit: sync
	uv run pre-commit install

pre-commit: sync
	uv run pre-commit run -a

test: sync
	uv run pytest -vvv
