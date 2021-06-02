# ann_load.py
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
#
# Exercises the annotator's auto scaling
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import uuid
import time
import sys
import json
import boto3
from botocore.exceptions import ClientError

# Define constants here; no config file is used for this scipt
USER_ID = "794afb63-0059-466f-9818-6fa5a1409871"
TOPIC = "arn:aws:sns:us-east-1:127134666975:nselman_job_requests"


"""Fires off annotation jobs with hardcoded data for testing
"""


def load_requests_queue():

    sns_client = boto3.client("sns", region_name='us-east-1')
    job_id = str(uuid.uuid1())
    message = {'user_id': USER_ID, 'job_id': job_id}
    response = sns_client.publish(TopicArn=TOPIC, Message=json.dumps(message))
    print(response)


if __name__ == '__main__':
    while True:
        try:
            load_requests_queue()
            time.sleep(3)
        except ClientError as e:
            print("Irrecoverable error. Exiting.")
            sys.exit()

# EOF
