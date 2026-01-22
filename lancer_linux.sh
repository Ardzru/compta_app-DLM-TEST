#!/bin/bash

cd "$(dirname "$0")"

source venv310/bin/activate

python ui_server.py

