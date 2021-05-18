# run.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Wrapper script for running AnnTools
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'



import time
import sys
import boto3
import os
import json
import uuid
from shutil import rmtree
from botocore.config import Config
from botocore.exceptions import ClientError

# Get configuration
from configparser import ConfigParser
config = ConfigParser(os.environ)
config.read('config.ini')

REGION = config['aws']['AwsRegionName']
SIG_VERSION = config['aws']['SignatureVersion']
ANNTOOLS_PATH = config['local']['AnnTools']
DYNAMO_TABLENAME = config['aws']['DynamoTablename']
RESULTS_SNS = config['aws']['ResultsTopicARN']
STEP_FUNCTION = config['aws']['StepFunctionArchive']
GAS_URL = config['gas']['GASurl']
sys.path.append(ANNTOOLS_PATH)

import driver

OUTPUT_DIR = config['local']['OutputDirectory']
OUTPUT_BUCKET = config['aws']['ResultsBucket']
OUTPUT_KEY_ROOT = config['aws']['ResultsBucketKey']

"""
A rudimentary timer for coarse-grained profiling
"""
class Timer(object):
	def __init__(self, verbose=True):
		self.verbose = verbose

	def __enter__(self):
		self.start = time.time()
		return self

	def __exit__(self, *args):
		self.end = time.time()
		self.secs = self.end - self.start
		if self.verbose:
			print(f"Approximate runtime: {self.secs:.2f} seconds")

if __name__ == '__main__':
	# Call the AnnTools pipeline
	print("sys args:::", sys.argv)
	if len(sys.argv) > 1:
		with Timer():
			input_filepath = sys.argv[1]
			driver.run(input_filepath, 'vcf')
			data = input_filepath.split('/')
			input_filename = data[-1]
			job_id = data[-2]
			user_id = data[-3]
			log_filename = input_filename + '.count.log'
			annot_filename = input_filename[:-4] + '.annot.vcf'
			# user = input_filename.split('~')[0]

			# put files in gas-results
			s3_client = boto3.client('s3', 
									 region_name=REGION, 
									 config=Config(signature_version=SIG_VERSION))
			
			for f in (log_filename, annot_filename):
				with open(f'{OUTPUT_DIR}/{user_id}/{job_id}/{f}', 'rb') as content:
					try:
						response = s3_client.put_object(
							Bucket=OUTPUT_BUCKET, 
							Key=f'{OUTPUT_KEY_ROOT}/{user_id}/{f}', 
							Body=content
						)
					except ClientError as e:
						print("There was an issue putting the annotations results in the s3:", e)
						raise
					if response['ResponseMetadata']['HTTPStatusCode'] == 200:
						continue
					else:
						print(f"the following file was not found after the analysis and thus not moved to the s3: {f}")
					
			# update dynamo
			new_data = {
				"job_status": {"S": "COMPLETED"} ,
				"complete_time": {"N": str(time.time())},
				"s3_results_bucket": {"S": OUTPUT_BUCKET},
				"s3_key_log_file": {"S": f"{OUTPUT_KEY_ROOT}/{user_id}/{log_filename}"},
				"s3_key_result_file": {"S": f"{OUTPUT_KEY_ROOT}/{user_id}/{annot_filename}"},
				"archive_status": {"S": "NOT_ARCHIVED"}
			}

			expression_items = []
			expression_vals = {}
			for k, v in new_data.items():
				expression_items.append(f"{k} = :new_{k}")
				expression_vals[f":new_{k}"] = v

			update_expression = f"SET {', '.join(expression_items)}"
			# exp_attr_vals = {
			#   ':new_job_status': {'S': job_status},
			#   ':new_complete_time': {'N': complete_time}
			# }
			try:
				dynamo_client = boto3.client('dynamodb', region_name=REGION)
				response = dynamo_client.update_item(TableName=DYNAMO_TABLENAME, 
																							Key={'job_id': {'S': job_id}}, 
																							UpdateExpression=update_expression,
																							ExpressionAttributeValues=expression_vals)
			except ClientError as e:
				print("There was an issue uploading the results to the Dynamo Table:", e)
				raise
			if response['ResponseMetadata']['HTTPStatusCode'] == 200:
				pass
			else:
				print(f"There was a response with an HTTPStatusCode of {response['ResponseMetadata']['HTTPStatusCode']} after uploading to Dynamo")

			# Send message to request queue
			LINK = f"{GAS_URL}/annotations/{job_id}"
			message = json.dumps({
				'user_id': user_id,
				'job_id': job_id,
				'link': LINK
			})
			try:
				print("sending to the jobs queue")
				sns_client = boto3.client("sns", region_name=REGION)
				sns_response = sns_client.publish(TopicArn=RESULTS_SNS, Message=message)
			except ClientError as e:
				print("problem publishing message to results sns:", e)

			# Execute step function to archive
			try:
				attributes = ['user_role', "s3_key_result_file"]
				response = dynamo_client.get_item(TableName=DYNAMO_TABLENAME,
									   Key={'job_id': {'S': job_id}},
									   AttributesToGet=attributes)
				items = response['Item']
				user_role = list(items['user_role'].values())[0]
				s3_key_result_file = list(items['s3_key_result_file'].values())[0]
			except ClientError as e:
				print("problem retreving user role:", e)


			print("the user role is:", user_role)	

			if user_role == "free_user":
				message = {
					"user_id": user_id,
					"job_id": job_id,
					"s3_key_result_file": s3_key_result_file
				}
				try:
					step_client = boto3.client('stepfunctions', region_name=REGION)					
					response = step_client.start_execution(
						stateMachineArn=STEP_FUNCTION,
						name=str(uuid.uuid1()),
						input=json.dumps(message)
						)
				except ClientError as e:
					print('problem starting step function')
					

			# Remove directory
			rmtree(f'{OUTPUT_DIR}/{user_id}/{job_id}')
			if not os.listdir(f'{OUTPUT_DIR}/{user_id}'):
				rmtree(f'{OUTPUT_DIR}/{user_id}')
			print('done')
					
	else:
		print("A valid .vcf file must be provided as input to this program.")

### EOF