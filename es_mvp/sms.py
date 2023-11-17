"""
Implement SMS sending solution.
"""
import boto3 # AWS Python CLI
import os

### AWS SES / Pinpoint 

# def sending_sms_aws(cellphone, message):
#     """A simple test function"""
#     print(f"Sent SMS to: {cellphone}")
#     print(f"Message: \n {message}")
#     return None

# Based on the following documentation:
# https://github.com/asaguado/django-amazon-sns
# https://aws.amazon.com/pt/sns/
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html
def sending_sms_aws(cellphone, message):
    """Send a SMS message to a recipient"""
    # Create an SNS client
    client = boto3.client(
        "sns",
        aws_access_key_id=os.getenv("SENDER_SMS_AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("SENDER_SMS_AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1"
    )

    # Send your sms message.
    response = client.publish(
        PhoneNumber=cellphone,
        Message=message,
    )
    ## TO-DO: to implement the log of this service execution
    return response['MessageId']