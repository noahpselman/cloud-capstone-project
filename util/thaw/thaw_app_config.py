# thaw_app_config.py
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
#
# Set app configuration options for thaw utility
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):

  CSRF_ENABLED = True

  AWS_REGION_NAME = "us-east-1"

  # AWS DynamoDB table
  AWS_DYNAMODB_ANNOTATIONS_TABLE = "nselman_annotations"

  # QUEUE
  AWS_THAW_QUEUE = 'https://sqs.us-east-1.amazonaws.com/127134666975/nselman_thaw'

  # NOTIFICATIONS
  AWS_THAW_SNS = 'arn:aws:sns:us-east-1:127134666975:nselman_thaw'
  AWS_RESTORE_SNS = 'arn:aws:sns:us-east-1:127134666975:nselman_restore'

  # GLACIER
  AWS_VAULT_NAME = 'ucmpcs'



### EOF
