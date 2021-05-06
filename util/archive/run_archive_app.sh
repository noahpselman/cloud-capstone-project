#!/bin/bash

# run_archive_app.sh
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
#
# Runs the archive utility Flask app
#
##

SSL_CERT_PATH=/usr/local/src/ssl/ucmpcs.org.crt
SSL_KEY_PATH=/usr/local/src/ssl/ucmpcs.org.key

cd /home/ubuntu/gas

export ARCHIVE_APP_HOME=/home/ubuntu/gas/util/archive
export SOURCE_HOST=0.0.0.0
export HOST_PORT=4433

/home/ubuntu/.virtualenvs/mpcs/bin/uwsgi \
  --manage-script-name \
  --enable-threads \
  --vacuum \
  --log-master \
  --chdir $ARCHIVE_APP_HOME \
  --socket /tmp/archive_app.sock \
  --mount /archive_app=archive_app:app \
  --https $SOURCE_HOST:$HOST_PORT,$SSL_CERT_PATH,$SSL_KEY_PATH

### EOF