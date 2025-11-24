# test_mail.py

import builtins
import types
import os
import ssl
import mimetypes
import email
import pytest

import pygarden.mail as es


class DummyLogger:
    def __init__(self):
        self.messages = []
    def info(self, m): self.messages.append(("info", m))
    def error(self, m): self.messages.append(("error", m))
    def critical(self, m): self.messages.append(("critical", m))


class DummySMTP:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.debuglevel = None
        self.sent = []
        self.started_tls = False
        self.logged_in = None
        self.ehlo_called = False
        self.quit_called = False

    # context manager
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

    # smtplib API used by email_send
    def set_debuglevel(self, level): self.debuglevel = level
    def send_message(self, msg): self.sent.append(msg)
    def ehlo(self): self.ehlo_called = True
    def starttls(self, context=None): self.started_tls = True
    def login(self, user, password): self.logged_in = (user, password)
    def quit(self): self.quit_called = True


@pytest.fixture
def logger(monkeypatch):
    lg = DummyLogger()
    monkeypatch.setattr(es, "create_logger", lambda: lg)
    return lg


def patch_ce(monkeypatch, mapping, raises_attr_error=False):
    """
    mapping: dict of key -> value to return from ce
    raises_attr_error: if True, raise AttributeError when fetching EMAIL_RECIPIENTS
    """
    def fake_ce(key, default=None):
        if raises_attr_error and key == "EMAIL_RECIPIENTS":
            raise AttributeError("missing")
        return mapping.get(key, default)
    monkeypatch.setattr(es, "ce", fake_ce)


def test_attach_file_nonexistent_returns_false():
    msg = email.mime.multipart.MIMEMultipart()
    assert es.attach_file(msg, "nope/does/not/exist.txt") is False


def test_attach_file_text_path(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    msg = email.mime.multipart.MIMEMultipart()
    ok = es.attach_file(msg, str(p))
    assert ok is True
    assert any(part.get_content_type() == "text/plain" for part in msg.get_payload())


def test_attach_file_application_path(tmp_path):
    # application/*
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4\n%...")
    msg = email.mime.multipart.MIMEMultipart()
    ok = es.attach_file(msg, str(p))
    assert ok is True
    assert any(part.get_content_type() == "application/pdf" for part in msg.get_payload())


def test_attach_file_image_path(tmp_path, monkeypatch):
    # force guess_type to image subtype regardless of extension
    p = tmp_path / "img.bin"
    p.write_bytes(b"\x89PNG\r\n\x00anything")
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: ("image/png", None))
    msg = email.mime.multipart.MIMEMultipart()
    ok = es.attach_file(msg, str(p))
    assert ok is True
    assert any(part.get_content_type() == "image/png" for part in msg.get_payload())


def test_attach_file_audio_path(tmp_path, monkeypatch):
    p = tmp_path / "sound.bin"
    p.write_bytes(b"ID3fake")
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: ("audio/mpeg", None))
    msg = email.mime.multipart.MIMEMultipart()
    ok = es.attach_file(msg, str(p))
    assert ok is True
    assert any(part.get_content_type() == "audio/mpeg" for part in msg.get_payload())


def test_attach_file_else_branch_mimebase(tmp_path, monkeypatch):
    p = tmp_path / "weird.bin"
    p.write_bytes(b"xyz")
    monkeypatch.setattr(mimetypes, "guess_type", lambda _: ("weird/main", None))
    msg = email.mime.multipart.MIMEMultipart()
    ok = es.attach_file(msg, str(p))
    assert ok is True
    # should not be one of the explicit classes; MIMEBase keeps type as weird/main
    assert any(part.get_content_type() == "weird/main" for part in msg.get_payload())


@pytest.mark.parametrize(
    "s,expected",
    [
        (None, False),
        ("", False),
        ("&lt;div&gt;escaped&lt;/div&gt;", False),
        ("<!DOCTYPE html><html></html>", True),
        ("<div>x</div>", True),
        ("<p>line<br>break", True),
        ("no html here", False),
    ],
)
def test_looks_like_html(s, expected):
    assert es.looks_like_html(s) is expected


def test_send_email_no_sender_early_return(monkeypatch, logger):
    patch_ce(monkeypatch, mapping={"EMAIL_SENDER": None})
    # Ensure AttributeError branch not triggered here; function returns before recipients resolution
    assert es.send_email("subj", "body") is None
    assert any(level == "critical" for level, msg in logger.messages)


def test_send_email_attributeerror_on_recipients(monkeypatch, logger):
    # From is set so we reach recipients try/except; then ce raises AttributeError
    patch_ce(
        monkeypatch,
        mapping={"EMAIL_SENDER": "from@example.com"},
        raises_attr_error=True,
    )
    assert es.send_email("s", "b") is None
    assert any(level == "critical" and "No EMAIL_RECIPIENTS" in msg for level, msg in logger.messages)


