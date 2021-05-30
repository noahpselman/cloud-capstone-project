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


try:
    os.makedirs(config['local']['JobsDirectory'])
except FileExistsError as e:
    print("ann-jobs directory already exists")

def get_val_from_message(val, message):
    return list(message[val].values())[0]

if __name__ == '__main__':
    # Connect to SQS and get the message queue
    try:
        sqs_client = boto3.client("sqs", region_name=config['aws']['AwsRegionName'])
    except ClientError as e:
        print("problem connecting to sqs_client:", e)
        raise

    # Poll the message queue in a loop 
    while True:
    
        # Attempt to read a message from the queue
        # Use long polling - DO NOT use sleep() to wait between polls
        try:
            print("Receiving messages...")
            response = sqs_client.receive_message(QueueUrl=config['aws']['JobsQueueUrl'], MaxNumberOfMessages=1, WaitTimeSeconds=20)
        except ClientError as e:
            print("Problem receiving messages:", e)
            raise
        
        try:
            messages = response['Messages']
        except KeyError:
            print("there was a key error here for some reason - probably no messages")
            continue
        
        print(f"found {len(messages)} messages")


        for message in messages:
            print("starting the message loop")
            try:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                content = json.loads(body['Message'])
            except KeyError as e:
                print("Message did not contain necessary data:", e)

            # Extract Parameters from message
            job_id = content['job_id']
            user_id = content['user_id']
            input_file_name = content['input_file_name']
            s3_key_input_file = content['s3_key_input_file']
            s3_inputs_bucket = content['s3_inputs_bucket']


            # make job directory    
            job_dir = f"{config['local']['JobsDirectory']}/{user_id}/{job_id}"
            try:
                os.makedirs(job_dir)
            except FileExistsError:
                # this should never happen
                print(f"job id {job_id} already as a corresponding folder")
                continue


            # download files to local ec2
            print("Downloading input files to ec2...")
            try:
                s3_client = boto3.client('s3', 
                                    region_name=config['aws']['AwsRegionName'], 
                                    config=Config(signature_version=config['aws']['SignatureVersion']))
            except ClientError as e:

                print("Problem connecting to s3:", e)
                continue
            
            input_file = s3_key_input_file.split('/')[-1]
            input_path = f"{job_dir}/{input_file}"
            with open(input_path, 'wb') as data:
                try:
                    s3_client.download_fileobj(s3_inputs_bucket, s3_key_input_file, data)
                except ClientError as e:
                    print("Problem downloading from s3:", e)
                    continue

            # run subprocess
            print("Initiating subprocess to run job...")
            args = f"python {config['local']['RunFile']} {input_path}"
            try:
                p = Popen(args, stdout=PIPE, shell=True)
            except Exception as e:
                print("Problem initiating run.py subprocess:", e)
                continue

            # update dynamo db
            print("Updating dynamo...")
            update_expression = "SET job_status = :new_job_status"
            expression_vals = {":new_job_status": {"S": "RUNNING"}, ":pending": {"S": "PENDING"}}
            condtion_expression = "job_status = :pending"
            try:
                dynamo_client = boto3.client('dynamodb', region_name=config['aws']['AwsRegionName'])
                response = dynamo_client.update_item(TableName=config['aws']['DynamoTablename'], 
                                                        Key={'job_id': {'S': job_id}}, 
                                                        UpdateExpression=update_expression,
                                                        ExpressionAttributeValues=expression_vals,
                                                        ConditionExpression=condtion_expression)
            except ClientError as e:
                print("There was an issue uploading the results to the Dynamo Table:", e)
                continue

            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                pass
            else:
                print(f"There was a response with an HTTPStatusCode of {response['ResponseMetadata']['HTTPStatusCode']} after uploading to Dynamo")
                continue

            # delete message
            print("Deleting message")
            try:
                sqs_client.delete_message(QueueUrl=config['aws']['JobsQueueUrl'], ReceiptHandle=receipt_handle)
                print("deleted message")
            except ClientError as e:
                print("\tThere was an error deleting message the message from the SQS:", e)


