#!/usr/bin/env sh
python3 -m pip install pytest pytest-cov pylint
python3 -m pytest --verbose --cov=yatat --cov-report=html
python3 -m pylint yatat
