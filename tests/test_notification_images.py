"""Tests for the champion icon: what is downloaded, what the email embeds and what ntfy receives."""

import email

import pytest
import requests as req

from conftest import FakeImageResponse, FakeWebhookResponse

NTFY_URL = "https://ntfy.sh/my-private-topic"
DISCORD_URL = "https://discord.com/api/webhooks/123456789/private-token-value"
ICON_URL = "https://ddragon.leagueoflegends.com/cdn/15.1.1/img/champion/Ahri.png"
ICON_BYTES = b"\x89PNG\r\n\x1a\nfake-champion-icon"


@pytest.fixture
# Puts the module in the state an ntfy run with the attachment switched on starts from
def ntfy_images(monkeypatch, lm_module):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", NTFY_URL)
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "NTFY_IMAGES", True)
    return lm_module


# ---------------------------------------------------------------------------
# The download
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    ICON_URL,
    "https://ddragon.leagueoflegends.com/cdn/img/champion/Ahri.png",
])
# Verifies an icon on the Data Dragon host is accepted
def test_a_data_dragon_icon_url_is_accepted(lm_module, url):
    assert lm_module.champion_icon_url_is_allowed(url) is True


@pytest.mark.parametrize("url", [
    "",
    None,
    "http://ddragon.leagueoflegends.com/cdn/img/champion/Ahri.png",
    "https://ddragon.leagueoflegends.com.evil.test/Ahri.png",
    "https://evil.test/Ahri.png",
    "https://",
])
# Verifies any other destination is refused, so no alert can make the tool fetch an arbitrary URL
def test_any_other_icon_url_is_refused(lm_module, url):
    assert lm_module.champion_icon_url_is_allowed(url) is False


# Verifies a downloaded icon is returned with the MIME subtype the response declared
def test_a_downloaded_icon_carries_its_subtype(lm_module, webhook_session):
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))

    assert lm_module.fetch_champion_icon(ICON_URL) == (ICON_BYTES, "png")


# Verifies the download pins the deadline, the TLS setting and the redirect policy the tool chose
def test_the_download_pins_its_deadline_tls_and_redirect_policy(lm_module, monkeypatch, webhook_session):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", True)
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))

    lm_module.fetch_champion_icon(ICON_URL)

    request = webhook_session.gets[0]
    assert request["url"] == ICON_URL
    assert request["timeout"] == lm_module.WEBHOOK_TIMEOUT_SECONDS
    assert request["verify"] is True
    assert request["allow_redirects"] is False
    assert request["stream"] is True


# Verifies the same champion is downloaded once, since it appears again in the summary of the match it started
def test_the_same_icon_is_downloaded_once(lm_module, webhook_session):
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))

    first = lm_module.fetch_champion_icon(ICON_URL)
    second = lm_module.fetch_champion_icon(ICON_URL)

    assert first == second
    assert len(webhook_session.gets) == 1


# Verifies the cache keeps the icons seen most recently rather than growing for the length of the run
def test_the_icon_cache_is_bounded(lm_module, webhook_session):
    urls = [f"https://ddragon.leagueoflegends.com/cdn/15.1.1/img/champion/Champion{index}.png" for index in range(lm_module.CHAMPION_ICON_CACHE_LIMIT + 1)]
    webhook_session.icons.extend(FakeImageResponse(ICON_BYTES) for _ in urls)

    for url in urls:
        lm_module.fetch_champion_icon(url)

    assert len(lm_module._champion_icon_cache) == lm_module.CHAMPION_ICON_CACHE_LIMIT
    assert urls[0] not in lm_module._champion_icon_cache
    assert urls[-1] in lm_module._champion_icon_cache


# Verifies a URL outside Data Dragon is never requested
def test_an_unexpected_host_is_never_requested(lm_module, webhook_session):
    assert lm_module.fetch_champion_icon("https://evil.test/Ahri.png") is None
    assert webhook_session.gets == []


@pytest.mark.parametrize("response", [
    FakeImageResponse(ICON_BYTES, headers={"Content-Type": "text/html"}),
    FakeImageResponse(b"", headers={"Content-Type": "image/png"}),
    FakeImageResponse(b"x" * 8, headers={"Content-Type": "image/png", "Content-Length": "999999999"}),
    FakeImageResponse(ICON_BYTES, error=req.HTTPError("404 Not Found")),
    req.ConnectionError("the host could not be reached"),
])
# Verifies anything that is not a usable icon returns nothing, so the alert is still sent without it
def test_an_unusable_response_returns_nothing(lm_module, webhook_session, response):
    webhook_session.icons.append(response)

    assert lm_module.fetch_champion_icon(ICON_URL) is None


# Verifies a response that keeps streaming past the limit is abandoned rather than read into memory
def test_an_oversized_stream_is_abandoned(lm_module, webhook_session, monkeypatch):
    monkeypatch.setattr(lm_module, "CHAMPION_ICON_LIMIT_BYTES", 16)
    webhook_session.icons.append(FakeImageResponse(b"x" * 64, headers={"Content-Type": "image/png"}))

    assert lm_module.fetch_champion_icon(ICON_URL) is None


