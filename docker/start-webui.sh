#!/bin/bash

set -e

python /opt/maxinus/configure_openwebui_stt.py /app/backend/data/webui.db
exec bash start.sh