def test_send_email_direct_smtp_with_list_recipients_and_no_files(monkeypatch, logger):
    smtp = DummySMTP("ignored", 0)
    monkeypatch.setattr(es.smtplib, "SMTP", lambda host, port: DummySMTP(host, port))
    patch_ce(
        monkeypatch,
        mapping={
            "EMAIL_SENDER": "from@x.com",
            "EMAIL_RECIPIENTS": "env1@x.com, env2@x.com",
            "SMTP_ADDRESS": "smtp.local",
            "SMTP_PORT": 2525,
            "EMAIL_DEBUG_LEVEL": 1,
            "RELAY_ADDRESS": None,
            "RELAY_PORT": None,
            "RELAY_PASSWORD": None,
            "RELAY_USER": None,
        },
    )
    # recipients arg overrides env; normalization for list
    recipients = ["a@x.com", "b@x.com"]
    res = es.send_email("subj", "just text", files=None, recipients=recipients, is_html=False)
    assert res is None
    # confirm SMTP was used with expected host/port and debug level
    # We can't access the instance directly, but our Dummy captures via lambda closure, so re-call to retrieve?
    # Instead, re-create one and inspect signature indirectly by monkeypatching to class with recordable instances
    # (Simplify by re-running with a capturing factory)

# Add below the previous code in test_mail.py

class SMTPFactory:
    def __init__(self):
        self.instances = []
    def __call__(self, host, port):
        inst = DummySMTP(host, port)
        self.instances.append(inst)
        return inst


def test_send_email_direct_smtp_path(monkeypatch, logger):
    factory = SMTPFactory()
    monkeypatch.setattr(es.smtplib, "SMTP", factory)
    patch_ce(
        monkeypatch,
        mapping={
            "EMAIL_SENDER": "from@x.com",
            "EMAIL_RECIPIENTS": "user1@x.com, user2@x.com",
            "SMTP_ADDRESS": "smtp.host",
            "SMTP_PORT": 2526,
            "EMAIL_DEBUG_LEVEL": 3,
            "RELAY_ADDRESS": None,
            "RELAY_PORT": None,
            "RELAY_PASSWORD": None,
            "RELAY_USER": None,
        },
    )
    es.send_email("Subject X", "Plain body", files="", recipients="a@x.com,b@x.com", is_html=None)
    inst = factory.instances[-1]
    assert inst.host == "smtp.host"
    assert inst.port == 2526
    assert inst.debuglevel == 3
    assert len(inst.sent) == 1
    msg = inst.sent[0]
    assert msg["From"] == "from@x.com"
    assert msg["To"] == "a@x.com, b@x.com"  # normalized comma/space
    # verify text/plain chosen because looks_like_html("Plain body") is False
    assert msg.get_payload(0).get_content_type() == "text/plain"
    assert inst.quit_called is True


def test_send_email_relay_starttls_path_with_attachments(monkeypatch, tmp_path, logger):
    factory = SMTPFactory()
    monkeypatch.setattr(es.smtplib, "SMTP", factory)
    # Force ssl context creation
    monkeypatch.setattr(ssl, "create_default_context", lambda: object())

    # Prepare attachments: one that succeeds, one that fails
    okfile = tmp_path / "data.tsv"
    okfile.write_text("a\tb\n1\t2\n", encoding="utf-8")
    missing = tmp_path / "nope.bin"

    # Patch attach_file to return True for okfile and False for missing to drive both branches
    calls = []
    def fake_attach(msg, path):
        calls.append(path)
        return os.path.isfile(path)
    monkeypatch.setattr(es, "attach_file", fake_attach)

    patch_ce(
        monkeypatch,
        mapping={
            "EMAIL_SENDER": "sender@x.com",
            "EMAIL_RECIPIENTS": "r1@x.com r2@x.com",  # whitespace-separated also ok (treated as one string; left as-is in header)
            "SMTP_ADDRESS": "ignored-direct",
            "SMTP_PORT": 25,
            "EMAIL_DEBUG_LEVEL": 0,
            "RELAY_ADDRESS": "relay.host",
            "RELAY_PORT": 587,
            "RELAY_PASSWORD": "secret",
            "RELAY_USER": "u",
        },
    )

    es.send_email("S", "<div>html<br></div>", files=[str(okfile), str(missing)], recipients=None, is_html=None)

    inst = factory.instances[-1]
    assert inst.host == "relay.host"
    assert inst.port == 587
    assert inst.ehlo_called is True
    assert inst.started_tls is True
    assert inst.logged_in == ("u", "secret")
    assert len(inst.sent) == 1
    msg = inst.sent[0]
    # html chosen by heuristic
    assert msg.get_payload(0).get_content_type() == "text/html"
    # Two attachments attempted; one success, one failure => still 1 attachment added by fake_attach
    # Our fake added nothing directly; we only care that attach_file was invoked for both paths
    assert calls == [str(okfile), str(missing)]


def test_send_email_misconfiguration_logs_error(monkeypatch, logger):
    factory = SMTPFactory()
    monkeypatch.setattr(es.smtplib, "SMTP", factory)
    patch_ce(
        monkeypatch,
        mapping={
            "EMAIL_SENDER": "s@x.com",
            "EMAIL_RECIPIENTS": "t@x.com",
            "SMTP_ADDRESS": "smtp.host",
            "SMTP_PORT": 25,
            "EMAIL_DEBUG_LEVEL": 0,
            "RELAY_ADDRESS": "relay.only.this.set",
            "RELAY_PORT": None,
            "RELAY_PASSWORD": None,
            "RELAY_USER": None,
        },
    )
    es.send_email("subject", "body", files=None)
    assert any(level == "error" and "Misconfigured environment variables" in msg for level, msg in logger.messages)
