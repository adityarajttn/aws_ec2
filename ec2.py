from datetime import datetime, timedelta
import json
from json2html import *
from typing import Dict, List
import boto3

ec2_client = boto3.client('ec2')
cloudwatch_client = boto3.client('cloudwatch')

def list_ec2_instances() -> List:
    instance_ids = []
    responses = ec2_client.describe_instances()
    for response in responses['Reservations']:
        for instance in response['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    return instance_ids


def average_cpu_usages(instance_ids: List) -> Dict:
    seconds_in_one_day = 86400 
    average_cpu_usages_res = {}
    for instance_id in instance_ids:
        responses = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/EC2',
            Dimensions=[
                {
                        'Name': 'InstanceId',
                        'Value': instance_id
                },
            ],
            MetricName='CPUUtilization',
            StartTime=datetime.now() - timedelta(days=7),
            EndTime=datetime.now(),
            Period=seconds_in_one_day,
            Statistics=[
                'Average'
            ],
            Unit='Percent'
        )

        cpu_usages = []
        for response in responses['Datapoints']:
            cpu_usages.append(response['Average'])
        avg_cpu = sum(cpu_usages) / 7
        average_cpu_usages_res[instance_id] = avg_cpu
        
    return average_cpu_usages_res

instance_ids = list_ec2_instances()
average_cpu = average_cpu_usages(instance_ids=instance_ids)
print(average_cpu)
average_cpu_json = json.dumps(average_cpu)
print(average_cpu_json)
# average_cpu_json = json.load(average_cpu_json)

html = json2html.convert(json = average_cpu_json)
with open("sample.html", "w") as html_file:
    html_file.write(htmls)



