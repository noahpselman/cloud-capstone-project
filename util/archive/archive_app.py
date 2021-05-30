# archive_app.py
#
# Archive free user data
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import json
import os
import uuid
import sys
import boto3
from botocore.exceptions import ClientError

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

from flask import Flask, request, abort, render_template

app = Flask(__name__)
environment = 'archive_app_config.Config'
app.config.from_object(environment)
app.url_map.strict_slashes = False

@app.route('/', methods=['GET'])
def home():
  return (f"This is the Archive utility: POST requests to /archive.")

@app.route('/archive', methods=['POST'])
def archive_free_user_data():

	# read notification
	try:
		data = json.loads(request.data)
		message = json.loads(data['Message'])
		topic_arn = data["TopicArn"]
	except KeyError as e:
		print("invalid inputs:", e)
		abort(500)
		

	if topic_arn != app.config['AWS_ARCHIVE_SNS']:
		abort(405)
	
	# connecto to sqs
	try:
		sqs_client = boto3.client("sqs", region_name=app.config['AWS_REGION_NAME'])
	except ClientError as e:
		print(f"Problem connecting to SQS:", e)
		return abort(500)

	try:
		response = sqs_client.receive_message(
		QueueUrl=app.config['AWS_ARCHIVE_MESSAGE_QUEUE'], 
		MaxNumberOfMessages=10, 
		WaitTimeSeconds=20)
	except ClientError as e:
		print("Problem receiving messages:", e)
		return abort(500)
	try:
		messages = response['Messages']
		print(f"found {len(messages)} messages")
	except KeyError as e:
		print(f"No messages found:", e)
		return abort(500)

	# extract data

	for message in messages:
		try:
			receipt_handle = message['ReceiptHandle']
			body = json.loads(message['Body'])
			content = json.loads(body['Message'])

			job_id = content['job_id']
			user_id = content['user_id']
			s3_key_result_file = content['s3_key_result_file']
		except KeyError as e:
			print("Message doesn't have correct fields:", e)
			abort(500)


		user_role = helpers.get_user_profile(user_id)['role']

		try:
			s3_client = boto3.client('s3', region_name=app.config['AWS_REGION_NAME'])
		except ClientError as e:
			print("problem creating s3 client:", e)
			return abort(500)

		if user_role == 'free_user':
			print("free user... archiving results")

			# get s3
			try:
				print("getting result objects from s3...")
				obj = s3_client.get_object(Bucket=app.config['AWS_S3_RESULTS_BUCKET'], 
										Key=s3_key_result_file)
				content = obj['Body'].read()
			except ClientError as e:
				print("Failed get object from s3:", e)
				return abort(500)

			# archiving to glacier
			try:
				print("uploading to glacier...")
				glacier_client = boto3.client('glacier', region_name=app.config['AWS_REGION_NAME'])
				response = glacier_client.upload_archive(vaultName=app.config['AWS_VAULT_NAME'],
											body=content)
				archive_id = response['archiveId']
			except ClientError as e:
				print("Problem uploading to glacier:", e)
				return abort(500)

			# upload glacier id to dynamo
			print(f"updating dynamo table with job_id {job_id} to store archive id...")
			update_expression = "SET archive_status = :new_archive_status, archive_id = :new_archive_id"
			expression_vals = {":new_archive_id": {"S": archive_id}, 
							":not_archived": {"S": "NOT_ARCHIVED"},
							":new_archive_status": {'S': 'ARCHIVED'}}
			condtion_expression = "archive_status = :not_archived"
			try:
				dynamo_client = boto3.client('dynamodb', region_name=app.config['AWS_REGION_NAME'])
				response = dynamo_client.update_item(TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
														Key={'job_id': {'S': job_id}}, 
														UpdateExpression=update_expression,
														ExpressionAttributeValues=expression_vals,
														ConditionExpression=condtion_expression)
			except ClientError as e:
				print("There was an issue uploading the results to the Dynamo Table:", e)
				return abort(500)

			try:
				print("deleting results file from s3...")
				response = s3_client.delete_object(
					Bucket=app.config['AWS_S3_RESULTS_BUCKET'],
					Key=s3_key_result_file
				)
			except ClientError as e:
				print("Problem deleting s3 object", e)
				return abort(500)

		# delete message
		try:
			print("deleting message from queue...")
			sqs_client.delete_message(QueueUrl=app.config['AWS_ARCHIVE_MESSAGE_QUEUE'], 
									ReceiptHandle=receipt_handle)
		except ClientError as e:
			print("There was an error deleting message the message from the SQS:", e)
			return abort(500)

	return "Success", 201


@app.errorhandler(404)
def page_not_found(e):
	return render_template('error.html', 
		title='Page not found', alert_level='warning',
		message="The page you tried to reach does not exist. \
			Please check the URL and try again."
		), 404

@app.errorhandler(405)
def not_allowed(e):
	return {
		'error': 'Not allowed', 
		'alert_level': 'warning',
		'message': "You attempted an operation that's not allowed; \
			get your act together, hacker!"
	}, 405

@app.errorhandler(500)
def internal_error(error):
	return {
		'error': 'Not allowed', 
		'alert_level': 'warning',
		'message': "You attempted an operation that's not allowed; \
			get your act together, hacker!"
	}, 500


### EOF
