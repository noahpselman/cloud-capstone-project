# GAS Framework
An enhanced web framework (based on [Flask](https://flask.palletsprojects.com/)) for use in the capstone project. Adds robust user authentication (via [Globus Auth](https://docs.globus.org/api/auth)), modular templates, and some simple styling based on [Bootstrap](https://getbootstrap.com/docs/3.3/).

Directory contents are as follows:
* `/web` - The GAS web app files
* `/ann` - Annotator files
* `/util` - Utility scripts/apps for notifications, archival, and restoration
* `/aws` - AWS user data files


## Analysis of Autoscaling Behavior

#### Scaling out of web

#### Scaling in of web

#### Scaling out of ann

#### Scaling in of ann


## Description of Various Processes
#### Archive Process
The archival process is initiated in ann/run.py.  If a user is a free user, run.py initiates a step function (nselman_archive).  The step function waits 5 minutes then publishes a notification in the sns topic nselman_archive.  The message contains the job_id and the user_id.  Two services are subscribed to the SNS:  a flask app running on the ec2 instance nselman_utils, and a sqs called nselman_archive.  The flask app receives up to 10 messages at a time from the sqs (in order to not fall behind in the case of many messages).  It then verifies the user is still free.  If so, it initiates an move from the s3 to glacier of the results file and updates the dynamo item corresponing to the job accordingly.

#### Restore Process
When a user upgrades to premium, a post is made to the /subscribe endpoint on the web-app.  That endpoint publishes a message to the SNS topic nselman_thaw.  Two services are subscribed to that topic:  a flask app run on and ec2 nselman_thaw, and an SQS called nselman_thaw.  The flask app reads the message from the queue and initiates a retrieval from the glacier archive.  Upon completion, the retrieval job publishes a message to the SNS topic, nselman_restore that contains the data required to read the retrieved job.  An SQS called nselman restore as well as a Lambda function called nselman_restore are subscribed to that SNS topic.  The Lambda function reads a message from the corresponding SQS, reads the retrieved results file, and puts it to results s3 at the same location where the results was initially stored after completion.




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

#### Load Testing
* https://blog.realkinetic.com/load-testing-with-locust-part-1-174040afdf23
* https://docs.locust.io/en/latest/quickstart.html



