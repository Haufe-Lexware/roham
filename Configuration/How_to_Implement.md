# Introduction
This guide will walk you through all the steps to implement Roham in your AWS environment. I have tried to cover every small step to achieve a full working setup. If you have any questions, simply send me an email on Esmaeil.Sarabadani@haufe-lexware.com and ask, I try my best to respond in a timely manner. However my biggest advice is to make sure you read this documentation thoroughly first before asking your question, becasue there are many points which you might have already missed. 

The goal of this guide is to have the diagram below implemented for every single component of Roham (Tagger, Stopper, Starter, Terminator):

<p align="center">
  <img width="824" height="363" src="https://github.com/Haufe-Lexware/roham/blob/master/Images/small-picture.png">
</p>

So as shown in the diagram above, Roham will be implemented on a central Shared Services AWS Account and manages EC2 Instances in other AWS Accounts. Roham has two different categories for the other AWS Accounts which it manages:

| AWS Account | Purpose |
|:---:|:---|
| Development | This is your project development environment. This is where you need to manage your cost. This could also be a production environment. EC2 Instances here are never automatically tagged to Terminate by Roham Tagger.  |
| Playground | This is an AWS Account where developers play around and learn. In many companies the costs in such Accounts increase really fast. EC2 Instances here are automatically tagged to Terminate by Roham Tagger unless they are manually tagged not to. |

# Steps Overview
Assuming that you have already a Shared Services AWS Account as well as a Development/Playground Account ready, follow this guide and take the following steps below:

#### Phase 1 - On the Shared Resources AWS Account:
  1. Create an IAM Role and Policy which assigns Lambda the permission to execute commands
  2. Create a separate Lambda function for Roham Tagger, Stopper, Starter, and Terminator respectively
  
#### Phase 2 - On the Development/Playground AWS Account:
  1. Create an IAM Role and Policy to allow cross-account access to EC2 Instances
  2. Create a separate SNS Topic for the Roham Tagger, Stopper, Starter, and Terminator Lambda functions respectively
  3. Assign the SNS Topic permission to allow the Shared Services AWS Account to use it
  4. Create a separate CloudWatch Rule for each SNS Topic created in the step above and make sure it publishes a message to its respective SNS Topic on a regular interval.
  
#### Phase 3 - On the Shared Resources AWS Account:
  1. Subscribe the Lambda functions to their respective SNS Topic in the Development/Playground AWS Account
  2. Allow the created Lambda functions to be executed by the SNS Topic in the other Development/Playground AWS Accounts

> Make sure you have AWS CLI on your PC/Mac. In this example the Shared Services AWS Account ID is 111111111111 and the Project1 AWS Account ID is 222222222222. 

