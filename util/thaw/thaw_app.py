# thaw_app.py
#
# Thaws upgraded (premium) user data
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import json
import os
import sys
import boto3


# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

from flask import Flask, request, abort
from botocore.exceptions import ClientError

app = Flask(__name__)
environment = 'thaw_app_config.Config'
app.config.from_object(environment)
app.url_map.strict_slashes = False


@app.route('/', methods=['GET'])
def home():
	return (f"This is the Thaw utility: POST requests to /thaw.")

@app.route('/thaw', methods=['POST'])
def thaw_premium_user_data():

	# get message and extra user_id
	try:

		data = json.loads(request.data)
		# message = json.loads(data['Message'])
		# user_id = message['user_id']
		# print("user_id is", user_id)
		topic_arn = data["TopicArn"]
	except KeyError as e:
		print("invalid inputs:", e)
		abort(500)

	# making sure endpoing is being triggered from correct place
	if topic_arn != app.config['AWS_THAW_SNS']:
		abort(403)

	try:
		sqs_client = boto3.client("sqs", region_name=app.config['AWS_REGION_NAME'])
	except ClientError as e:
		print(f"Problem connecting to SQS:", e)
		return abort(500)

	try:
		print("Receiving messages...")
		response = sqs_client.receive_message(
			QueueUrl=app.config['AWS_THAW_QUEUE'], 
			MaxNumberOfMessages=10, 
			WaitTimeSeconds=20)
	except ClientError as e:
		print("Problem receiving messages:", e)
	try:
		messages = response['Messages']
	except KeyError as e:
		print(f"No messages found:", e)
		return abort(500)

	for message in messages:
		try:
			receipt_handle = message['ReceiptHandle']
			body = json.loads(message['Body'])
			content = json.loads(body['Message'])
			user_id = content['user_id']
		except KeyError as e:
			print(f"Message does not contain required data: {e}" )
			delete_message(sqs_client, receipt_handle)
			continue

		# make sure user is premium
		user_role = helpers.get_user_profile(user_id)['role']
		if user_role != 'premium_user':
			print(f"User {user_id} is not premium.")
			delete_message(sqs_client, receipt_handle)
			continue

		try:
			print("Getting user jobs from Dynamo Table...")
			dynamo_client = boto3.client('dynamodb', region_name=app.config['AWS_REGION_NAME'])
			response = dynamo_client.query(TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
										KeyConditions={'user_id': {'AttributeValueList': [{'S': user_id}], 
													'ComparisonOperator': 'EQ'}},
										QueryFilter={'archive_status': {'AttributeValueList': [{'S': 'ARCHIVED'}],
													'ComparisonOperator': 'EQ'},
													'retrieval_status': {'AttributeValueList': [{'S': 'NOT_RETRIEVED'}],
													'ComparisonOperator': 'EQ'}},
										IndexName='user_id_index', 
										AttributesToGet=['archive_id', 'archive_status', 'job_id'])
			items = response['Items']

		except ClientError as e:
			print("Failed to get user jobs:", e)
			print("Skipping...")
			continue

		params = {
			'Type': 'archive-retrieval',
			'SNSTopic': app.config['AWS_RESTORE_SNS']
		}

		print(f"number of jobs for user: {len(items)}")

		for item in items:

			# extract glacier id
			try:
				print("Extracting archive id...")
				archive_status = list(item['archive_status'].values())[0]
				if archive_status != 'ARCHIVED':
					continue
				archive_id = list(item['archive_id'].values())[0]
				job_id = list(item['job_id'].values())[0]
			except KeyError:
				print("Could not extract correct data:", e)
				print("Skipping...")
				continue

			print("Processing message for job_id:", job_id)

			params['ArchiveId'] = archive_id
			params['Description'] = json.dumps({'job_id': job_id})
			params['Tier'] = 'Expedited'

			# initiate job
			try:
				print("Initiating glacier retrieval...")
				glacier_client = boto3.client('glacier', region_name=app.config['AWS_REGION_NAME'])
				response = glacier_client.initiate_job(
					accountId='-',
					vaultName=app.config['AWS_VAULT_NAME'],
					jobParameters=params)
			except glacier_client.exceptions.InsufficientCapacityException:
				print('Insufficient capacity to run Expedited retrival')
				try:
					print("Trying standard retrieval...")
					params['Tier'] = 'Standard'
					response = glacier_client.initiate_job(
						accountId='-',
						vaultName=app.config['AWS_VAULT_NAME'],
						jobParameters=params)
					
					retrieval_id = response['jobId']
				except ClientError as e:
					print('There was an error retriving archive:', e)
					print("Skipping...")

			# update dynamo
			print("Updating Dynamo table with restore job id...")
			new_data = {"retrieval_status": {"S": "RETRIEVING"}}
			update_expression = "SET retrieval_status = :new_retrieval_status, retrieval_id = :new_retrieval_id"
			expression_vals = {":new_retrieval_id": {"S": retrieval_id}, 
							":not_retrieved": {"S": "NOT_RETRIEVED"},
							":new_retrieval_status": {'S': 'RETRIEVING'}}
			condtion_expression = "retrieval_status = :not_retrieved"
			try:
				dynamo_client = boto3.client('dynamodb', region_name=app.config['AWS_REGION_NAME'])
				response = dynamo_client.update_item(TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
														Key={'job_id': {'S': job_id}}, 
														UpdateExpression=update_expression,
														ExpressionAttributeValues=expression_vals,
														ConditionExpression=condtion_expression)
			except ClientError as e:
				print("There was an issue uploading the results to the Dynamo Table:", e)
				print("Skipping...")
				continue

		# delete message
		delete_message(sqs_client, receipt_handle)

		return 200

def delete_message(sqs_client, receipt_handle):
	try:
		print("Deleting message...")
		sqs_client.delete_message(QueueUrl=app.config['AWS_THAW_QUEUE'], 
								ReceiptHandle=receipt_handle)
	except ClientError as e:
		print("There was an error deleting message the message from the SQS:", e)

	return True



@app.errorhandler(403)
def forbidden(e):
	return render_template('error.html',
		title='Not authorized', alert_level='danger',
		message="You are not authorized to access this page. \
			If you think you deserve to be granted access, please contact the \
			supreme leader of the mutating genome revolutionary party."
		), 403

@app.errorhandler(500)
def internal_error(error):
	return render_template('error.html',
		title='Server error', alert_level='danger',
		message="The server encountered an error and could \
			not process your request."
		), 500

### EOF
