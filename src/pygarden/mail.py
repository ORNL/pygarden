"""Provide functions to send emails."""

import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


def send_email(subject, text, files=None, recipients=None):
    """
    Construct and send an email.

    Send email to the EMAIL_RECIPIENTS env variable with the given subject
    and message body from the EMAIL_SENDER address. Email debug level is
    controlled with the EMAIL_DEBUG_LEVEL environmental variable and
    defaults to `0`, resulting in no debugging information.

    :param subject: the subject of email to send
    :param text: the content of the message to send
    :param files: a list of files to attach to the email
    :param recipients: a list of email addresses to send the email to
    :return: None
    """
    logger = create_logger()

    from_address = ce("EMAIL_SENDER")
    smtp_address = ce("SMTP_ADDRESS")
    relay_address = ce("RELAY_ADDRESS")
    relay_port = ce("RELAY_PORT")
    relay_password = ce("RELAY_PASSWORD")
    relay_user = ce("RELAY_USER")
    smtp_port = ce("SMTP_PORT", 25)
    if from_address is None:
        logger.critical("Unable to send email as no EMAIL_SENDER set")
        return None

    try:
        if recipients is None:
            to_address = ce("EMAIL_RECIPIENTS")
        else:
            to_address = recipients
        if "," in to_address:
            to_address = ", ".join(to_address.split(","))
        logger.info(f"{to_address}")
    except AttributeError:
        logger.critical("No EMAIL_RECIPIENTS set.")
        return None

    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain"))

    # if attachment files have been passed..
    if isinstance(files, list) and len(files) > 0:
        for f in files:
            if os.path.isfile(f):
                with open(f, "rb") as att_file:
                    part = MIMEApplication(att_file.read())
                part["Content-Disposition"] = "attachment; filename=" f'"{os.path.basename(f)}"'
                msg.attach(part)
            else:
                logger.error(f"Failed to attach file {f}. {f} is not a file.")
    elif isinstance(files, str) and len(files) > 0:
        if os.path.isfile(files):
            with open(files, "rb") as att_file:
                part = MIMEApplication(att_file.read())
            part["Content-Disposition"] = "attachment; filename=" f'"{os.path.basename(files)}"'
            msg.attach(part)
        else:
            logger.error(f"Failed to attach file {files}. {files} is not a " "file.")
    else:
        logger.info(f'No files attached: "{files}" ')
    logger.info(f"Sending email to {to_address} from {from_address}")
    # try:
    if all(var is None for var in [relay_address, relay_port, relay_password]):
        with smtplib.SMTP(smtp_address, smtp_port) as server:
            server.set_debuglevel(ce("EMAIL_DEBUG_LEVEL", 0))
            server.send_message(msg)
            server.quit()
        logger.info(f"Email successfully sent to {to_address}.")
    elif all(var is not None for var in [relay_address, relay_port, relay_password, relay_user]):
        # allow ssl connection
        context = ssl.create_default_context()
        with smtplib.SMTP(relay_address, relay_port) as conn:
            conn.ehlo()
            conn.starttls(context=context)
            conn.login(relay_user, relay_password)
            conn.send_message(msg)
            conn.quit()
        logger.info(f"Email successfully sent to {to_address}.")
    else:
        logger.error(
            "Misconfigured environment variables detected. "
            + "Please specify either all environment variables "
            + "for relay addresses or none of them. Relay "
            + "environment variables: 'RELAY_ADDRESS', "
            + "'RELAY_PORT', 'RELAY_PASSWORD'"
        )
    # except smtplib.SMTPException as error:
    #     logger.error(f'Error sending email: {error}')

    return None