# Verifies a failed download is traced with what the run did instead, without the exception reaching the caller
def test_a_failed_download_is_traced(lm_module, monkeypatch, webhook_session, capsys):
    monkeypatch.setattr(lm_module, "DEBUG_MODE", True)
    webhook_session.icons.append(req.ConnectionError("the host could not be reached"))

    lm_module.fetch_champion_icon(ICON_URL)

    output = capsys.readouterr().out
    assert "Champion icon download" in output
    assert "fallback=sending without the icon" in output


# ---------------------------------------------------------------------------
# The switches
# ---------------------------------------------------------------------------


# Verifies each channel only downloads an icon when its own setting asks for one
@pytest.mark.parametrize("setting,builder", [("EMAIL_IMAGES", "build_email_champion_icon"), ("NTFY_IMAGES", "build_ntfy_champion_icon")])
def test_an_icon_is_only_built_for_an_enabled_channel(lm_module, monkeypatch, webhook_session, setting, builder):
    monkeypatch.setattr(lm_module, setting, False)

    assert getattr(lm_module, builder)(ICON_URL) is None
    assert webhook_session.gets == []

    monkeypatch.setattr(lm_module, setting, True)
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))

    assert getattr(lm_module, builder)(ICON_URL) == (ICON_BYTES, "png")


# Verifies an alert with no champion never reaches the download, which is what an error alert looks like
def test_an_alert_without_a_champion_fetches_nothing(lm_module, monkeypatch, webhook_session):
    monkeypatch.setattr(lm_module, "EMAIL_IMAGES", True)
    monkeypatch.setattr(lm_module, "NTFY_IMAGES", True)

    assert lm_module.build_email_champion_icon("") is None
    assert lm_module.build_ntfy_champion_icon("") is None
    assert webhook_session.gets == []


# ---------------------------------------------------------------------------
# The email
# ---------------------------------------------------------------------------


# Verifies the icon reference is added at the end of the body, after the timestamp the alert closes with
def test_the_icon_reference_is_added_at_the_end_of_the_body(lm_module):
    rendered = lm_module.add_email_champion_icon_html("<html><head></head><body>Champion: Ahri<br>Timestamp: now</body></html>")

    assert rendered == '<html><head></head><body>Champion: Ahri<br>Timestamp: now<br><br><img src="cid:champion_icon" alt="Champion icon"></body></html>'


# Verifies a body with no closing tag still gets the icon, so an unexpected shape does not lose it
def test_a_body_without_a_closing_tag_still_gets_the_icon(lm_module):
    assert lm_module.add_email_champion_icon_html("Champion: Ahri").endswith('<img src="cid:champion_icon" alt="Champion icon">')


# Verifies the delivered message carries the icon inline beside both text parts
def test_the_delivered_message_carries_the_icon_inline(lm_module, smtp_double):
    body_html = lm_module.add_email_champion_icon_html("<html><head></head><body>Champion: Ahri</body></html>")

    assert lm_module.send_email("subject", "body text", body_html, True, image_bytes=ICON_BYTES) == 0

    message = email.message_from_string(smtp_double.last.sent["message"])
    assert message.get_content_type() == "multipart/related"
    assert [part.get_content_type() for part in message.walk()] == ["multipart/related", "multipart/alternative", "text/plain", "text/html", "image/png"]
    icon_part = [part for part in message.walk() if part.get_content_type() == "image/png"][0]
    assert icon_part["Content-ID"] == f"<{lm_module.EMAIL_CHAMPION_ICON_CONTENT_ID}>"
    assert icon_part.get_payload(decode=True) == ICON_BYTES
    assert icon_part.get_filename() == f"{lm_module.EMAIL_CHAMPION_ICON_CONTENT_ID}.png"


# Verifies an email with no icon keeps the plain two-part shape it has always had
def test_an_email_without_an_icon_keeps_its_plain_shape(lm_module, smtp_double):
    lm_module.send_email("subject", "body text", "<html><body>Champion: Ahri</body></html>", True)

    message = email.message_from_string(smtp_double.last.sent["message"])
    assert message.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in message.walk()] == ["multipart/alternative", "text/plain", "text/html"]


# Verifies the enabled setting reaches a real notification, icon bytes and body reference together
def test_an_enabled_email_notification_embeds_the_icon(lm_module, monkeypatch, smtp_double, webhook_session):
    monkeypatch.setattr(lm_module, "EMAIL_IMAGES", True)
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))

    lm_module.send_notification_channels("status", "subject", "body text", "<html><body>Champion: Ahri</body></html>", email_enabled=True, image_url=ICON_URL)

    message = email.message_from_string(smtp_double.last.sent["message"])
    html_part = [part for part in message.walk() if part.get_content_type() == "text/html"][0]
    payload = html_part.get_payload(decode=True)
    assert isinstance(payload, bytes)
    assert 'src="cid:champion_icon"' in payload.decode("utf-8")
    assert [part for part in message.walk() if part.get_content_type() == "image/png"][0].get_payload(decode=True) == ICON_BYTES


