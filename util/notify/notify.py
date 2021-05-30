# notify.py
#
# Notify users of job completion
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import boto3
import time
import os
import sys
import json
import psycopg2
from botocore.exceptions import ClientError

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers
# helpers must be imported first to avoid ambiguous file names


# Get configuration
from configparser import ConfigParser
notify_config = ConfigParser(os.environ)
notify_config.read('notify_config.ini')
# util_config = ConfigParser(os.environ)
# util_config.read('../util_config.ini')


'''Capstone - Exercise 3(d)
Reads result messages from SQS and sends notification emails.
'''


if __name__ == '__main__':


    # Connect to SQS and get the message queue
    try:
        sqs_client = boto3.client("sqs", region_name=notify_config['aws']['AwsRegionName'])
    except ClientError as e:
        print("Problem connecting to sqs_client:", e)
        raise

    # Poll queue for new results and process them
    while True:

        try:
            print("Receiving messages...")
            response = sqs_client.receive_message(
                QueueUrl=notify_config['sqs']['ResultsQueueUrl'], MaxNumberOfMessages=1, WaitTimeSeconds=20)
        except ClientError as e:
            print("Problem connecting to SQS:", e)
            continue   

        try:
            messages = response['Messages']
        except KeyError:
            print("No messages found...")
            continue

        print(f"found {len(messages)} messages")

        for message in messages:

            # Extract Parameters from message
            try:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                content = json.loads(body['Message'])
                job_id = content['job_id']
                user_id = content['user_id']
                download_link = content['link']
                print("Extracted parameters for messages associated with job_id:", job_id)
            except (KeyError, TypeError, json.decoder.JSONDecodeError) as e:
                print("The message isn't in the right format:", e)
                continue

            user_email = helpers.get_user_profile(user_id)['email']

            try:
                print("Sending email to", user_email)
                message = f"Job {job_id} for user {user_id} has finished.  " + \
                f"Results can be downloaded from this link: {download_link}"
                helpers.send_email_ses(recipients=user_email, 
                                    sender=notify_config['gas']['MailDefaultSender'], 
                                    subject='GAS Job Complete', 
                                    body=message)
            except ClientError as e:
                print("There was a problem sending the email:", e)
                continue

            # delete message
            try:
                print("Deleting message from SQS...")
                sqs_client.delete_message(QueueUrl=notify_config['sqs']['ResultsQueueUrl'], 
                                            ReceiptHandle=receipt_handle)
            except ClientError as e:
                print("There was an error deleting message the message from the SQS:", e)
                continue



### EOF
