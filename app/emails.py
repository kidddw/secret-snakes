import boto3

def send_tip_email(to_email, tip_content):
    ses = boto3.client('ses', region_name='us-east-1')
    ses.send_email(
        Source='your-verified-email@example.com',
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': 'You received a new tip!'},
            'Body': {'Text': {'Data': tip_content}}
        }
    )