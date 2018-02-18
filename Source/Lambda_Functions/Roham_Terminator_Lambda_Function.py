#Roham is a an open-source tool which helps you to save cost on AWS by terminating/stopping/starting EC2 Instances based on schedule tags.
#This is 'Roham Terminator' - A Lambda function which terminates EC2 Instances based on a tagging syntax.
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

def lambda_handler(event, context):

    # The lines below receive and interpret the json parameters passed to the Lambda function from another account.
    # In this function only one of the parameters is important: 'rolearn' which is
    # the role in the other account to be assumed by Lambda
    sns_message_json = event["Records"][0]["Sns"]["Message"]
    print(sns_message_json)
    sns_message = json.loads(sns_message_json)
    role_to_assume = sns_message["rolearn"]

    # For a future feature implementation
    #account_type = sns_message["account_type"]

    # This is where the Lambda function assumes the role (which is passed to it) to be able to run commands in the other AWS account
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_to_assume,
        RoleSessionName="Roham_Terminator"
    )

    credentials = assumed_role_object['Credentials']
        
    client = boto3.client(
    'ec2',
    aws_access_key_id = credentials['AccessKeyId'],
    aws_secret_access_key = credentials['SecretAccessKey'],
    aws_session_token = credentials['SessionToken'],
    )
        
    ec2_regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
        
    #The part below is the main part of the code which we look through every region for instances
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
            instance_state = instance.state["Name"]
            #If the instance state is not any of the following, the code terminates the instance as long as it includes the toterminate tag with a value of YES
            if ((instance_state != "pending") and (instance_state != "shutting-down") and (instance_state != "stopping") and (instance_state != "terminated")):
                if instance.tags is not None:
                    toterminate_tag_value = None
                    for tag in instance.tags:
                        if tag["Key"].lower() == "toterminate":
                            toterminate_tag_value = tag["Value"].lower()
                            break
                    if toterminate_tag_value is not None:
                        if(toterminate_tag_value == "yes"):
                            instance.modify_attribute(DisableApiTermination={'Value': False})
                            ec2c.terminate_instances(InstanceIds=instance_id)
                            print("Instance was terminated by Roham...")
                        elif (toterminate_tag_value == "no"):
                            print("Instance was tagged not to terminate...")
                        else:
                            print("Instance has an incorrect toterminate tag value...")
                    else:
                        print("Instance does not have a toterminate tag...")
                else:
                    print("Instance does not have any tags...")
            else:
                print("Instance is not in the correct state to be terminated...")
