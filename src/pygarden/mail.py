"""
Provide functions to send emails.

This module provides functionality to send emails with support for attachments,
multiple recipients, and different SMTP configurations. It uses environment
variables for configuration and supports both direct SMTP and relay connections.

The module provides:
- Email sending with customizable subject and content
- File attachment support (single file or list of files)
- Multiple recipient support
- SMTP and relay server configurations
- Environment variable based configuration

Examples
--------
Send a simple email::

    >>> send_email("Test Subject", "This is a test message")

Send email with attachments::

    >>> send_email("Report", "Please find attached report", files=["report.pdf"])

Send email to specific recipients::

    >>> send_email("Alert", "System alert", recipients=["admin@example.com"])

Send email with multiple attachments::

    >>> send_email("Data Export", "Please find the exported data", 
    ...           files=["data.csv", "summary.pdf"])

Notes
-----
Environment Variables Required:
    - EMAIL_SENDER: The sender email address
    - EMAIL_RECIPIENTS: Default recipients (comma-separated)
    - SMTP_ADDRESS: SMTP server address
    - SMTP_PORT: SMTP server port (default: 25)

Optional Environment Variables:
    - RELAY_ADDRESS: Relay server address
    - RELAY_PORT: Relay server port
    - RELAY_PASSWORD: Relay server password
    - RELAY_USER: Relay server username
    - EMAIL_DEBUG_LEVEL: Debug level for SMTP (default: 0)
"""
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

    The function supports both direct SMTP connections and relay server
    connections based on environment variable configuration.

    :param subject: The subject of email to send
    :type subject: str
    :param text: The content of the message to send
    :type text: str
    :param files: A list of files to attach to the email, or a single file path
    :type files: list or str or None
    :param recipients: A list of email addresses to send the email to
    :type recipients: list or str or None
    :return: Always returns None
    :rtype: None
    :raises Exception: If email configuration is missing or invalid

    Examples
    --------
    Send a simple email::

        >>> send_email("Test", "Hello world")

    Send email with file attachment::

        >>> send_email("Report", "See attached", files=["report.pdf"])

    Send email to specific recipients::

        >>> send_email("Alert", "System down", recipients=["admin@example.com"])

    Send email with multiple attachments::

        >>> send_email("Export", "Data attached", files=["data.csv", "summary.pdf"])

    Notes
    -----
    Environment Variables Used:
        - EMAIL_SENDER: The sender email address
        - EMAIL_RECIPIENTS: Default recipients (comma-separated)
        - SMTP_ADDRESS: SMTP server address
        - SMTP_PORT: SMTP server port (default: 25)
        - RELAY_ADDRESS: Relay server address (optional)
        - RELAY_PORT: Relay server port (optional)
        - RELAY_PASSWORD: Relay server password (optional)
        - RELAY_USER: Relay server username (optional)
        - EMAIL_DEBUG_LEVEL: Debug level for SMTP (default: 0)

    Connection Types:
        - Direct SMTP: Uses SMTP_ADDRESS and SMTP_PORT
        - Relay: Uses RELAY_* variables for authenticated relay connection
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
