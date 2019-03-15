#!/usr/bin/env sh
python3 -m pytest --verbose --cov=yatat --cov-report=html
python3 -m pylint yatat
