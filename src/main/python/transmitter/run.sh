#!/usr/bin/bash --
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$(cd $SCRIPT_DIR && PYTHONPATH="${PYTHONPATH}:/home/raspi/projects/corto/src/main/python/" python boat_remote.py $@)
