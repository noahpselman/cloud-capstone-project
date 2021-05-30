# GAS Framework
An enhanced web framework (based on [Flask](https://flask.palletsprojects.com/)) for use in the capstone project. Adds robust user authentication (via [Globus Auth](https://docs.globus.org/api/auth)), modular templates, and some simple styling based on [Bootstrap](https://getbootstrap.com/docs/3.3/).

Directory contents are as follows:
* `/web` - The GAS web app files
* `/ann` - Annotator files
* `/util` - Utility scripts/apps for notifications, archival, and restoration
* `/aws` - AWS user data files



## Sources:

#### SQS
* https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#client

#### S3
* https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
* https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html
* https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-download-file.html
* https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
* https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html


#### Dynamo DB
* https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#client
 
 
#### Glacier
* https://botocore.amazonaws.com/v1/documentation/api/latest/reference/services/glacier.html#client
* https://docs.aws.amazon.com/code-samples/latest/catalog/python-glacier-retrieve_inventory_initiate.py.html
* https://docs.aws.amazon.com/code-samples/latest/catalog/python-glacier-retrieve_inventory_results.py.html


#### Stripe
* https://stripe.com/docs/api/customers
* https://stripe.com/docs/api/subscriptions/create

#### Step functions
* https://aws.amazon.com/step-functions/?step-functions.sort-by=item.additionalFields.postDateTime&step-functions.sort-order=desc
* https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html
* https://www.youtube.com/watch?v=s0XFX3WHg0w


#### Lambda
* https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html
