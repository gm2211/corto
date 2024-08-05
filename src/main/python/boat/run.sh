#!/usr/bin/bash --

function run_server() {
  PYTHONPATH="${PYTHONPATH}:/home/raspi/projects/corto/src/main/python/" python corto.py
}

until run_server; do
    echo "Server crashed with exit code $?.  Respawning.." >&2
    sleep 1
done

