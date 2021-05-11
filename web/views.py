# views.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Application logic for the GAS
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import uuid
import time
import json
from datetime import datetime

import boto3
from botocore.client import Config
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from flask import (abort, flash, redirect, render_template, 
	request, session, url_for)

from gas import app, db
from decorators import authenticated, is_premium

"""Start annotation request
Create the required AWS S3 policy document and render a form for
uploading an annotation input file using the policy document

Note: You are welcome to use this code instead of your own
but you can replace the code below with your own if you prefer.
"""
@app.route('/annotate', methods=['GET'])
@authenticated
def annotate():
	# Open a connection to the S3 service
	s3 = boto3.client('s3', 
		region_name=app.config['AWS_REGION_NAME'], 
		config=Config(signature_version='s3v4'))

	bucket_name = app.config['AWS_S3_INPUTS_BUCKET']
	user_id = session['primary_identity']
	print("user_Id", user_id)

	# Generate unique ID to be used as S3 key (name)
	job_id = str(uuid.uuid4())
	key_name = '/'.join([app.config['AWS_S3_KEY_PREFIX'], user_id, job_id + "~${filename}"])

	# Create the redirect URL
	redirect_url = f"{request.url}/job"

	# Define policy conditions
	encryption = app.config['AWS_S3_ENCRYPTION']
	acl = app.config['AWS_S3_ACL']
	fields = {
		"success_action_redirect": redirect_url,
		"x-amz-server-side-encryption": encryption,
		"acl": acl
	}
	conditions = [
		["starts-with", "$success_action_redirect", redirect_url],
		{"x-amz-server-side-encryption": encryption},
		{"acl": acl}
	]

	# Generate the presigned POST call
	try:
		presigned_post = s3.generate_presigned_post(
			Bucket=bucket_name, 
			Key=key_name,
			Fields=fields,
			Conditions=conditions,
			ExpiresIn=app.config['AWS_SIGNED_REQUEST_EXPIRATION'])
	except ClientError as e:
		app.logger.error(f'Unable to generate presigned URL for upload: {e}')
		return abort(500)

	# Render the upload form which will parse/submit the presigned POST
	return render_template('annotate.html',
		s3_post=presigned_post,
		role=session['role'])


"""Fires off an annotation job
Accepts the S3 redirect GET request, parses it to extract 
required info, saves a job item to the database, and then
publishes a notification for the annotator service.

Note: Update/replace the code below with your own from previous
homework assignments
"""
@app.route('/annotate/job', methods=['GET'])
@authenticated
def create_annotation_job_request():

	region = app.config['AWS_REGION_NAME']

	# Parse redirect URL query parameters for S3 object info
	bucket_name = request.args.get('bucket')
	s3_key = request.args.get('key')
	print(s3_key)

	# Extract the job ID from the S3 key
	[key_root, user_id, s3_input_file] = s3_key.split('/')
	[job_id, input_file_name] = s3_input_file.split('~')


	# Creating data
	dynamo_data = { 
		"job_id": {'S': job_id},
		"user_id": {'S': user_id},
		"input_file_name": {'S': input_file_name},
		"s3_inputs_bucket": {'S': bucket_name},
		"s3_key_input_file": {'S': s3_key},
		"submit_time": {'N': str(time.time())},
		"job_status": {'S': "PENDING"}
		}
	
	message_data = {k: list(v.values())[0] for (k, v) in dynamo_data.items()}

	# Send message to request queue
	try:
		sns_client = boto3.client("sns", region_name=region)
		sns_response = sns_client.publish(TopicArn=app.config['AWS_SNS_JOB_REQUEST_TOPIC'], Message=json.dumps(message_data))
	except ClientError as e:
		print(e)
		app.logger.error(f'Problem publishing SNS message: {e}')
		return abort(500)

	# Persist job to database
	try:
		dynamo_client = boto3.client("dynamodb", 
								region_name=region)
		put_response = dynamo_client.put_item(TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], Item=dynamo_data)
	except ClientError:
		print(e)
		app.logger.error(f'Problem putting data in Dynamo DB: {e}')
		return abort(500)


	return render_template('annotate_confirm.html', job_id=job_id)


"""List all annotations for the user
"""
@app.route('/annotations', methods=['GET'])
@authenticated
def annotations_list():

	# Get list of annotations to display
	
	return render_template('annotations.html', annotations=None)


"""Display details of a specific annotation job
"""
@app.route('/annotations/<id>', methods=['GET'])
@authenticated
def annotation_details(id):
	pass


"""Display the log file contents for an annotation job
"""
@app.route('/annotations/<id>/log', methods=['GET'])
@authenticated
def annotation_log(id):
	pass


"""Subscription management handler
"""
import stripe
from auth import update_profile

@app.route('/subscribe', methods=['GET', 'POST'])
@authenticated
def subscribe():
	if (request.method == 'GET'):
		# Display form to get subscriber credit card info
		pass
		
	elif (request.method == 'POST'):
		# Process the subscription request

		# Create a customer on Stripe

		# Subscribe customer to pricing plan

		# Update user role in accounts database

		# Update role in the session

		# Request restoration of the user's data from Glacier
		# ...add code here to initiate restoration of archived user data
		# ...and make sure you handle files not yet archived!

		# Display confirmation page
		pass


"""Set premium_user role
"""
@app.route('/make-me-premium', methods=['GET'])
@authenticated
def make_me_premium():
	# Hacky way to set the user's role to a premium user; simplifies testing
	update_profile(
		identity_id=session['primary_identity'],
		role="premium_user"
	)
	return redirect(url_for('profile'))


"""Reset subscription
"""
@app.route('/unsubscribe', methods=['GET'])
@authenticated
def unsubscribe():
	# Hacky way to reset the user's role to a free user; simplifies testing
	update_profile(
		identity_id=session['primary_identity'],
		role="free_user"
	)
	return redirect(url_for('profile'))


"""DO NOT CHANGE CODE BELOW THIS LINE
*******************************************************************************
"""

"""Home page
"""
@app.route('/', methods=['GET'])
def home():
	return render_template('home.html')

"""Login page; send user to Globus Auth
"""
@app.route('/login', methods=['GET'])
def login():
	app.logger.info(f"Login attempted from IP {request.remote_addr}")
	# If user requested a specific page, save it session for redirect after auth
	if (request.args.get('next')):
		session['next'] = request.args.get('next')
	return redirect(url_for('authcallback'))

"""404 error handler
"""
@app.errorhandler(404)
def page_not_found(e):
	return render_template('error.html', 
		title='Page not found', alert_level='warning',
		message="The page you tried to reach does not exist. \
			Please check the URL and try again."
		), 404

"""403 error handler
"""
@app.errorhandler(403)
def forbidden(e):
	return render_template('error.html',
		title='Not authorized', alert_level='danger',
		message="You are not authorized to access this page. \
			If you think you deserve to be granted access, please contact the \
			supreme leader of the mutating genome revolutionary party."
		), 403

"""405 error handler
"""
@app.errorhandler(405)
def not_allowed(e):
	return render_template('error.html',
		title='Not allowed', alert_level='warning',
		message="You attempted an operation that's not allowed; \
			get your act together, hacker!"
		), 405

"""500 error handler
"""
@app.errorhandler(500)
def internal_error(error):
	return render_template('error.html',
		title='Server error', alert_level='danger',
		message="The server encountered an error and could \
			not process your request."
		), 500

### EOF