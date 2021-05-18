# archive_config.py
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
#
# Set app configuration options for archive utility
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):

  CSRF_ENABLED = True

  AWS_REGION_NAME = "us-east-1"

  AWS_DYNAMODB_ANNOTATIONS_TABLE = "nselman_annotations"
  AWS_S3_RESULTS_BUCKET = "gas-results"
  AWS_RESULTS_S3_KEY = 'nselman'
  AWS_ARCHIVE_MESSAGE_QUEUE = 'https://sqs.us-east-1.amazonaws.com/127134666975/nselman_results_archive'
  AWS_ARCHIVE_SNS = 'arn:aws:sns:us-east-1:127134666975:nselman_results_archive'
  AWS_VAULT_NAME = 'ucmpcs'

### EOF