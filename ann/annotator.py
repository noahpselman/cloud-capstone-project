import json
import os
from uuid import uuid1
from time import sleep
from subprocess import Popen, PIPE
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('config.ini')

# ROOT = config['local']['RootDirectory']
# QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/127134666975/nselman_job_requests"
REGION = config['aws']['AwsRegionName']
QUEUE_URL = config['aws']['JobsQueueUrl']
DYNAMO_TABLENAME = config['aws']['DynamoTablename']
SIG_VERSION = config['aws']['SignatureVersion']
RUN_FILE = config['local']['RunFile']

JOBS_DIR = config['local']['JobsDirectory']
try:
    os.makedirs(JOBS_DIR)
except FileExistsError as e:
    print("ann-jobs directory already exists")

def get_val_from_message(val, message):
    return list(message[val].values())[0]

if __name__ == '__main__':
    # Connect to SQS and get the message queue
    try:
        sqs_client = boto3.client("sqs", region_name=REGION)
    except ClientError as e:
        print("problem connecting to sqs_client")
        print(e)
        raise

    # Poll the message queue in a loop 
    while True:
    
        # Attempt to read a message from the queue
        # Use long polling - DO NOT use sleep() to wait between polls
        try:
            response = sqs_client.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=20)
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
            receipt_handle = message['ReceiptHandle']
            body = json.loads(message['Body'])
            content = json.loads(body['Message'])
            # print(content)

            ### need a way to make sure that we haven't already processed the message 
            ### maybe this is taken care of by deleting the message from the queue

            # Extract Parameters from message
            job_id = content['job_id']
            user_id = content['user_id']
            input_file_name = content['input_file_name']
            s3_key_input_file = content['s3_key_input_file']
            s3_inputs_bucket = content['s3_inputs_bucket']

            print("\tjob_id", job_id)

            # make job directory    
            job_dir = f"{JOBS_DIR}/{user_id}/{job_id}"
            try:
                os.makedirs(job_dir)
            except FileExistsError:
                # this should never happen
                print(f"\tjob id {job_id} already as a corresponding folder")
                continue


            # download files to local ec2
            try:
                s3_client = boto3.client('s3', 
                                    region_name=REGION, 
                                    config=Config(signature_version=SIG_VERSION))
            except ClientError as e:

                print("\tProblem connecting to s3:", e)
                continue
            
            input_file = s3_key_input_file.split('/')[-1]
            input_path = f"{job_dir}/{input_file}"
            with open(input_path, 'wb') as data:
                try:
                    s3_client.download_fileobj(s3_inputs_bucket, s3_key_input_file, data)
                except ClientError as e:
                    print("\tProblem downloading from s3:", e)
                    continue
                    # possibly add logic to put this in a exception queue

            # run subprocess
            # run_file = f"{ROOT}/hw5-noahpselman/run.py"
            args = f"python {RUN_FILE} {input_path}"
            try:
                p = Popen(args, stdout=PIPE, shell=True)
            except Exception as e:
                print("\tProblem initiating hw5_run.py subprocess:", e)
                continue
                # possibly add logic to put this in a exception queue


            # update dynamo db
            update_expression = "SET job_status = :new_job_status"
            expression_vals = {":new_job_status": {"S": "RUNNING"}, ":pending": {"S": "PENDING"}}
            condtion_expression = "job_status = :pending"
            try:
                dynamo_client = boto3.client('dynamodb', region_name=REGION)
                response = dynamo_client.update_item(TableName=DYNAMO_TABLENAME, 
                                                        Key={'job_id': {'S': job_id}}, 
                                                        UpdateExpression=update_expression,
                                                        ExpressionAttributeValues=expression_vals,
                                                        ConditionExpression=condtion_expression)
            except ClientError as e:
                print("\tThere was an issue uploading the results to the Dynamo Table:", e)
                continue

            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                pass
            else:
                print(f"\tThere was a response with an HTTPStatusCode of {response['ResponseMetadata']['HTTPStatusCode']} after uploading to Dynamo")
                continue

            # delete message
            try:
                sqs_client.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
            except ClientError as e:
                print("\tThere was an error deleting message the message from the SQS:", e)


