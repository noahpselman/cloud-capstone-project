#!/bin/bash

# run_ann.sh
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Runs the annotator script
#
##

cd /home/ubuntu/gas/ann
source /usr/local/bin/virtualenvwrapper.sh
source /home/ubuntu/.virtualenvs/mpcs/bin/activate
python /home/ubuntu/gas/ann/annotator.py

### EOF