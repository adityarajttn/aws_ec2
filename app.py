from flask import Flask, jsonify
import json
import logging
import boto3
from botocore.exceptions import ClientError
from json2html import *
import datetime
from dateutil.tz import tzutc

AWS_REGION='ap-south-1'
BUCKET='geet-combat'
OBJECT='instance_metric.json'

app = Flask(__name__)


def is_in_autoscale_group(region, instance_id):
    asg = boto3.client('autoscaling', region_name=region)
    instances = \
        asg.describe_auto_scaling_instances(InstanceIds=[instance_id])
    instance_status = instances['AutoScalingInstances']
    if instance_status:
        print(f"Instance {instance_id} is in autoscale group {instance_status[0]['AutoScalingGroupName']}")
        return True
    return False


def average_cpu_instances(region, tag_key, tag_values, idle_period_secs, minimum):
    ec2 = boto3.client('ec2', region_name=region)
    c = boto3.client('cloudwatch', region_name=region)
    values = tag_values.split(",")
    filters = []
    if tag_key:
        f0 = {}
        f0['Name'] = "tag:{}".format(tag_key)
        f0['Values'] = values
        filters.append(f0)

    f1 = {}
    f1['Name'] = 'instance-state-name'
    f1['Values'] = ['running']
    filters.append(f1)
    rs = ec2.describe_instances(Filters=filters)
    now = datetime.datetime.now(tzutc())
    lookback = datetime.timedelta(seconds=idle_period_secs)
    time_start = now - lookback
    instance_metric = {}
    for r in rs['Reservations']:
        for i in r['Instances']:
            launch_time = i['LaunchTime']
            if is_in_autoscale_group(region, i['InstanceId']):
                continue
            age = now - launch_time
            if age < datetime.timedelta(seconds=idle_period_secs):
                print(f"Age of instance {i['InstanceId']} = {str(age)}, less than {str(lookback)}")
                continue
            dim = [{'Name': 'InstanceId', 'Value': i['InstanceId']}]
            period = idle_period_secs - (idle_period_secs % 60)
            if period < 60:
                period = 60
            metric = c.get_metric_statistics(Period=period,
                                             StartTime=time_start,
                                             EndTime=now,
                                             MetricName='CPUUtilization',
                                             Namespace='AWS/EC2',
                                             Statistics=['Average'],
                                             Dimensions=dim)
            # print metric
            if metric['Datapoints']:
                average = metric['Datapoints'][0]['Average']
                print(f"Average for {i['InstanceId']} is {average}. Minimum is {minimum}")
                instance_metric[i['InstanceId']] = {"avergae": average, "minimum": minimum}
                
    return instance_metric

def upload_to_s3(region, instance_metric, file):
    s3_client = boto3.client('s3', region_name=region)
    json_object = json.dumps(instance_metric, indent = 4)

    with open(file, "w") as outfile:
        outfile.write(json_object)

    try:
        response = s3_client.upload_file(file, BUCKET, file)
    except ClientError as e:
        logging.error(e)
        return False

    html = json.loads(json_object)
    html = json2html.convert(json = html)
    print(html)
    with open("instance.html", "w") as html_file:
        html_file.write(html)
        try:
            response = s3_client.upload_file('index.html', BUCKET, 'instance.html')
        except ClientError as e:
            logging.error(e)
            return False

    return True


@app.route('/instances')
def get_instances():
    instance_metric = average_cpu_instances(region=AWS_REGION,
                        tag_key='Name',
                        tag_values='aws_training',
                        idle_period_secs=86400,
                        minimum=0.05)

    response = upload_to_s3(region=AWS_REGION, instance_metric=instance_metric, file='instance_metric.json')
    if response:
        return jsonify({"message": "successfuly uploaded"})
    return jsonify({"message": "upload was not successful"})

app.run(port=5000)

