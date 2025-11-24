# email_send.py

import os, mimetypes
import smtplib
import ssl
import re

from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

# Helpful MIME type registrations (occasionally missing on some systems)
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/tab-separated-values", ".tsv")
mimetypes.add_type("application/x-ndjson", ".jsonl")
mimetypes.add_type("application/x-ndjson", ".ndjson")
mimetypes.add_type("application/x-netcdf", ".nc")
mimetypes.add_type("application/x-hdf5", ".h5")
mimetypes.add_type("application/x-hdf5", ".hdf5")
mimetypes.add_type("application/vnd.apache.parquet", ".parquet")
mimetypes.add_type("application/vnd.apache.arrow.file", ".arrow")
mimetypes.add_type("application/vnd.apache.arrow.file", ".feather")
mimetypes.add_type("application/geo+json", ".geojson")


def attach_file(msg, path):
    """
    Detect MIME type and attach `path` to the multipart message `msg`.

    - Uses `mimetypes.guess_type` to resolve content type.
    - Falls back to `application/octet-stream` when detection fails or file is encoded.
    - Uses RFC 2231 for filename parameter to safely carry non-ASCII filenames.

    :param msg: an email.mime.multipart.MIMEMultipart message to attach to
    :param path: filesystem path of the file to attach
    :return: True if attached, False if `path` does not exist or is not a file
    """
    if not os.path.isfile(path):
        return False

    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"

    maintype, subtype = ctype.split("/", 1)

    # Choose open mode and MIME container by main type
    if maintype == "text":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            part = MIMEText(f.read(), _subtype=subtype, _charset="utf-8")
    elif maintype == "image":
        with open(path, "rb") as f:
            part = MIMEImage(f.read(), _subtype=subtype)
    elif maintype == "audio":
        with open(path, "rb") as f:
            part = MIMEAudio(f.read(), _subtype=subtype)
    elif maintype == "application":
        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype=subtype)
    else:
        with open(path, "rb") as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())
            encoders.encode_base64(part)

    # RFC 2231 filename parameter for non-ASCII safety
    filename = os.path.basename(path)
    part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", filename))
    msg.attach(part)
    return True


_HTML_DOCTYPE = re.compile(r'<!DOCTYPE\s+html', re.I)
_HTML_TAG_HINTS = re.compile(r'<(html|body|table|div|span|p|br|h[1-6])\b', re.I)



def looks_like_html(s: str) -> bool:
    if not isinstance(s, str) or not s:
        return False
    # Escaped HTML means it's not actual HTML markup
    if "&lt;" in s and "&gt;" in s:
        return False
    if _HTML_DOCTYPE.search(s):
        return True
    # Heuristic: presence of common tags plus either a closing tag or <br>
    if _HTML_TAG_HINTS.search(s) and (("</" in s) or ("<br" in s.lower())):
        return True
    return False

def send_email(subject, text, files=None, recipients=None, is_html: bool | None = None):
    """
    Construct and send an email.

    Email is sent either via a direct SMTP host (unauthenticated) or via a
    STARTTLS-authenticated relay, depending on environment variables.

    Environment variables consulted (via `ce`):
      - EMAIL_SENDER (required): From address
      - EMAIL_RECIPIENTS (fallback when `recipients` arg is None): comma- or whitespace-separated
      - SMTP_ADDRESS (for direct path)
      - SMTP_PORT (default 25)
      - EMAIL_DEBUG_LEVEL (int for smtplib debug)
      - RELAY_ADDRESS, RELAY_PORT, RELAY_USER, RELAY_PASSWORD (for STARTTLS relay path)

    Attachment handling:
      - Accepts `files` as a list or a single string path.
      - Uses `attach_file` to detect MIME types, choose the correct MIME part, and
        attach with robust filename encoding.

    :param subject: subject line of the message
    :param text: plain text body
    :param files: list of file paths or a single path to attach
    :param recipients: string or list of recipient addresses; when None, uses EMAIL_RECIPIENTS
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

    # Validate sender configuration early
    if from_address is None:
        logger.critical("Unable to send email as no EMAIL_SENDER set")
        return None

    # Resolve recipients:
    # - Prefer explicit `recipients` arg
    # - Else fall back to EMAIL_RECIPIENTS
    try:
        if recipients is None:
            to_address = ce("EMAIL_RECIPIENTS")
        else:
            to_address = recipients

        # Normalize into a comma-separated string for the header
        if isinstance(to_address, list):
            to_address = ", ".join(to_address)
        elif isinstance(to_address, str) and "," in to_address:
            to_address = ", ".join(to_address.split(","))
        logger.info(f"{to_address}")
    except AttributeError:
        logger.critical("No EMAIL_RECIPIENTS set.")
        return None

    # Build the multipart message (simple plain-text body)
    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = subject

    decide_html = is_html if is_html is not None else looks_like_html(text)

    if decide_html:
        msg.attach(MIMEText(text, "html"))
    else:
        msg.attach(MIMEText(text, "plain"))

    # ---------- Attachments ----------
    # Accept list or single path; call attach_file for each.
    if isinstance(files, list) and len(files) > 0:
        for f in files:
            if attach_file(msg, f):
                logger.info(f"Attached file: {f}")
            else:
                logger.error(f"Failed to attach file {f}. {f} is not a file.")
    elif isinstance(files, str) and len(files) > 0:
        if attach_file(msg, files):
            logger.info(f"Attached file: {files}")
        else:
            logger.error(f"Failed to attach file {files}. {files} is not a file.")
    else:
        logger.info(f'No files attached: "{files}" ')

    logger.info(f"Sending email to {to_address} from {from_address}")

    # ---------- Delivery Path Selection ----------
    # Path A: Direct SMTP (no relay variables configured)
    if all(var is None for var in [relay_address, relay_port, relay_password]):
        with smtplib.SMTP(smtp_address, smtp_port) as server:
            server.set_debuglevel(ce("EMAIL_DEBUG_LEVEL", 0))
            server.send_message(msg)
            server.quit()
        logger.info(f"Email successfully sent to {to_address}.")

    # Path B: Authenticated relay via STARTTLS (all relay vars present)
    elif all(var is not None for var in [relay_address, relay_port, relay_password, relay_user]):
        context = ssl.create_default_context()
        with smtplib.SMTP(relay_address, relay_port) as conn:
            conn.ehlo()
            conn.starttls(context=context)
            conn.login(relay_user, relay_password)
            conn.send_message(msg)
            conn.quit()
        logger.info(f"Email successfully sent to {to_address}.")

    # Misconfiguration: partial relay configuration present
    else:
        # Provide clear guidance on what must be set together.
        logger.error(
            "Misconfigured environment variables detected. "
            + "Please specify either all environment variables "
            + "for relay addresses or none of them. Relay "
            + "environment variables: 'RELAY_ADDRESS', "
            + "'RELAY_PORT', "
            + "'RELAY_PASSWORD', "
            + "'RELAY_USER'"
        )

    return None
