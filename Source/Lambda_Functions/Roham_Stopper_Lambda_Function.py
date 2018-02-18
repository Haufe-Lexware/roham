#Roham is a an open-source tool which helps you to save cost on AWS by terminating/stopping/starting EC2 Instances based on schedule tags.
#This is 'Roham Stopper' - A Lambda function which stops EC2 Instances based on a schedule tag.
#The word 'Roham' refers to a well-known hero in Persian legends. It also literally means 'undefeatable'.

import boto3
import logging
import json
from croniter import croniter
from datetime import datetime, timedelta

#setup simple logging for INFO
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#ec2 = boto3.resource('ec2')
iam = boto3.resource('iam')
sts_client = boto3.client('sts')

#This is a function which returns a "yes" if today is a weekend and a "no" if it is not - weekend means Sat (00:00) until Sun (23:59)...
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
        RoleSessionName="Roham_Stopper"
    )

    credentials = assumed_role_object['Credentials']
        
    client = boto3.client(
    'ec2',
    aws_access_key_id = credentials['AccessKeyId'],
    aws_secret_access_key = credentials['SecretAccessKey'],
    aws_session_token = credentials['SessionToken'],
    )
            
    ec2_regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
        
    #The part below is the main part of the code which we look through every region for every instance
    for region in ec2_regions:
        conn = boto3.resource('ec2',
        region_name=region,
        aws_access_key_id = credentials['AccessKeyId'],
        aws_secret_access_key = credentials['SecretAccessKey'],
        aws_session_token = credentials['SessionToken'],
        )
        ec2c = boto3.client('ec2',
        region_name=region,
        aws_access_key_id = credentials['AccessKeyId'],
        aws_secret_access_key = credentials['SecretAccessKey'],
        aws_session_token = credentials['SessionToken'],
        )
        instances = conn.instances.filter()
    
        for instance in instances:
            instance_id = instance.id.split()
            print(instance.id, instance.instance_type, region)
            
            #The line below first checks if the instance is in the running state
            if (instance.state["Name"] == "running"):
                if instance.tags is not None:
                    weekendstop_tag_value = None
                    tostop_tag_value = None
                    for tag in instance.tags:
                        tag_key = tag["Key"].lower()
                        tag_value = tag["Value"].lower()
                        if tag_key == "weekendstop":
                            weekendstop_tag_value = tag_value
                        if tag_key == "tostop":
                            tostop_tag_value = tag_value
                    #This section below checks if today is weekend and if it is a weekend and the weekendstop tag is set to yes, the instance will be stopped
                    if(is_today_weekend()):
                        if weekendstop_tag_value is not None:
                            if weekendstop_tag_value == "yes":
                                ec2c.stop_instances(InstanceIds=instance_id)
                                print("Instance was stopped by Roham...")
                                break
                            elif weekendstop_tag_value == "no":
                                print("Instance was tagged not to stop over the weekend...")
                            else:
                                print("Instance has an incorrect/does not have a weekendstop tag. Roham Tagger service will correct it if needed...")
                        else:
                            print("Instance does not have a weekendstop tag. Roham Tagger service will correct it if needed...")
                    # If the instance has the tostop Tag, and the tag value is not / but a valid cron expression, check if the time to stop is close and stop it
                    if tostop_tag_value is not None:
                        if croniter.is_valid(tostop_tag_value) and ('/' not in tostop_tag_value) and tostop_tag_value != "no":
                            # The cron expression shows the time the Instance needs to stop. The difference between the previous event of the cron expression and the time NOW is calculated and if it
                            # is smaller than 75 minutes, the Instance will be stopped.
                            prev_runtime = croniter(tostop_tag_value, datetime.now()).get_prev(datetime)
                            time_difference = datetime.now() - prev_runtime
                            minutes_after_stop_tag = timedelta(minutes=75)
                            if (time_difference < minutes_after_stop_tag):
                                ec2c.stop_instances(InstanceIds=instance_id)
                                print("Instance was stopped by Roham...")
                            else:
                                print("Instance was tagged to stop at a different time...")
                        else:
                            print("Instance has an incorrect tostop tag or the tostop tag is configured to 'NO'...")
                    else:
                        print("Instance does not have a tostop tag...")
                else:
                    print("Instance does not have any tags...")
            else:
                print("Instance is already stopped...")