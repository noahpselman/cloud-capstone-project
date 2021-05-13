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

# Get configuration
from configparser import ConfigParser
notify_config = ConfigParser(os.environ)
notify_config.read('notify_config.ini')
util_config = ConfigParser(os.environ)
util_config.read('../util_config.ini')


REGION = notify_config['aws']['AwsRegionName']
RESULTS_QUEUE = notify_config['sqs']['ResultsQueueUrl']
DYNAMO_TABLENAME = notify_config['dynamodb']['DynamoTableName']

'''Capstone - Exercise 3(d)
Reads result messages from SQS and sends notification emails.
'''
def handle_results_queue(sqs=None):

    # Read a message from the queue

    # Process message

    # Delete message

    pass

if __name__ == '__main__':

    # Get handles to resources; and create resources if they don't exist


    # Connect to SQS and get the message queue
    try:
        sqs_client = boto3.client("sqs", region_name=REGION)
    except ClientError as e:
        print("problem connecting to sqs_client")
        print(e)
        raise

    # Poll queue for new results and process them
    while True:

        try:
            response = sqs_client.receive_message(
                QueueUrl=RESULTS_QUEUE, MaxNumberOfMessages=10, WaitTimeSeconds=20)
            # print("sqs client response:", response)
        except ClientError as e:
            print("Problem connecting to SQS")
            print(e)
            raise

        try:
            messages = response['Messages']
        except KeyError:
            print("there was a key error here for some reason - probably no messages")
            continue

        print(f"found {len(messages)} messages")

        for message in messages:


            # Extract Parameters from message
            try:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                content = json.loads(body['Message'])
                job_id = content['job_id']
                print("\tjob_id:", job_id)
                user_id = content['user_id']
                download_link = content['link']
            except (KeyError, TypeError, json.decoder.JSONDecodeError) as e:
                print("The message isn't in the right format")
                print(e)
                continue

            # handle_results_queue(sqs=sqs)

            # get recipient email
            try:
                dynamo_client = boto3.client('dynamodb', region_name=REGION)
                response = dynamo_client.get_item(TableName=DYNAMO_TABLENAME,
                                       Key={'job_id': {'S': job_id}},
                                       AttributesToGet=['user_email'])
                user_email = list(response['Item']['user_email'].values())[0]
                print("\tuser email retrieved", user_email)

            except ClientError as e:
                print("There fetching email address")
                print(e)
                continue

            # send email
            try:
                message = f"Job {job_id} for user {user_id} has finished.  " + \
                f"Results can be downloaded from this link: {download_link}"
                helpers.send_email_ses(recipients=user_email, 
                                    sender=util_config['gas']['MailDefaultSender'], 
                                    subject='GAS Job Complete', 
                                    body=message)
                print("\temail sent to:", user_email)
            except ClientError as e:
                print("There was a problem sending the email")
                print(e)
                continue

            # delete message
            try:
                sqs_client.delete_message(QueueUrl=RESULTS_QUEUE, ReceiptHandle=receipt_handle)
            except ClientError as e:
                print("\tThere was an error deleting message the message from the SQS:", e)
                continue



### EOF
