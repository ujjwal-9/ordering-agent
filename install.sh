#!/bin/bash
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
npm install
cd frontend && npm install
