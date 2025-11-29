## invoke the email api
## (Message, email) --> email sent confirmation
import smtplib
import ssl
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def send_email(receiver_email, subject, body, verbosity = True):
    """
    Sends an email using Gmail SMTP server.
    I have my own credentials here, but you can change it

    Args:
        receiver_email: The email of the receiver
        subject : The subject of the email
        body : The main email, the email body
    """
    # print("-----------------Hit the email --------------------")
    # return
    if os.environ.get("EMAIL_SENDER") is None:
        value = input("Enter the sender's email ").strip()
        os.environ["EMAIL_SENDER"] = value
    if os.environ.get("EMAIL_PASSWORD") is None:
        value = input("Input the password for your email ").strip()
        os.environ["EMAIL_PASSWORD"] = value
    sender_email = os.environ["EMAIL_SENDER"]
    sender_password = os.environ["EMAIL_PASSWORD"]
    smtp_server = "smtp.gmail.com"
    port = 465

    context = ssl.create_default_context()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(body)
    if verbosity:
        print("The email has been generated, yet to send")

    try:
        ## Making connection to smtp server
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            if verbosity:
                print("Email sent to {0}".format(receiver_email))
            return True
    except Exception as e:
        print("Email API failed")
        if verbosity:
            print("Error: Unable to send email. {0}".format(e))
        return False

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