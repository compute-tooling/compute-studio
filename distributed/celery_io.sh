#!/usr/bin/env bash
SAFEOWNER=$(python -c "import re, os; print(re.sub('[^0-9a-zA-Z]+', '', \"$1\").lower())")
SAFETITLE=$(python -c "import re, os; print(re.sub('[^0-9a-zA-Z]+', '', \"$2\").lower())")
celery -A celery_app.${SAFEOWNER}_${SAFETITLE}_tasks worker --loglevel=info --concurrency=1 -n ${SAFEOWNER}_${SAFETITLE}_inputs@%h