# Phase 1 - On the Shared Resources AWS Account
### Create IAM Role and Policy
Create a custom IAM Policy with the following JSON content and name it Roham_Policy_Master:
```sh
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*"
        }
    ]
}
```
Create a custom IAM Role with the following JSON content and name it Roham_Role_Master:
```sh
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
### Create a separate Lambda function for each Roham component
Download the function zip files from [here](https://github.com/Haufe-Lexware/roham/tree/master/Source/Lambda_Packages)
You will need to repeat the steps below one at a time for each of these four packages. let's say first we do it for Roham Tagger. Run the following AWS CLI command to create the Lambda function:
```sh
aws lambda create-function --function-name Roham_Tagger --runtime python3.6 --role arn:aws:iam::111111111111:role/Roham_Role_Master --handler lambda_function.lambda_handler --timeout 300 --zip-file fileb://"C:\Users\esmaeil\Desktop\Roham\Functions\Tagger\Roham_Tagger_Lambda.zip" --profile shared --region eu-central-1
```

# Phase 2 - On the Development/Playground AWS Account:
### Create IAM Role and Policy
Create a custom IAM Policy with the following JSON content and name it Roham_Policy_Managed:
```sh
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "sns:*",
                "ec2:*"
            ],
            "Resource": "*"
        }
    ]
}
```
Create a custom IAM Role with the following JSON content and name it Roham_Role_Managed:
```sh
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {}
    }
  ]
}
```
### Create a separate SNS Topic for each Roham component
You will need to run the command below three more times for the other three components of Roham (Stopper, Starter, Terminator)
```sh
aws sns create-topic --name Roham_Tagger --region eu-central-1
```

### Assign the SNS Topic permission
```sh
aws sns add-permission --region eu-central-1 --topic-arn arn:aws:sns:eu-central-1:222222222222:test --label lambda-access --aws-account-id 111111111111 --action-name Subscribe ListSubscriptionsByTopic Receive
```

### Create a separate CloudWatch Rule for each SNS Topic
So here we create the CloudWatch Rule which:
  - Publishes an SNS Message to the SNS Topic subscribers
  - Lambda received the message and is therefore executed
  - The message contains the IAM Role ARN (Roham_Rold_Managed) and the Account type (playground/dev)
  - Roham Lambda functions assume this Role and are therefore able to manage EC2 Instances in that AWS Account

```sh
aws events put-rule --name Roham_Tagger --schedule-expression "cron(30 * * * ? *)" --state DISABLED --region eu-central-1
```
> Please take note the cron expression above follows the AWS cron format and has nothing to do with the way we use cron expressions to schedule Roham.

## What should be your AWS CloudWatch Rule Schedule cron expression?
It is a very important question and might be a bit confusing at first. The CloudWatch Rule Schedule cron expression is completely different from Roham cron expression tags you assign to your EC2 Instances. To understand CloudWatch Schedule cron expressions, please [visit this page](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html) which follows a completely different format. 

We sugest the following values for the CloudWatch Rule Schedules:

| CloudWatch Rule | Cron Expression | Definition | Reason |
|:---:|:---:|:---|:---|
| Roham_Starter | 30 * * * ? * | Every hour of every day on the minute 30 | It is best to check the "tostart" tags on EC2 Instances every hour. It is also suggested to configure it on the minute 30 in case of any delay in Lambda function execution. |
| Roham_Stopper | 30 * * * ? * | Every hour of every day on the minute 30 | It is best to check the "tostop" tags on EC2 Instances every hour. It is also suggested to configure it on the minute 30 in case of any delay in Lambda function execution. |
| Roham_Tagger | 0 0/6 * * ? * | Every day once at 16:30 | It is best to check tagging compliance only few times per day. |
| Roham_Terminator | 15 0 ? * SAT-SUN * | Every Saturday and Sunday at 00:15 | Roham Terminator does NOT use cron expression tags to terminates EC2 Instances. As long as the "toterminate" tag is set to yes, the Instance becomes eligible for termination. So as soon as the CloudWatch Event is executed, all Instances with this tag get terminated. So the best time is at the beginning of every Saturday or Sunday. |

Now we need to add a target (SNS Topic) to our CloudWatch Rule. There is no simple way to do it via the AWS CLI. So I show you how to do this single step using the AWS Console.
Open the Console -> Oen the CloudWatch Rules -> Select the your Rule -> Click Actions -> Click Edit:

<p align="center">
  <img width="1000" height="340" src="https://github.com/Haufe-Lexware/roham/blob/master/Images/rule-edit.png">
</p>

Click Add Target. Select and add your SNS Topic and click Configure input -> select Constant and add the following JSON string:
```sh
{ "rolearn": "arn:aws:iam::222222222222:role/Roham_Role", "account_type": "dev" }
```
<p align="center">
  <img width="1000" height="383" src="https://github.com/Haufe-Lexware/roham/blob/master/Images/rule-edit-2.png">
</p>

Click Configure details and then click Update rule.

# Phase 3 - On the Shared Resources AWS Account:
### Subscribe the Lambda functions to their respective SNS Topic
Now we need to make sure each of the four Lambda functions is subscribed to their respective SNS Topic. You need to run this AWS CLI command:
```sh
aws sns subscribe --topic-arn arn:aws:sns:eu-central-1:222222222222:Roham_Tagger --protocol lambda --notification-endpoint arn:aws:lambda:eu-central-1:111111111111:function:Roham_Tagger --region eu-central-1
```
### Allow the created Lambda functions to be executed by the SNS Topic
Now we need to assign the Lambda function permission to be executed by the SNS Topic in the other AWS Account:
```sh
aws lambda add-permission --function-name Roham_Tagger --statement-id rohamtagger-1 --action "lambda:InvokeFunction" --principal sns.amazonaws.com --source-arn arn:aws:sns:eu-central-1:265722387297:Roham_Tagger --region eu-central-1
```

If you reached up to here successfully, it means you are done with implementing Roham and now you can sit back and enjoy saving costs...
