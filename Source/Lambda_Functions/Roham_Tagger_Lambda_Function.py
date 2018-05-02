#Roham is a an open-source tool which helps you to save cost on AWS by terminating/stopping/starting EC2 Instances based on schedule tags.
#This is 'Roham Tagger' - A Lambda function which enforces/creates tags on EC2 Instances automatically in case the owner does not do it. 
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

def termination_tagger(conn, instance_id):
    conn.create_tags(
    Resources=instance_id,
        Tags=[
            {'Key': 'toterminate', 'Value': 'yes'},
        ]
    )
    print("Instance was successfully tagged to terminate by Roham...")
    print("Instance does not need to have a weekendstop tag...")

def weekendstop_tagger(conn, instance_id):
    conn.create_tags(
        Resources=instance_id,
        Tags=[
            {'Key': 'weekendstop', 'Value': 'yes'},
        ]
    )
    print("Instance was successfully tagged by Roham to stop over the weekend...")

def stop_tagger(conn, instance_id):
    conn.create_tags(
        Resources=instance_id,
        Tags=[
            {'Key': 'tostop', 'Value': '0 18 * * mon-fri'},
        ]
    )
    print("Instance was successfully tagged to stop by Roham...")

def lambda_handler(event, context):
    # The lines below receive and interpret the json parameters passed to the Lambda function from another account.
    # In this function 'rolearn' which is the role in the other account to be assumed by Lambda
    sns_message_json = event["Records"][0]["Sns"]["Message"]
    print(sns_message_json)
    sns_message = json.loads(sns_message_json)
    role_to_assume = sns_message["rolearn"]

    # For a future feature implementation
    account_type = sns_message["account_type"]

    # This is where the Lambda function assumes the role (which is passed to it) to be able to run commands in the other AWS account
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_to_assume,
        RoleSessionName="Roham_Tagger"
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
        instances = conn.instances.filter()
        for instance in instances:
            instance_id = instance.id.split()
            print(instance.id, instance.instance_type, region)
            #In this FOR loop the account_type is checked and if it is a playground account, Instances will be checked for toterminate and weekendstop tags
            if(account_type == "playground"):
                if instance.tags is not None:
                    toterminate_tag_value = None
                    for tag in instance.tags:
                        if tag["Key"].lower() == "toterminate":
                            toterminate_tag_value = tag["Value"].lower()
                            break
                    if toterminate_tag_value is not None:
                        if toterminate_tag_value == "yes":
                            print("Instance has the correct termination tag...")
                            print("Instance does not need to have a weekendstop tag...")
                        #The code below checks if the Instance has a value of 'no' for the 'toterminate' tag key; and if it is the case, the Instance will be checked for the 'weekendstop' tag.
                        elif toterminate_tag_value == "no":
                            print("Instance has the correct termination tag...")
                            weekendstop_tag_value = None
                            for tag in instance.tags:
                                if tag["Key"].lower() == "weekendstop":
                                    weekendstop_tag_value = tag["Value"].lower()
                                    break
                            if weekendstop_tag_value is not None:
                                if (weekendstop_tag_value != "yes") and (weekendstop_tag_value != "no"):
                                    weekendstop_tagger(conn, instance_id)
                                else:
                                    print("Instance has the correct weekendstop tag...")
                            else:
                                weekendstop_tagger(conn, instance_id)
                        else:
                            termination_tagger(conn, instance_id)
                    else:
                        termination_tagger(conn, instance_id)
                else:
                    termination_tagger(conn, instance_id)
    
            #If the account type is 'dev', then the 'tostop' tag and its compliance will be checked for. 
            elif(account_type == "dev"):
                if instance.tags is not None:
                    tostop_tag_value = None
                    for tag in instance.tags:
                        if tag["Key"].lower() == "tostop":
                            tostop_tag_value = tag["Value"].lower()
                            break
                    if tostop_tag_value is not None:
                        if (croniter.is_valid(tostop_tag_value) and ('/' not in tostop_tag_value)) or (tostop_tag_value == "no"):
                            print("Instance has the correct tostop tag...")
                        else:
                            stop_tagger(conn, instance_id)
                    else:
                        stop_tagger(conn, instance_id)
                    
                    #In the lines below the 'weekendstop' tag and its compliance is checked for. 
                    weekendstop_tag_value = None
                    for tag in instance.tags:
                        if tag["Key"].lower() == "weekendstop":
                            weekendstop_tag_value = tag["Value"].lower()
                            break
                    if weekendstop_tag_value is not None:
                        if (weekendstop_tag_value != "yes") and (weekendstop_tag_value != "no"):
                            weekendstop_tagger(conn, instance_id)
                        else:
                            print("Instance has the correct weekendstop tag...")
                    else:
                        weekendstop_tagger(conn, instance_id)
                else:
                    stop_tagger(conn, instance_id)
                    weekendstop_tagger(conn, instance_id)
    