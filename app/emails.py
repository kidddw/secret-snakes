import os
import datetime
import logging
import boto3
from botocore.exceptions import ClientError


ENV = os.environ.get("ENVIRONMENT", "dev")
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "no-reply@secretsnakes.com")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

PRIMARY_COLOR_THREE = "#3d523d"
ACCENT_COLOR_TWO = "#4682B4"

# Adding logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_email(to_email, subject, html_body, logger_info="Email sent successfully"):
    """Generic function to send an email using AWS SES.
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
        logger.info(logger_info + f"! Message ID: {response['MessageId']}")
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


def send_username_recovery_email(to_email: str, username: str):
    """
    Sends an email to the user with their forgotten username.
    """
    subject = "Secret Snakes Username Recovery"

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
            .header {{ background-color: {PRIMARY_COLOR_THREE}; color: #ffffff; padding: 10px 20px; border-radius: 8px 8px 0 0; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #777; }}
            .username-box {{ background-color: #ffffff; border: 1px solid #eee; padding: 15px; margin-top: 20px; text-align: center; font-size: 1.2em; font-weight: bold; border-radius: 5px; }}
            .button {{ display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: {ACCENT_COLOR_TWO}; text-color: #ffffff; text-decoration: none; border-radius: 5px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🐍 Secret Snakes Username Recovery 🐍</h2>
            </div>
            <div class="content">
                <p>You recently requested your username for the Secret Snakes application. Your username is:</p>
                <div class="username-box">
                    {username}
                </div>
                <p>You can now use this username to log in.</p>
                
                <a href="{BASE_URL}/home" 
                style="
                        display: inline-block;
                        padding: 10px 20px;
                        margin-top: 20px;
                        background-color: {ACCENT_COLOR_TWO};
                        color: #ffffff;
                        text-decoration: none;
                        border-radius: 5px;
                        -webkit-text-size-adjust: none;   /* Email client compatibility for text sizing */
                        mso-hide: all;                    /* Email client compatibility for text sizing */
                        ">
                    Log In Here
                </a>

                <p>If you did not request this, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>Thanks to you, Snakesmas just got a little more shitty</p>
            </div>
        </div>
    </body>
    </html>
    """

    logger_info = f"Username recovery email sent successfully to {to_email}!"

    send_email(to_email, subject, html_body, logger_info=logger_info) 


def send_password_reset_email(to_email: str, reset_token: str):
    """
    Sends an email to the user with a link to reset their password.
    """
    subject = "Secret Snakes Password Reset"
    reset_link = f"{BASE_URL}/reset-password?token={reset_token}"

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
            .header {{ background-color: {PRIMARY_COLOR_THREE}; color: #ffffff; padding: 10px 20px; border-radius: 8px 8px 0 0; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #777; }}
            .button {{ display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: {ACCENT_COLOR_TWO}; color: white; text-decoration: none; text-color: white; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🐍 Secret Snakes Password Reset 🐍</h2>
            </div>
            <div class="content">
                <p>You recently requested to reset your password.  Please click the link below to reset your password:</p>
                <a href="{reset_link}" 
                    style="
                        display: inline-block;
                        padding: 10px 20px;
                        margin-top: 20px;
                        background-color: {ACCENT_COLOR_TWO};
                        color: #ffffff;
                        text-decoration: none;
                        border-radius: 5px;
                        -webkit-text-size-adjust: none;   /* Email client compatibility for text sizing */
                        mso-hide: all;                    /* Email client compatibility for text sizing */
                        ">
                    Reset Your Password
                </a>
                <p>This link will expire in one hour.  If you did not request a password reset, you can ignore this email.</p>
            </div>
            <div class="footer">
                <p>Thanks to you, Snakesmas just got a little more shitty</p>
            </div>
        </div>
    </body>
    </html>
    """

    logger_info = f"Password reset email sent successfully to {to_email}!"

    send_email(to_email, subject, html_body, logger_info=logger_info) 


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
            .header {{ background-color: {PRIMARY_COLOR_THREE}; color: #ffffff; padding: 10px 20px; border-radius: 8px 8px 0 0; text-align: center; }}
            .content {{ padding: 20px; }}
            .shipping-box {{ background-color: #ffffff; border: 1px dashed #ccc; padding: 15px; margin-top: 20px; border-radius: 5px; }}
            .shipping-box p {{ margin: 5px 0; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #777; }}
            .button {{ display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: {ACCENT_COLOR_TWO}; color: white; text-decoration: none; text-color: white; border-radius: 5px; }}
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
                <p>Remember to keep Snakesmas shitty!</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(to_email, subject, html_body) 


def send_tip_email(to_email, tip_content, subject="You received a new Snakesmas tip!"):
    """Send an email with a tip to the specified recipient."""

    # Append [DEV] to the subject if in development environment
    if ENV == "dev":
        subject = f"[DEV] {subject}"

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
            .header {{ background-color: {PRIMARY_COLOR_THREE}; color: #ffffff; padding: 10px 20px; border-radius: 8px 8px 0 0; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #777; }}
            .tip-box {{ background-color: #ffffff; border: 1px solid #eee; padding: 15px; margin-top: 20px; text-align: center; font-size: 1.2em; font-weight: bold; border-radius: 5px; }}
            .button {{ display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: {ACCENT_COLOR_TWO}; color: white; text-decoration: none; text-color: white; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🐍 Secret Snakes Tip for Your Assignment 🐍</h2>
            </div>
            <div class="content">
                <p>You received a new tip from an anonymous user:</p>
                <div class="tip-box">
                    {tip_content}
                </div>
            </div>
            <div class="footer">
                <p>Remember to keep Snakesmas shitty!</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(to_email, subject, html_body) 


def send_assignment_note_email(to_email, note_content, subject="You received a note from your secret snake!"):
    """Send an email with a note to the assigned user."""

    # Append [DEV] to the subject if in development environment
    if ENV == "dev":
        subject = f"[DEV] {subject}"
        logger.info(f"Would send note email to: {to_email}")
        to_email = "daniel.wayne.kidd@gmail.com"  # Override email for testing in dev

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
            .header {{ background-color: {PRIMARY_COLOR_THREE}; color: #ffffff; padding: 10px 20px; border-radius: 8px 8px 0 0; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #777; }}
            .tip-box {{ background-color: #ffffff; border: 1px solid #eee; padding: 15px; margin-top: 20px; text-align: center; font-size: 1.2em; font-weight: bold; border-radius: 5px; }}
            .button {{ display: inline-block; padding: 10px 20px; margin-top: 20px; background-color: {ACCENT_COLOR_TWO}; color: white; text-decoration: none; text-color: white; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🐍 Secret Snakes Note from Your Secret Snake 🐍</h2>
            </div>
            <div class="content">
                <p>You received a new note from your secret snake:</p>
                <div class="tip-box">
                    {note_content}
                </div>
            </div>
            <div class="footer">
                <p>Remember to keep Snakesmas shitty!</p>
            </div>
        </div>
    </body>
    </html>
    """

    send_email(to_email, subject, html_body) 