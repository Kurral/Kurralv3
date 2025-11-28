"""
Email sending functionality using Gmail SMTP.

Note: For Gmail, you need to use an App Password, not your regular password.
To generate an App Password:
1. Enable 2-Step Verification on your Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Generate an app password for "Mail"
4. Use that password in EMAIL_PASSWORD in your .env file
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_email(receiver_email: str, subject: str, body: str, verbosity: bool = True) -> None:
    """
    Sends an email using Gmail SMTP server.
    
    Args:
        receiver_email: The email address of the receiver
        subject: The subject of the email
        body: The main email body content
        verbosity: Whether to print status messages
    
    Raises:
        ValueError: If EMAIL_SENDER or EMAIL_PASSWORD are not set in environment
        smtplib.SMTPAuthenticationError: If authentication fails (401 error)
    """
    # Get credentials from environment variables
    sender_email = os.getenv("EMAIL_SENDER", "").strip()
    sender_password = os.getenv("EMAIL_PASSWORD", "").strip()
    
    if not sender_email:
        raise ValueError(
            "EMAIL_SENDER not found in environment variables. "
            "Please set EMAIL_SENDER in your .env file."
        )
    
    if not sender_password:
        raise ValueError(
            "EMAIL_PASSWORD not found in environment variables. "
            "Please set EMAIL_PASSWORD in your .env file. "
            "Note: Use an App Password for Gmail, not your regular password."
        )
    
    smtp_server = "smtp.gmail.com"
    port = 465
    
    context = ssl.create_default_context()
    
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(body)
    
    if verbosity:
        print("Preparing to send email...")
    
    try:
        # Make connection to SMTP server
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
            if verbosity:
                print(f"✓ Email sent successfully to {receiver_email}")
    
    except smtplib.SMTPAuthenticationError as e:
        error_msg = (
            f"SMTP Authentication Error (401): Failed to authenticate with Gmail.\n"
            f"Common causes:\n"
            f"  1. Incorrect email or password\n"
            f"  2. Using regular password instead of App Password\n"
            f"  3. 2-Step Verification not enabled\n\n"
            f"To fix:\n"
            f"  1. Enable 2-Step Verification on your Google Account\n"
            f"  2. Generate an App Password: https://myaccount.google.com/apppasswords\n"
            f"  3. Use the App Password (not your regular password) in EMAIL_PASSWORD\n\n"
            f"Error details: {str(e)}"
        )
        if verbosity:
            print(f"\n[ERROR] {error_msg}")
        raise ValueError(error_msg) from e
    
    except smtplib.SMTPException as e:
        error_msg = f"SMTP Error: Unable to send email. {str(e)}"
        if verbosity:
            print(f"\n[ERROR] {error_msg}")
        raise
    
    except Exception as e:
        error_msg = f"Unexpected error while sending email: {str(e)}"
        if verbosity:
            print(f"\n[ERROR] {error_msg}")
        raise

# def main():
#     ## This main function is just for testing this, no need to import this in the app.py
#     receiver_email = "jayjani482001@gmail.com"
#     email_subject = "Initial Python test"
#     email_body = """
#     Hello,
    
#     This is a test email sent from my Python script using the smtplib library.
    
#     Regards,
#     Your Python Script
#     """
#     send_email(receiver_email,email_subject, email_body)


# main()