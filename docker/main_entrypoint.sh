#!/usr/bin/env bash

cd /srv/lkf-sanic-app/app/
#sanic main:create_app --host=0.0.0.0 --port=8000 --debug --auto-reload

python main.py
# watchfiles --filter python 'python main.py' /srv/lkf-sanic-app/app/modules