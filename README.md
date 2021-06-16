# GAS Framework
An enhanced web framework (based on [Flask](https://flask.palletsprojects.com/)) for use in the capstone project. Adds robust user authentication (via [Globus Auth](https://docs.globus.org/api/auth)), modular templates, and some simple styling based on [Bootstrap](https://getbootstrap.com/docs/3.3/).

Directory contents are as follows:
* `/web` - The GAS web app files
* `/ann` - Annotator files
* `/util` - Utility scripts/apps for notifications, archival, and restoration
* `/aws` - AWS user data files

** Note: The AWS and Globus Accounts behind this project are no longer in service. **

## Project Description

The GAS (Gene Annotation Service) framework allows user to submit and view results of gene annotations jobs.  Users can be free or premium.  Free results for free users are archieved soon after completion whereas premium users' results are stored in perpetuity.  The framework is built as a distributed system described by the following chart.

!()[imagesdistributed-system.png]

Notice how messages between ec2 groups are persisted using SNS and SQS.  This allows the system to be fault tolerent.  EC2 instances running the web server and annotation server are members of auto-scaling groups that add/remove instances dependent on usage metrics.

Globus is used for authentication and Stripe is used to handle credit card verification (of course only fake cards are used for the demo).  



## Analysis of Autoscaling Behavior
Locusts were used to test the autoscaling behavior.  Below is an analysis of how the tests played out.

#### Scaling out of web
The autoscaling of the web group went as expected.  After unleashing the locusts, the group added an instance every 5 minutes.  As the number of requests did not subside, this continued until the group reached 10 instances, it's maximum.  The  process was monotonic in that at no point did it remove an instance.  This may have been possible since the alarm to scale in uses target wait time as its metric.  Had the requests come back quicker, there may have been conflicting instructions from either alarm (as happened to some of my classmates).  These observations underlie a reason that the request count may not be an optimal metric for scaling up.  Receiving a high number of requests is only harmful to our system insofar as it impacts the user experience (defined broadly).  Therefore, other metrics may be appropriate for scaling out, such as target response time.  Because various endpoints are associated with vastly different workloads, other metrics may better capture important information like processed bytes.

#### Scaling in of web
Like the scaling out, the scaling in worked as expected.  After the locusts were stopped, the group removed instances one by one until it reached the minimum of 2.  The target response time of such a small value would be fine if all pages were as simple as our home page.  However, that's not the case.  Some of our pages take a number of seconds to complete, even when healthy (I'm thinking of things like submitting a presigned post of a large input file).  Here a request count actually feels more appropriate because the number of instances will not be a bottle neck if there is a low instance count. 


Here are the graphs.
elb-load-test-locust
#### Scaling out of ann
![](/images/elb-load-test-locust.PNG)
![](/images/elb-load-test.PNG)
![](/images/elb-load-test1.PNG)

#### Scaling in of annotator

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

##### Important Note:  This project was designed by my instructor, Vas Vasiliadis.  Much of the boilerplace code, html, and server management code was written by him.

