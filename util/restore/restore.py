# restore.py
#
# Restores thawed data, saving objects to S3 results bucket
# NOTE: This code is for an AWS Lambda function
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
##

import json
import os
import boto3
from botocore.exceptions import ClientError


# HERE ARE THE VARIABLES IN THE LAMBDA ENVIRONMENT
DYNAMO_TABLE_NAME = "nselman_annotations"
REGION_NAME = "us-east-1"
RESTORE_SQS = "https://sqs.us-east-1.amazonaws.com/127134666975/nselman_restore"
RESULTS_S3_KEY = "nselman"
S3_RESULTS_BUCKET = "gas-results"
VAULT_NAME = "ucmpcs"


def lambda_handler(event, context):
	print("received event", json.dumps(event, indent=2))


	# read sqs
	try:
		sqs_client = boto3.client("sqs", region_name=os.environ['REGION_NAME'])
	except ClientError as e:
		print(f"Problem connecting to SQS:", e)
		raise

	try:
		response = sqs_client.receive_message(
		QueueUrl=os.environ['RESTORE_SQS'],
		MaxNumberOfMessages=1,
		WaitTimeSeconds=20)
	except ClientError as e:
		print("Problem receiving messages:", e)
		raise
	try:
		[message] = response['Messages']
		print("message")
		print(message)
		receipt_handle = message['ReceiptHandle']
		body = json.loads(message['Body'])
		content = json.loads(body['Message'])
		print("content", content)
		restore_job_id = content['JobId']
		job_id = json.loads(content['JobDescription'])['job_id']
	except KeyError as e:
		print(f"no messages found:", e)
		raise

	print('restore_job_id', restore_job_id)

	# get job_id data
	attributes = ['s3_key_result_file', 's3_results_bucket']
	try:
		dynamo_client = boto3.client('dynamodb',
									  region_name=os.environ['REGION_NAME'])
		response = dynamo_client.get_item(TableName=os.environ['DYNAMO_TABLE_NAME'],
							  	       Key={'job_id': {'S': job_id}},
						   			   AttributesToGet=attributes)
		item = response['Item']

	except (ClientError, KeyError) as e:
		print("problem reading dynamo table", e)
		raise


	item = {k: list(v.values())[0] for k, v in item.items()}
	try:
		s3_key = item['s3_key_result_file']
		s3_bucket = item['s3_results_bucket']
	except KeyError as e:
		print("Dynamo table does not have expected columns:", e)
		raise


	# move thawed file to s3
	try:
		glacier_client = boto3.client('glacier', region_name=os.environ['REGION_NAME'])
		response = glacier_client.get_job_output(
						vaultName=os.environ['VAULT_NAME'],
						jobId=restore_job_id
					)
	except ClientError as e:
		print("There was an exception accessing the retrieval results:", e)
		raise

	print("restore response:", response)
	body = response['body'].read()
	print("restore response body:", body)


	# move to s3
	try:
		s3_client = boto3.client('s3', region_name=os.environ['REGION_NAME'])
		response = s3_client.put_object(
			Bucket=s3_bucket,
			Key=s3_key,
			Body=body)
	except ClientError as e:
		print("There was an exception moving to s3:", e)
		raise

	print("s3 response:", response)

	# update dynamo
	new_data = {"retrieval_status": {"S": "RETRIEVED"}}
	print("updating dynamo with ", job_id)
	update_expression = "SET retrieval_status = :new_retrieval_status"
	expression_vals = {":retrieving": {"S": "RETRIEVING"},
						":new_retrieval_status": {'S': 'RETRIEVED'}}
	condition_expression = "retrieval_status = :retrieving"
	try:
		dynamo_client = boto3.client('dynamodb', region_name=os.environ['REGION_NAME'])
		response = dynamo_client.update_item(TableName=os.environ['DYNAMO_TABLE_NAME'],
											Key={'job_id': {'S': job_id}},
											UpdateExpression=update_expression,
											ExpressionAttributeValues=expression_vals,
											ConditionExpression=condition_expression)
	except ClientError as e:
		print("There was an issue uploading the results to the Dynamo Table:", e)
		raise


	# delete message
	try:
		sqs_client.delete_message(QueueUrl=os.environ['RESTORE_SQS'],
									ReceiptHandle=receipt_handle)
	except ClientError as e:
		print("There was an error deleting message the message from the SQS:", e)
		raise


### EOF
