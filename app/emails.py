import os
import datetime
import logging
import boto3
from botocore.exceptions import ClientError


ENV = os.environ.get("ENVIRONMENT", "dev")
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "no-reply@secretsnakes.com")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

# Adding logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_assignment_email(to_email, assigned_username, shipping_info, subject="Your Secret Snakes Assignment"):
    """Send an email with assignment details to the specified recipient."""

    # Append [DEV] to the subject if in development environment
    if ENV == "dev":
        subject = f"[DEV] {subject}"

    # Construct the HTML body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
            .header {{ background-color: #2a7e19; color: #ffffff; padding: 10px 20px; border-radius: 8px 8px 0 0; text-align: center; }}
            .content {{ padding: 20px; }}
            .shipping-box {{ background-color: #ffffff; border: 1px dashed #ccc; padding: 15px; margin-top: 20px; border-radius: 5px; }}
            .shipping-box p {{ margin: 5px 0; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #777; }}
            .button {{ display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: #3cb371; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🐍 Your Secret Snakes Assignment! 🎁</h2>
            </div>
            <div class="content">
                <p>The moment you've been waiting for is here! You've been assigned your recipient for the annual Secret Snakes gift exchange.</p>
                <p>This year, you are the Secret Snake for:</p>
                <h3>{assigned_username}</h3>
                
                <p>Here is their shipping information:</p>
                <div class="shipping-box">
                    <p><strong>{shipping_info.get('first_name', '')} {shipping_info.get('last_name', '')}</strong></p>
                    <p>{shipping_info.get('street_address', '')}</p>
                    <p>{shipping_info.get('unit', '')}</p>
                    <p>{shipping_info.get('city', '')}, {shipping_info.get('state', '')} {shipping_info.get('zipcode', '')}</p>
                </div>
                
                <p>When needed, you can check the website in case they've updated their shipping address.</p>
                
                <a href="https://secretsnakes.com/assignment" class="button">View My Assignment Online</a>
            </div>
            <div class="footer">
                <p>Remember to Snakesmas shitty!</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:

        ses = boto3.client('ses', region_name=AWS_REGION)

        response = ses.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject
                },
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': html_body
                    }
                }
            }
        )
        logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        return response['MessageId']

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.warning(f"Failed to send email. Error Code: {error_code}, Message: {error_message}")
        if error_code == 'MessageRejected':
            logger.warning("Common reasons for rejection: Recipient not verified (if in SES Sandbox), sender not verified, or content issues.")
        return None

    except Exception as e:
        logger.warning(f"An unexpected error occurred while sending email: {e}")
        return None


def send_tip_email(to_email, tip_content, subject="You received a new Snakesmas tip!"):
    """Send an email with a tip to the specified recipient."""

    # Append [DEV] to the subject if in development environment
    if ENV == "dev":
        subject = f"[DEV] {subject}"

    try:

        ses = boto3.client('ses', region_name=AWS_REGION)
        response = ses.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject
                },
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': '<p><b>Hello!</b></p><p><b>You received a new tip from an anonymous user:</b></p><p>' + tip_content + '</p>'
                    }
                }
            }
        )
        logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        return response['MessageId']

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.warning(f"Failed to send email. Error Code: {error_code}, Message: {error_message}")
        if error_code == 'MessageRejected':
            logger.warning("Common reasons for rejection: Recipient not verified (if in SES Sandbox), sender not verified, or content issues.")
        return None


    except Exception as e:
        logger.warning(f"An unexpected error occurred while sending email: {e}")
        return None
