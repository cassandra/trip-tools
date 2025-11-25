#!/bin/sh

# NUM_WORKERS must remain "1" until refactored for multiple processes to
# share the state of the background managers and monitors. Else too much
# API polling and processes having inconsistent states.

NUM_WORKERS=1
NUM_THREADS=9
BINDARG=unix:/var/run/gunicorn.sock

exec gunicorn tt.wsgi:application \
  --name gunicorn \
  --workers $NUM_WORKERS \
  --threads $NUM_THREADS \
  --bind=$BINDARG \
  --log-file=-