# Verifies a text-only alert is sent when the icon cannot be downloaded, rather than no alert at all
def test_a_failed_icon_still_sends_the_notification(lm_module, monkeypatch, smtp_double, webhook_session):
    monkeypatch.setattr(lm_module, "EMAIL_IMAGES", True)
    webhook_session.icons.append(req.ConnectionError("the host could not be reached"))

    lm_module.send_notification_channels("status", "subject", "body text", "<html><body>Champion: Ahri</body></html>", email_enabled=True, image_url=ICON_URL)

    message = email.message_from_string(smtp_double.last.sent["message"])
    assert message.get_content_type() == "multipart/alternative"
    assert "cid:champion_icon" not in smtp_double.last.sent["message"]


# Verifies an alert with no HTML body is left alone, since a plain-text email has nowhere to show an icon
def test_a_plain_text_notification_fetches_no_icon(lm_module, monkeypatch, smtp_double, webhook_session):
    monkeypatch.setattr(lm_module, "EMAIL_IMAGES", True)

    lm_module.send_notification_channels("status", "subject", "body text", "", email_enabled=True, image_url=ICON_URL)

    assert webhook_session.gets == []
    assert email.message_from_string(smtp_double.last.sent["message"]).get_content_type() == "multipart/alternative"


# ---------------------------------------------------------------------------
# The ntfy attachment
# ---------------------------------------------------------------------------


# Verifies the icon is posted as the request body with the alert text moved into the query
def test_the_icon_is_posted_as_the_ntfy_body(ntfy_images, webhook_session):
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))
    webhook_session.responses.append(FakeWebhookResponse(200))

    assert ntfy_images.send_webhook("subject", "body text", "status", image_url=ICON_URL) == 0

    post = webhook_session.posts[0]
    assert post["url"] == NTFY_URL
    assert post["data"] == ICON_BYTES
    assert post["params"] == {"title": "subject", "message": "body text"}
    assert post["headers"]["Content-Type"] == "image/png"
    assert post["headers"]["X-Filename"] == f"{ntfy_images.NTFY_CHAMPION_ICON_FILENAME}.png"


# Verifies the ntfy options still travel with an attachment, so a priority or tag is not lost with the icon
def test_the_ntfy_options_travel_with_the_attachment(ntfy_images, webhook_session):
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))
    webhook_session.responses.append(FakeWebhookResponse(200))

    ntfy_images.send_webhook("subject", "body text", "status", image_url=ICON_URL, ntfy_priority=4, ntfy_tags="video_game")

    assert webhook_session.posts[0]["params"] == {"title": "subject", "priority": 4, "tags": "video_game", "message": "body text"}


# Verifies a rejected attachment is retried as a text-only alert, since the alert matters more than its icon
def test_a_rejected_attachment_falls_back_to_text(ntfy_images, webhook_session):
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))
    webhook_session.responses.extend([FakeWebhookResponse(400), FakeWebhookResponse(200)])

    assert ntfy_images.send_webhook("subject", "body text", "status", image_url=ICON_URL, sleeper=lambda seconds: None) == 0

    assert webhook_session.posts[0]["data"] == ICON_BYTES
    assert webhook_session.posts[1]["data"] == b"body text"
    assert webhook_session.posts[1]["params"] == {"title": "subject"}


# Verifies an attachment lost to a network failure is retried as a text-only alert
def test_an_unreachable_attachment_falls_back_to_text(ntfy_images, webhook_session):
    webhook_session.icons.append(FakeImageResponse(ICON_BYTES))
    webhook_session.responses.extend([req.ConnectionError("connection reset"), FakeWebhookResponse(200)])

    assert ntfy_images.send_webhook("subject", "body text", "status", image_url=ICON_URL, sleeper=lambda seconds: None) == 0

    assert webhook_session.posts[1]["data"] == b"body text"


# Verifies the switched-off setting keeps the plain text body ntfy has always received
def test_the_disabled_setting_keeps_a_plain_ntfy_body(ntfy_images, monkeypatch, webhook_session):
    monkeypatch.setattr(ntfy_images, "NTFY_IMAGES", False)
    webhook_session.responses.append(FakeWebhookResponse(200))

    ntfy_images.send_webhook("subject", "body text", "status", image_url=ICON_URL)

    assert webhook_session.gets == []
    assert webhook_session.posts[0]["data"] == b"body text"


# Verifies Discord never downloads the icon, since its template carries the URL for the embed instead
def test_discord_never_downloads_the_icon(lm_module, monkeypatch, webhook_session):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", DISCORD_URL)
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "NTFY_IMAGES", True)
    webhook_session.responses.append(FakeWebhookResponse(204))

    lm_module.send_webhook("subject", "body text", "status", image_url=ICON_URL)

    assert webhook_session.gets == []
    assert webhook_session.posts[0]["json"]["embeds"][0]["thumbnail"]["url"] == ICON_URL
