#Roham is a an open-source tool which helps you to save cost on AWS by terminating/stopping/starting EC2 Instances based on schedule tags.
#This is 'Roham Starter' - A Lambda function which starts EC2 Instances based on a schedule tag.
#The word 'Roham' refers to a well-known hero in Persian legends. It also literally means 'undefeatable'.

import boto3
import logging
import json
from croniter import croniter
from datetime import datetime, timedelta

# setup simple logging for INFO
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Definitions
ec2 = boto3.resource('ec2')
iam = boto3.resource('iam')
sts_client = boto3.client('sts');

def is_today_weekend():
    day_of_the_Week = datetime.today().isoweekday()
    if((day_of_the_Week > 5)):
        return True
    else:
        return False

def lambda_handler(event, context):
    # The lines below receive and interpret the json parameters passed to the Lambda function from another account.
    # In this function only one of the parameters is important: 'rolearn' which is
    # the role in the other account to be assumed by Lambda
    sns_message_json = event["Records"][0]["Sns"]["Message"]
    print(sns_message_json)
    sns_message = json.loads(sns_message_json)
    role_to_assume = sns_message["rolearn"]

    # For a future feature implementation
    # account_type = sns_message["account_type"]

    # This is where the Lambda function assumes the role (which is passed to it) to be able to run commands in the other AWS account
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_to_assume,
        RoleSessionName="Roham_Starter"
    )

    credentials = assumed_role_object['Credentials']

    ec2_client = boto3.client(
        'ec2',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
    )
    
    ec2_regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    # The part below is the main part of the code which we look through every region for every instance
    for region in ec2_regions:
        conn = boto3.resource('ec2',
                                region_name=region,
                                aws_access_key_id=credentials['AccessKeyId'],
                                aws_secret_access_key=credentials['SecretAccessKey'],
                                aws_session_token=credentials['SessionToken'],
                                )
        ec2c = boto3.client('ec2',
                            region_name=region,
                            aws_access_key_id=credentials['AccessKeyId'],
                            aws_secret_access_key=credentials['SecretAccessKey'],
                            aws_session_token=credentials['SessionToken'],
                            )
        instances = conn.instances.filter()
    
        for instance in instances:
            instance_id = instance.id.split()
            print(instance.id, instance.instance_type, region)
    
            # check if the instance is in the stopped state
            if (instance.state["Name"] == "stopped"):
                if instance.tags is not None:
                    weekendstop_tag_value = None
                    tostart_tag_value = None
                    for tag in instance.tags:
                        tag_key = tag["Key"].lower()
                        tag_value = tag["Value"].lower()
                        if tag_key == "weekendstop":
                            weekendstop_tag_value = tag_value
                        if tag_key == "tostart":
                            tostart_tag_value = tag_value
                    # If today is a weekend and the weekendstop tag is set to yes, then it does not check for the tostart tag because the instance is supposed to be off (stopped)
                    if(is_today_weekend() and weekendstop_tag_value == "yes"):
                        print("It is a weekend today and the weekendstop tag value is YES, so there is no need to start this Instance...")
                    else:
                        # If the instance has the tostart Tag, and the tag value is not / but a valid cron expression, check if the time to start is close and start it
                        if tostart_tag_value is not None:
                            if croniter.is_valid(tostart_tag_value) and ('/' not in tostart_tag_value) and tostart_tag_value != "no":
                                # The cron expression shows the time the Instance needs to start. The difference between the next event of the cron expression and the time NOW is calculated and if it
                                # is smaller than 75 minutes, the Instance will be started.
                                next_runtime = croniter(tostart_tag_value, datetime.now()).get_next(datetime)
                                time_difference = next_runtime - datetime.now()
                                minutes_before_start_tag = timedelta(minutes=75)
                                if (time_difference < minutes_before_start_tag):
                                    ec2c.start_instances(InstanceIds=instance_id)
                                    print("Instance was started by Roham...")
                                else:
                                    print("Instance was tagged to start at a different time...")
                            else:
                                print("Instance has an incorrect tostart tag or the tostart tag is configured to 'NO'...")
                        else:
                            print("Instance does not have a tostart tag...")
                else:
                    print("Instance does not have any tags...")
            else:
                print("Instance is already running...")