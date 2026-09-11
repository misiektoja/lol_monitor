"""Tests for SMTP validation and the message the tool actually hands to the server."""

import email
import smtplib
from email.header import decode_header, make_header

import pytest


# Verifies a valid notification is delivered over TLS to the configured recipient
def test_notification_is_delivered_over_tls(lm_module, smtp_double):
    assert lm_module.send_email("LoL user is in game now", "body text", "", True) == 0

    delivery = smtp_double.last
    assert delivery.host == "smtp.example.test"
    assert delivery.port == 587
    assert delivery.started_tls is True
    assert delivery.login_args == ("monitor@example.test", "not-a-real-password")
    assert delivery.sent["receiver"] == "alerts@example.test"
    assert delivery.quit_called is True


# Verifies a delivered message is traced with the recipient and the subject, so a verbose log shows what went where
def test_a_delivered_message_is_traced_with_its_recipient(lm_module, monkeypatch, smtp_double, capsys):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)

    lm_module.send_email("LoL user is in game now", "body text", "", True)

    assert "* Email delivered to alerts@example.test: 'LoL user is in game now'" in capsys.readouterr().out


# Verifies DELIVERY_CONFIRMATIONS drops the delivery line without turning the rest of verbose mode off
def test_delivery_confirmations_can_be_turned_off(lm_module, monkeypatch, smtp_double, capsys):
    monkeypatch.setattr(lm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(lm_module, "DELIVERY_CONFIRMATIONS", False)

    assert lm_module.send_email("LoL user is in game now", "body text", "", True) == 0

    assert "Email delivered" not in capsys.readouterr().out


# Verifies a plain SMTP session skips the TLS upgrade when the operator turned SSL off
def test_plain_session_skips_the_tls_upgrade(lm_module, smtp_double):
    assert lm_module.send_email("subject", "body", "", False) == 0

    assert smtp_double.last.started_tls is False


# Verifies both message parts are sent as UTF-8, so a player name with non-ASCII characters survives delivery
def test_message_carries_both_parts_as_utf8(lm_module, smtp_double):
    lm_module.send_email("LoL user Łukasz plays Kai'Sa", "plain body with Łukasz", "<b>html body with Łukasz</b>", True)

    message = email.message_from_string(smtp_double.last.sent["message"])
    payload_types = [part.get_content_type() for part in message.walk() if part.get_content_maintype() == "text"]
    assert payload_types == ["text/plain", "text/html"]
    decoded = []
    for part in message.walk():
        if part.get_content_maintype() != "text":
            continue
        payload = part.get_payload(decode=True)
        assert isinstance(payload, bytes)
        decoded.append(payload.decode("utf-8"))
    assert "Łukasz" in decoded[0]
    assert "Łukasz" in decoded[1]
    assert "Łukasz" in str(make_header(decode_header(message["Subject"])))


# Verifies an IP address is accepted as the SMTP host, which a self-hosted relay commonly uses
def test_ip_address_host_is_accepted(lm_module, smtp_double, monkeypatch):
    monkeypatch.setattr(lm_module, "SMTP_HOST", "192.0.2.25")

    assert lm_module.send_email("subject", "body", "", True) == 0


@pytest.mark.parametrize("setting,value", [
    ("SMTP_HOST", "not a host"),
    ("SMTP_PORT", 0),
    ("SMTP_PORT", 70000),
    ("SMTP_PORT", "not a port"),
    ("SENDER_EMAIL", "not-an-email"),
    ("RECEIVER_EMAIL", "not-an-email"),
    ("SMTP_USER", "your_smtp_user"),
    ("SMTP_USER", ""),
    ("SMTP_PASSWORD", "your_smtp_password"),
    ("SMTP_PASSWORD", ""),
])
# Verifies incomplete or placeholder SMTP settings are refused before any connection is attempted
def test_incomplete_settings_are_refused_without_connecting(lm_module, smtp_double, monkeypatch, setting, value):
    monkeypatch.setattr(lm_module, setting, value)

    assert lm_module.send_email("subject", "body", "", True) == 1
    assert smtp_double.last is None


@pytest.mark.parametrize("setting,value", [
    ("SMTP_HOST", "not a host"),
    ("SMTP_PORT", "not a port"),
    ("SENDER_EMAIL", "not-an-email"),
    ("SMTP_PASSWORD", ""),
])
# Verifies a refused setting names the fix and the guide, so no delivery path reports without saying what to do
def test_a_refused_setting_carries_the_shared_error_block(lm_module, smtp_double, monkeypatch, capsys, setting, value):
    monkeypatch.setattr(lm_module, setting, value)

    assert lm_module.send_email("subject", "body", "", True) == 1

    output = capsys.readouterr().out
    assert "* Error: The SMTP settings are incorrect (" in output
    assert "To fix: Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file" in output
    assert f"Guide: {lm_module.SMTP_GUIDE_URL}" in output


# Verifies a message the tool cannot send carries the same block as an unusable setting
def test_an_unsendable_message_carries_the_shared_error_block(lm_module, smtp_double, capsys):
    assert lm_module.send_email("", "body", "", True) == 1
    assert lm_module.send_email("subject", "", "", True) == 1

    output = capsys.readouterr().out
    assert output.count("* Error: The SMTP settings are incorrect (") == 2
    assert output.count(f"Guide: {lm_module.SMTP_GUIDE_URL}") == 2


# Verifies a message with nothing to say is refused rather than delivered empty
def test_empty_message_is_refused(lm_module, smtp_double):
    assert lm_module.send_email("subject", "", "", True) == 1
    assert lm_module.send_email("", "body", "", True) == 1
    assert smtp_double.last is None


# Verifies a failing SMTP server is reported as a failure instead of raising into the monitoring loop
def test_smtp_failures_are_reported_not_raised(lm_module, monkeypatch, capsys):
    # Refuses the connection the way an unreachable relay would
    def refuse(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "service not available")

    monkeypatch.setattr(lm_module.smtplib, "SMTP", refuse)

    assert lm_module.send_email("subject", "body", "", True) == 1
    assert "The SMTP server could not be reached" in capsys.readouterr().out


# Verifies the configured timeout reaches the SMTP client, so a hung relay cannot stall the poll loop
def test_timeout_is_passed_to_the_smtp_client(lm_module, smtp_double):
    lm_module.send_email("subject", "body", "", True, smtp_timeout=5)

    assert smtp_double.last.timeout == 5
