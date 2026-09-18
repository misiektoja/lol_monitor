"""Tests for the webhook channel: what is built, what is sent, what is refused and what the private URL never reveals."""


import pytest
import requests as req

DISCORD_URL = "https://discord.com/api/webhooks/123456789/private-token-value"
NTFY_URL = "https://ntfy.sh/my-private-topic"


@pytest.fixture
# Puts the module in the state a configured Discord webhook run starts from
def discord(monkeypatch, lm_module):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", DISCORD_URL)
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    return lm_module


@pytest.fixture
# Puts the module in the state a configured ntfy run starts from
def ntfy(monkeypatch, lm_module):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", NTFY_URL)
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    return lm_module


# Records the delays a delivery waited instead of sleeping through them
class RecordingSleeper:
    def __init__(self):
        self.delays = []

    # Records one wait without spending it
    def __call__(self, seconds):
        self.delays.append(seconds)


# ---------------------------------------------------------------------------
# The destination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", [DISCORD_URL, NTFY_URL, "https://example.test:8443/hooks/abc"])
# Verifies a complete private HTTPS destination is accepted
def test_a_complete_https_destination_is_accepted(lm_module, url):
    assert lm_module.validate_webhook_url(url) is True


@pytest.mark.parametrize("url", ["", "   ", "your_webhook_url", "http://ntfy.sh/topic", "https://ntfy.sh", "https://ntfy.sh/", "https://user:pass@ntfy.sh/topic", "ntfy.sh/topic", None, 12])
# Verifies anything that is not a complete private HTTPS link is refused, including a link carrying credentials
def test_an_incomplete_or_unsafe_destination_is_refused(lm_module, url):
    assert lm_module.validate_webhook_url(url) is False


# Verifies the configured destination is what an argument-free call checks, so the caller cannot forget to pass it
def test_the_configured_destination_is_what_an_argument_free_call_checks(discord):
    assert discord.validate_webhook_url() is True
    discord.WEBHOOK_URL = "not-a-url"
    assert discord.validate_webhook_url() is False


@pytest.mark.parametrize("url,expected", [
    (NTFY_URL, "ntfy"),
    ("https://NTFY.SH/Topic", "ntfy"),
    (DISCORD_URL, "discord"),
    ("https://discord.com/api/v10/webhooks/123/token", "discord"),
    ("https://ptb.discord.com/api/webhooks/123/token", "discord"),
    ("https://discordapp.com/api/webhooks/123/token", "discord"),
    ("https://discord.com/channels/123/456", ""),
    ("https://discord.com/api/webhooks/not-a-number/token", ""),
    ("https://example.test/hooks/abc", ""),
    ("not-a-url", ""),
])
# Verifies the provider is read from the URL shape alone, so a mismatched configured value can be corrected
def test_the_provider_is_detected_from_the_url_shape(lm_module, url, expected):
    assert lm_module.detect_webhook_provider(url) == expected


@pytest.mark.parametrize("value,expected", [
    ("my-private-topic", "https://ntfy.sh/my-private-topic"),
    (NTFY_URL, NTFY_URL),
    ("  spaced-topic  ", "https://ntfy.sh/spaced-topic"),
    ("topic with spaces", ""),
    ("a" * 65, ""),
    ("", ""),
    (None, ""),
])
# Verifies a bare ntfy topic name is expanded to its full URL and anything ambiguous is refused
def test_a_bare_ntfy_topic_expands_to_its_full_url(lm_module, value, expected):
    assert lm_module.normalize_ntfy_topic_url(value) == expected


@pytest.mark.parametrize("configured,expected", [("discord", "discord"), ("  NTFY  ", "ntfy"), ("Discord", "discord"), ("slack", ""), ("", ""), (7, "")])
# Verifies the configured provider is casefolded and anything unsupported reads as unset rather than as itself
def test_the_configured_provider_is_normalized(lm_module, configured, expected):
    assert lm_module.normalized_webhook_provider(configured) == expected


# Verifies the configured setting is what an argument-free call reads, so the caller cannot forget to pass it
def test_the_configured_provider_is_what_an_argument_free_call_reads(ntfy):
    assert ntfy.normalized_webhook_provider() == "ntfy"


@pytest.mark.parametrize("provider,expected", [("discord", "Discord"), ("ntfy", "ntfy"), ("slack", "an unset provider"), ("", "an unset provider")])
# Verifies each service is named the way it spells itself, since the stored value is casefolded for comparisons
def test_each_provider_is_displayed_the_way_it_spells_itself(lm_module, provider, expected):
    assert lm_module.webhook_provider_display_name(provider) == expected


# Verifies a trace names the destination host alone, so the private path never reaches the screen or the log
def test_a_trace_names_the_host_without_the_private_path(discord):
    host = discord.webhook_destination_host()

    assert host == "discord.com"
    assert "private-token-value" not in host


# ---------------------------------------------------------------------------
# Which alerts are on
# ---------------------------------------------------------------------------


# Verifies the master switch gates every alert type, so switching webhooks off silences all of them at once
def test_the_master_switch_gates_every_alert_type(discord, monkeypatch):
    assert discord.webhook_event_enabled("status") is True
    assert discord.webhook_event_enabled("error") is True

    monkeypatch.setattr(discord, "WEBHOOK_ENABLED", False)

    assert discord.webhook_event_enabled("status") is False
    assert discord.webhook_event_enabled("error") is False


# Verifies each alert type is gated by its own setting, so one can be on while the other is off
def test_each_alert_type_is_gated_by_its_own_setting(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_ERROR_NOTIFICATION", False)

    assert discord.webhook_event_enabled("status") is True
    assert discord.webhook_event_enabled("error") is False


# Verifies an alert type the tool does not have is off rather than treated as enabled
def test_an_unknown_alert_type_is_off(discord):
    assert discord.webhook_event_enabled("mastery") is False


# Verifies the categories are listed in a fixed display order, which is what the doctor row and the summary print
def test_the_selected_categories_are_listed_in_display_order(discord):
    assert discord._selected_webhook_notification_categories() == ["status changes", "errors"]


# Verifies the startup list is empty while webhooks are off, even with alert types selected
def test_the_startup_categories_are_empty_while_webhooks_are_off(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_ENABLED", False)

    assert discord._selected_webhook_notification_categories() == ["status changes", "errors"]
    assert discord._startup_webhook_notification_categories() == []


# ---------------------------------------------------------------------------
# The retry delay
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("candidate,expected", [("2", 2.0), (3, 3.0), ("2.5", 2.5), ("", None), (None, None), ("soon", None), ("nan", None), ("inf", None)])
# Verifies a numeric retry value is read as seconds and an unusable one reports nothing rather than zero
def test_a_numeric_retry_value_is_read_as_seconds(lm_module, candidate, expected):
    assert lm_module.parse_retry_after_seconds(candidate) == expected


# Verifies an HTTP-date retry value is read as the seconds remaining until that moment
def test_an_http_date_retry_value_is_read_as_seconds_remaining(lm_module):
    seconds = lm_module.parse_retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT")

    assert seconds is not None and seconds < 0


# Verifies the first usable candidate wins, so a header and a body value cannot both apply
def test_the_first_usable_retry_candidate_wins(lm_module):
    assert lm_module.bounded_retry_after_seconds(["nonsense", "2", "4"], fallback=1.0, maximum=5.0) == 2.0


# Verifies an untrusted delay is bounded on both sides, so a service cannot stall the tool or rush it
def test_an_untrusted_retry_delay_is_bounded_on_both_sides(lm_module):
    assert lm_module.bounded_retry_after_seconds(["3600"], fallback=1.0, maximum=5.0) == 5.0
    assert lm_module.bounded_retry_after_seconds(["-30"], fallback=1.0, maximum=5.0) == 0.0
    assert lm_module.bounded_retry_after_seconds([], fallback=1.0, maximum=5.0) == 1.0


# Verifies a rate-limit response is read from the header first and from the JSON body when the header is missing
def test_a_rate_limit_delay_is_read_from_the_header_then_the_body(lm_module):
    from conftest import FakeWebhookResponse

    with_header = FakeWebhookResponse(429, headers={"Retry-After": "2"}, payload={"retry_after": 4})
    body_only = FakeWebhookResponse(429, payload={"retry_after": 3})
    neither = FakeWebhookResponse(429)

    assert lm_module.webhook_retry_after_seconds(with_header) == 2.0
    assert lm_module.webhook_retry_after_seconds(body_only) == 3.0
    assert lm_module.webhook_retry_after_seconds(neither) == lm_module.WEBHOOK_FALLBACK_RETRY_SECONDS


# Verifies the cap the delivery path applies is the short one, so a hostile header cannot hold a run open
def test_the_delivery_path_caps_a_hostile_retry_header(lm_module):
    from conftest import FakeWebhookResponse

    delay = lm_module.webhook_retry_after_seconds(FakeWebhookResponse(429, headers={"Retry-After": "86400"}))

    assert delay == lm_module.WEBHOOK_MAX_RETRY_AFTER_SECONDS


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------


# Verifies placeholders are substituted through every level of a nested template
def test_placeholders_are_substituted_through_a_nested_template(lm_module):
    template = {"a": "{title}", "b": ["{title}", {"c": "{description}"}], "d": ("{title}",), "e": 7}

    rendered = lm_module.format_payload(template, {"title": "T", "description": "D"})

    assert rendered == {"a": "T", "b": ["T", {"c": "D"}], "d": ("T",), "e": 7}


# Verifies the two placeholders that stand for non-text values keep their type instead of becoming strings
def test_the_non_text_placeholders_keep_their_type(lm_module):
    rendered = lm_module.format_payload({"color": "{color}", "fields": "{fields}"}, {"color": 123, "fields": [{"name": "n"}]})

    assert rendered == {"color": 123, "fields": [{"name": "n"}]}


# Reports an unknown field before attempting delivery
def test_an_unknown_placeholder_names_the_template_error(lm_module):
    with pytest.raises(ValueError, match="not_a_placeholder"):
        lm_module.format_payload("{not_a_placeholder}", {"title": "T"})


# Verifies the alert text is sanitized and bounded, so a hostile player name cannot drive the receiving service
def test_the_alert_text_is_sanitized_and_bounded(discord):
    values = discord.build_webhook_values("subject\r\nwith a break", "body\r\nline", "status")

    assert values["title"] == "subject with a break"
    assert values["description"] == "body\nline"
    assert len(discord.build_webhook_values("t" * 500, "d" * 9000, "status")["title"]) == discord.WEBHOOK_EMBED_TITLE_LIMIT
    assert len(discord.build_webhook_values("t" * 500, "d" * 9000, "status")["description"]) == discord.WEBHOOK_EMBED_DESCRIPTION_LIMIT


# Verifies an empty subject still names the tool, so no service receives a titleless notification
def test_an_empty_subject_falls_back_to_the_tool_name(discord):
    assert discord.build_webhook_values("   ", "body", "status")["title"] == "LoL Monitor"


# Verifies each alert type carries its own colour, which is what makes a failure readable next to a status change
def test_each_alert_type_carries_its_own_colour(discord):
    status_color = discord.build_webhook_values("t", "d", "status")["color"]
    error_color = discord.build_webhook_values("t", "d", "error")["color"]

    assert status_color == discord.WEBHOOK_EVENT_COLORS["status"]
    assert error_color == discord.WEBHOOK_EVENT_COLORS["error"]
    assert status_color != error_color
    assert discord.build_webhook_values("t", "d", "mastery")["color"] == discord.WEBHOOK_DEFAULT_COLOR


# Verifies the version reaches the payload, so a report names the release that sent it
def test_the_running_version_reaches_the_payload(discord):
    payload = discord.build_webhook_payload("subject", "body", "status")

    assert payload["embeds"][0]["footer"]["text"] == f"LoL Monitor v{discord.VERSION}"


# Verifies mentions stay disabled even when a customized template asks for them
def test_mentions_stay_disabled_even_when_the_template_asks_for_them(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_TEMPLATE", {"content": "{title}", "allowed_mentions": {"parse": ["everyone"]}})

    payload = discord.build_webhook_payload("subject", "body", "status")

    assert payload["allowed_mentions"] == {"parse": []}


# Verifies the optional Discord display fields are dropped when unset rather than sent empty
def test_the_unset_display_fields_are_dropped_rather_than_sent_empty(discord):
    payload = discord.build_webhook_payload("subject", "body", "status")

    assert "username" not in payload
    assert "avatar_url" not in payload
    assert "thumbnail" not in payload["embeds"][0]


# Verifies a champion icon reaches the embed thumbnail the template has always carried, which was sent empty
# and dropped on every alert until an alert had an icon to put in it
def test_a_champion_icon_reaches_the_embed_thumbnail(discord, monkeypatch):
    monkeypatch.setattr(discord, "_ddragon_version_cache", "15.19.1")
    icon = discord.champion_image_url("Ahri")

    payload = discord.build_webhook_payload("subject", "body", "status", icon)

    assert icon == "https://ddragon.leagueoflegends.com/cdn/15.19.1/img/champion/Ahri.png"
    assert payload["embeds"][0]["thumbnail"] == {"url": icon}


# Verifies the icon a delivered alert carries is the one the caller passed, since the value is built per alert
# rather than read from a setting
def test_the_icon_an_alert_carries_reaches_the_delivered_payload(discord, monkeypatch, webhook_session):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "_ddragon_version_cache", "15.19.1")
    webhook_session.responses.append(FakeWebhookResponse(204))

    assert discord.send_webhook("subject", "body", "status", force=True, image_url=discord.champion_image_url("Lux")) == 0

    sent = webhook_session.posts[0]["json"]
    assert sent["embeds"][0]["thumbnail"] == {"url": "https://ddragon.leagueoflegends.com/cdn/15.19.1/img/champion/Lux.png"}


# Verifies an icon URL is built only from a known release and a plain champion name, since anything else would
# be interpolated into a URL this tool then sends to a third-party service
@pytest.mark.parametrize("version,champion", [("", "Ahri"), ("15.19.1", "../../../etc/passwd"), ("15.19.1", "Ahri/../x"), ("15.19.1", "Kai'Sa"), ("15.19.1", ""), ("15.19.1", None), ("../evil", "Ahri"), ("latest", "Ahri")])
def test_an_icon_url_is_refused_unless_both_halves_are_plain(lm_module, monkeypatch, version, champion):
    monkeypatch.setattr(lm_module, "_ddragon_version_cache", version)

    assert lm_module.champion_image_url(champion) == ""


# Verifies a configured display name and avatar do reach the payload
def test_a_configured_display_name_and_avatar_reach_the_payload(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_USERNAME", "LoL Monitor")
    monkeypatch.setattr(discord, "WEBHOOK_AVATAR_URL", "https://example.test/avatar.png")

    payload = discord.build_webhook_payload("subject", "body", "status")

    assert payload["username"] == "LoL Monitor"
    assert payload["avatar_url"] == "https://example.test/avatar.png"


# Verifies a template the tool cannot format is reported as a configuration error rather than sent half-built
def test_a_template_that_cannot_be_formatted_is_reported(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_TEMPLATE", {"content": "{title"})

    with pytest.raises(ValueError, match="WEBHOOK_TEMPLATE"):
        discord.build_webhook_payload("subject", "body", "status")


# Verifies a configured transformation is applied to the value it names
def test_a_configured_transformation_is_applied(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_TRANSFORMS", [("title", "upper"), ("description", "replace", "**", "")])

    values = discord.build_webhook_values("subject", "**body**", "status")

    assert values["title"] == "SUBJECT"
    assert values["description"] == "body"


# Verifies a transformation naming a value that is not text is skipped rather than raised
def test_a_transformation_on_a_non_text_value_is_skipped(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_TRANSFORMS", [("color", "upper"), ("missing", "upper")])

    assert discord.build_webhook_values("subject", "body", "status")["color"] == discord.WEBHOOK_EVENT_COLORS["status"]


# Verifies a transformation that fails names the entry, so the configuration line to fix is obvious
def test_a_failing_transformation_names_its_entry(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_TRANSFORMS", [("title", "replace")])

    with pytest.raises(ValueError, match="entry 1"):
        discord.build_webhook_values("subject", "body", "status")


@pytest.mark.parametrize("setting,value,expected", [
    ("WEBHOOK_USERNAME", 7, "WEBHOOK_USERNAME must be a string"),
    ("WEBHOOK_AVATAR_URL", 7, "WEBHOOK_AVATAR_URL must be a string"),
    ("WEBHOOK_AVATAR_URL", "http://example.test/a.png", "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"),
    ("WEBHOOK_TEMPLATE", 7, "WEBHOOK_TEMPLATE must be a dictionary or a JSON object string"),
    ("WEBHOOK_TRANSFORMS", "upper", "WEBHOOK_TRANSFORMS must be a list or tuple"),
    ("WEBHOOK_TRANSFORMS", [("title",)], "WEBHOOK_TRANSFORMS entry 1 must contain a field name and string method name"),
    ("WEBHOOK_TRANSFORMS", [("title", "__class__")], "WEBHOOK_TRANSFORMS entry 1 uses an unsupported string method"),
    ("WEBHOOK_TRANSFORMS", [("title", "not_a_method")], "WEBHOOK_TRANSFORMS entry 1 uses an unsupported string method"),
])
# Verifies each unusable customization is named by the setting it belongs to rather than reported as a generic failure
def test_each_unusable_customization_names_its_setting(discord, monkeypatch, setting, value, expected):
    monkeypatch.setattr(discord, setting, value)

    assert discord.validate_webhook_customization("discord") == expected


# Verifies a clean configuration reports no customization error
def test_a_clean_customization_reports_no_error(discord):
    assert discord.validate_webhook_customization("discord") is None


# ---------------------------------------------------------------------------
# The ntfy message
# ---------------------------------------------------------------------------


# Verifies text under the byte limit is returned untouched
def test_text_under_the_byte_limit_is_untouched(lm_module):
    assert lm_module.truncate_utf8_bytes("short", 100, "...") == "short"


# Verifies a cut never leaves half a multi-byte character behind
def test_a_cut_never_leaves_half_a_character(lm_module):
    cut = lm_module.truncate_utf8_bytes("ą" * 50, 21, "")

    assert cut == "ą" * 10
    assert len(cut.encode("utf-8")) <= 21


# Verifies the marker is charged against the limit, so the result still fits what the service accepts
def test_the_truncation_marker_is_charged_against_the_limit(lm_module):
    cut = lm_module.truncate_utf8_bytes("x" * 100, 20, "[cut]")

    assert cut.endswith("[cut]")
    assert len(cut.encode("utf-8")) == 20


# Verifies a limit smaller than the marker still produces something that fits rather than overflowing
def test_a_limit_smaller_than_the_marker_still_fits(lm_module):
    cut = lm_module.truncate_utf8_bytes("x" * 100, 3, "[cut]")

    assert len(cut.encode("utf-8")) <= 3


# Verifies a long alert is cut to ntfy's message limit and says that it was
def test_a_long_alert_is_cut_to_the_ntfy_limit(ntfy):
    title, message = ntfy.build_ntfy_webhook_message("subject", "b" * 10000)

    assert title == "subject"
    assert len(message.encode("utf-8")) <= ntfy.NTFY_MESSAGE_LIMIT_BYTES
    assert message.endswith(ntfy.NTFY_TRUNCATION_SUFFIX)


# Verifies an ntfy title is collapsed onto one line, since a header cannot carry a line break
def test_an_ntfy_title_is_collapsed_onto_one_line(ntfy):
    title, _ = ntfy.build_ntfy_webhook_message("subject\r\nwith a break", "body")

    assert title == "subject with a break"


@pytest.mark.parametrize("priority,tags,expected", [
    (0, "", None),
    (5, "warning", None),
    (6, "", "ntfy priority must be 0 to omit it or an integer from 1 through 5"),
    (-1, "", "ntfy priority must be 0 to omit it or an integer from 1 through 5"),
    (True, "", "ntfy priority must be 0 to omit it or an integer from 1 through 5"),
    ("3", "", "ntfy priority must be 0 to omit it or an integer from 1 through 5"),
    (0, 7, "ntfy tags must be a comma-separated string"),
    (0, "warning\nX-Injected: 1", "ntfy tags must not contain line breaks"),
])
# Verifies unusable ntfy metadata is refused before it reaches a request header
def test_unusable_ntfy_metadata_is_refused(lm_module, priority, tags, expected):
    assert lm_module.validate_ntfy_metadata(priority, tags) == expected


# ---------------------------------------------------------------------------
# The request headers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("headers,expected", [
    ("X-Token: a", "WEBHOOK_HEADERS must be a dictionary of string header names and values"),
    ({"Bad Name": "a"}, "WEBHOOK_HEADERS contains an invalid HTTP header name"),
    ({"X-A": "a", "x-a": "b"}, "WEBHOOK_HEADERS contains duplicate case-insensitive header names"),
    ({"X-A": 7}, "WEBHOOK_HEADERS value for X-A must be a string"),
    ({"X-A": "a\r\nX-Injected: 1"}, "WEBHOOK_HEADERS value for X-A must not contain line breaks"),
])
# Verifies an unusable header mapping is refused, so nothing can smuggle a second header into a request
def test_an_unusable_header_mapping_is_refused(discord, monkeypatch, headers, expected):
    monkeypatch.setattr(discord, "WEBHOOK_HEADERS", headers)

    assert discord.validate_webhook_headers("discord") == expected


@pytest.mark.parametrize("token,expected", [
    ("tk_value", None),
    (7, "NTFY_ACCESS_TOKEN must be a string"),
    ("tk\nX-Injected: 1", "NTFY_ACCESS_TOKEN must not contain line breaks"),
    ("Bearer tk_value", "NTFY_ACCESS_TOKEN must contain only the access token without an Authorization scheme"),
    ("basic dGVzdA==", "NTFY_ACCESS_TOKEN must contain only the access token without an Authorization scheme"),
])
# Verifies an unusable ntfy token is refused, including one that already carries an Authorization scheme
def test_an_unusable_ntfy_token_is_refused(ntfy, monkeypatch, token, expected):
    monkeypatch.setattr(ntfy, "NTFY_ACCESS_TOKEN", token)

    assert ntfy.validate_webhook_headers("ntfy") == expected


# Verifies the ntfy token is only checked for the provider that uses it
def test_the_ntfy_token_is_only_checked_for_ntfy(discord, monkeypatch):
    monkeypatch.setattr(discord, "NTFY_ACCESS_TOKEN", "Bearer tk_value")

    assert discord.validate_webhook_headers("discord") is None


# Verifies every request identifies the tool and its version, so a service owner can tell what is calling
def test_every_request_identifies_the_tool_and_version(discord):
    headers = discord.build_webhook_headers("discord", discord.build_webhook_values("t", "d", "status"))

    assert headers["User-Agent"] == f"LoLMonitor/{discord.VERSION}"


# Verifies a configured User-Agent replaces the default rather than being sent alongside it
def test_a_configured_user_agent_replaces_the_default(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_HEADERS", {"user-agent": "Custom/1.0"})

    headers = discord.build_webhook_headers("discord", discord.build_webhook_values("t", "d", "status"))

    assert [name for name in headers if name.casefold() == "user-agent"] == ["user-agent"]
    assert headers["user-agent"] == "Custom/1.0"


# Verifies ntfy always receives a plain-text body and the token as a Bearer credential
def test_ntfy_receives_plain_text_and_a_bearer_token(ntfy, monkeypatch):
    monkeypatch.setattr(ntfy, "NTFY_ACCESS_TOKEN", "tk_secret_token_value")
    monkeypatch.setattr(ntfy, "WEBHOOK_HEADERS", {"Content-Type": "application/json"})

    headers = ntfy.build_webhook_headers("ntfy", ntfy.build_webhook_values("t", "d", "status"))

    assert headers["Content-Type"] == "text/plain; charset=utf-8"
    assert headers["Authorization"] == "Bearer tk_secret_token_value"


# Verifies a header value built from a placeholder is validated after substitution, not only before it
def test_a_header_built_from_a_placeholder_is_validated_after_substitution(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_HEADERS", {"X-Title": "{title}"})
    values = discord.build_webhook_values("t", "d", "status")
    values["title"] = "ok\r\nX-Injected: 1"

    with pytest.raises(ValueError, match="must not contain line breaks"):
        discord.build_webhook_headers("discord", values)


# Verifies a header placeholder does reach the request when the value it carries is safe
def test_a_safe_header_placeholder_reaches_the_request(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_HEADERS", {"X-Title": "{title}"})

    headers = discord.build_webhook_headers("discord", discord.build_webhook_values("subject", "body", "status"))

    assert headers["X-Title"] == "subject"


# ---------------------------------------------------------------------------
# The delivery
# ---------------------------------------------------------------------------


# Verifies a Discord alert is posted to the configured destination as the built JSON payload
def test_a_discord_alert_is_posted_as_json(discord, webhook_session):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(204))

    assert discord.send_webhook("subject", "body", "status") == 0

    post = webhook_session.posts[0]
    assert post["url"] == DISCORD_URL
    assert post["json"]["embeds"][0]["title"] == "subject"
    assert post["headers"]["User-Agent"] == f"LoLMonitor/{discord.VERSION}"


# Verifies an ntfy alert is posted as the encoded message body with its title and options as query parameters
def test_an_ntfy_alert_is_posted_as_a_plain_body(ntfy, webhook_session):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(200))

    assert ntfy.send_webhook("subject", "body", "error", ntfy_priority=5, ntfy_tags="warning") == 0

    post = webhook_session.posts[0]
    assert post["url"] == NTFY_URL
    assert post["data"] == b"body"
    assert post["params"] == {"title": "subject", "priority": 5, "tags": "warning"}


# Verifies the ntfy options are left out when unset rather than sent as empty values
def test_unset_ntfy_options_are_left_out(ntfy, webhook_session):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(200))

    ntfy.send_webhook("subject", "body", "status")

    assert webhook_session.posts[0]["params"] == {"title": "subject"}


# Preserves escaped JSON templates while enforcing the no-mentions policy
def test_legacy_escaped_json_template_keeps_mentions_disabled(discord, webhook_session, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "WEBHOOK_TEMPLATE", '{{"content": "{title}"}}')
    webhook_session.responses.append(FakeWebhookResponse(204))

    discord.send_webhook("subject", "body", "status")

    assert webhook_session.posts[0]["json"] == {"content": "subject", "allowed_mentions": {"parse": []}}


# Verifies every delivery pins the deadline, the TLS setting and the redirect policy the tool chose
def test_every_delivery_pins_its_deadline_tls_and_redirect_policy(discord, webhook_session, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "VERIFY_SSL", True)
    webhook_session.responses.append(FakeWebhookResponse(204))

    discord.send_webhook("subject", "body", "status")

    post = webhook_session.posts[0]
    assert post["timeout"] == discord.WEBHOOK_TIMEOUT_SECONDS
    assert post["verify"] is True
    assert post["allow_redirects"] is False


# Verifies a redirect is never followed, so a hijacked destination cannot forward the private payload elsewhere
def test_a_redirect_is_reported_rather_than_followed(discord, webhook_session, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(302, headers={"Location": "https://elsewhere.test/collect"}))

    assert discord.send_webhook("subject", "body", "status") == 1
    assert "HTTP 302" in capsys.readouterr().out


# Verifies an alert whose type is switched off is not delivered unless the caller forces it
def test_an_alert_type_that_is_off_is_not_delivered(discord, webhook_session, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "WEBHOOK_STATUS_NOTIFICATION", False)

    assert discord.send_webhook("subject", "body", "status") == 1
    assert webhook_session.posts == []

    webhook_session.responses.append(FakeWebhookResponse(204))
    assert discord.send_webhook("subject", "body", "status", force=True) == 0


@pytest.mark.parametrize("setting,value,expected", [
    ("WEBHOOK_URL", "not-a-url", "WEBHOOK_URL must contain a complete HTTPS link"),
    ("WEBHOOK_PROVIDER", "slack", "WEBHOOK_PROVIDER must be discord or ntfy"),
    ("WEBHOOK_HEADERS", {"Bad Name": "a"}, "WEBHOOK_HEADERS contains an invalid HTTP header name"),
    ("WEBHOOK_AVATAR_URL", "http://example.test/a.png", "WEBHOOK_AVATAR_URL must contain a complete HTTPS link"),
])
# Verifies an unusable setting stops the delivery before a request leaves the machine
def test_an_unusable_setting_stops_the_delivery_before_the_request(discord, webhook_session, monkeypatch, capsys, setting, value, expected):
    monkeypatch.setattr(discord, setting, value)

    assert discord.send_webhook("subject", "body", "status", force=True) == 1
    assert webhook_session.posts == []
    assert expected in capsys.readouterr().out


# Verifies unusable ntfy metadata stops the delivery before a request leaves the machine
def test_unusable_ntfy_metadata_stops_the_delivery(ntfy, webhook_session, capsys):
    assert ntfy.send_webhook("subject", "body", "status", ntfy_priority=9, force=True) == 1
    assert webhook_session.posts == []
    assert "ntfy priority" in capsys.readouterr().out


# Verifies a refusal the service will not change its mind about is reported without a second attempt
def test_a_permanent_refusal_is_not_retried(discord, webhook_session, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(404))
    sleeper = RecordingSleeper()

    assert discord.send_webhook("subject", "body", "status", sleeper=sleeper) == 1
    assert len(webhook_session.posts) == 1
    assert sleeper.delays == []
    assert "The webhook service returned HTTP 404" in capsys.readouterr().out


# Verifies a server failure is retried once and then reported, so a delivery cannot loop
def test_a_server_failure_is_retried_once_then_reported(discord, webhook_session, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.extend([FakeWebhookResponse(500), FakeWebhookResponse(500)])
    sleeper = RecordingSleeper()

    assert discord.send_webhook("subject", "body", "status", sleeper=sleeper) == 1
    assert len(webhook_session.posts) == discord.WEBHOOK_MAX_ATTEMPTS
    assert sleeper.delays == [discord.WEBHOOK_FALLBACK_RETRY_SECONDS]
    assert "The webhook service returned HTTP 500" in capsys.readouterr().out


# Verifies a delivered alert is traced with the provider and the title, never with the private destination
def test_a_delivered_alert_is_traced_with_its_provider(discord, webhook_session, monkeypatch, capsys):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "VERBOSE_MODE", True)
    webhook_session.responses.append(FakeWebhookResponse(204))

    assert discord.send_webhook("LoL user is in game now", "body", "status", sleeper=RecordingSleeper()) == 0

    printed = capsys.readouterr().out
    assert "* Webhook sent through Discord" in printed
    assert DISCORD_URL not in printed


# Verifies DELIVERY_CONFIRMATIONS drops the delivery line without turning the rest of verbose mode off
def test_delivery_confirmations_can_be_turned_off(discord, webhook_session, monkeypatch, capsys):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "VERBOSE_MODE", True)
    monkeypatch.setattr(discord, "DELIVERY_CONFIRMATIONS", False)
    webhook_session.responses.append(FakeWebhookResponse(204))

    assert discord.send_webhook("LoL user is in game now", "body", "status", sleeper=RecordingSleeper()) == 0

    assert "Webhook sent through" not in capsys.readouterr().out


# Verifies a retried delivery that succeeds reports success rather than the failure that preceded it
def test_a_retried_delivery_that_succeeds_reports_success(discord, webhook_session):
    from conftest import FakeWebhookResponse
    webhook_session.responses.extend([FakeWebhookResponse(503), FakeWebhookResponse(204)])

    assert discord.send_webhook("subject", "body", "status", sleeper=RecordingSleeper()) == 0
    assert len(webhook_session.posts) == 2


# Verifies a rate-limited delivery waits the delay the service asked for before its second attempt
def test_a_rate_limited_delivery_waits_the_delay_the_service_asked_for(discord, webhook_session):
    from conftest import FakeWebhookResponse
    webhook_session.responses.extend([FakeWebhookResponse(429, headers={"Retry-After": "3"}), FakeWebhookResponse(204)])
    sleeper = RecordingSleeper()

    assert discord.send_webhook("subject", "body", "status", sleeper=sleeper) == 0
    assert sleeper.delays == [3.0]


# Verifies a service the tool cannot reach is retried once and then reported without a stack trace
def test_an_unreachable_service_is_retried_once_then_reported(discord, webhook_session, capsys):
    webhook_session.responses.extend([req.exceptions.ConnectionError("connection refused"), req.exceptions.ConnectionError("connection refused")])
    sleeper = RecordingSleeper()

    assert discord.send_webhook("subject", "body", "status", sleeper=sleeper) == 1
    assert sleeper.delays == [discord.WEBHOOK_FALLBACK_RETRY_SECONDS]
    assert "The webhook service could not be reached" in capsys.readouterr().out


# Verifies a failure never prints the private destination, the token inside it or the response body
def test_a_failure_never_prints_the_private_destination(discord, webhook_session, capsys, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "NTFY_ACCESS_TOKEN", "tk_secret_token_value")
    webhook_session.responses.append(FakeWebhookResponse(403, payload={"message": "invalid webhook token private-token-value"}))

    discord.send_webhook("subject", "body", "status")

    output = capsys.readouterr().out
    assert "private-token-value" not in output
    assert "tk_secret_token_value" not in output
    assert DISCORD_URL not in output


# Verifies a refused delivery carries the fix and the guide, so no delivery path reports without saying what to do
def test_a_refused_delivery_carries_the_shared_error_block(discord, webhook_session, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(404))

    assert discord.send_webhook("subject", "body", "status", sleeper=lambda seconds: None) == 1

    output = capsys.readouterr().out
    assert "* Error: The webhook service returned HTTP 404" in output
    assert "To fix: " in output
    assert f"Guide: {discord.WEBHOOK_GUIDE_URL}" in output


# Verifies an unreachable service carries the same block, so the two failure kinds read alike
def test_an_unreachable_service_carries_the_shared_error_block(discord, webhook_session, capsys):
    webhook_session.responses.extend([req.exceptions.ConnectionError("connection refused")] * 2)

    assert discord.send_webhook("subject", "body", "status", sleeper=lambda seconds: None) == 1

    output = capsys.readouterr().out
    assert "* Error: The webhook service could not be reached" in output
    assert "To fix: " in output
    assert f"Guide: {discord.WEBHOOK_GUIDE_URL}" in output


# Verifies an unusable webhook setting is refused with the same block the delivery failures print
def test_an_unusable_webhook_setting_carries_the_shared_error_block(discord, monkeypatch, capsys):
    monkeypatch.setattr(discord, "WEBHOOK_PROVIDER", "carrier pigeon")

    assert discord.send_webhook("subject", "body", "status") == 1

    output = capsys.readouterr().out
    assert "* Error: WEBHOOK_PROVIDER must be discord or ntfy" in output
    assert f"Guide: {discord.WEBHOOK_GUIDE_URL}" in output


# Verifies a message built around the destination is redacted at the printer, since not every caller sanitizes first
def test_a_webhook_error_is_redacted_at_the_printer(discord, capsys):
    discord.print_webhook_error(f"the service rejected {DISCORD_URL}")

    output = capsys.readouterr().out
    assert DISCORD_URL not in output
    assert "<redacted>" in output


# Verifies the destination is checked again at the request itself, since a reload can replace it mid-delivery
def test_the_destination_is_checked_again_at_the_request(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_URL", "not-a-url")

    with pytest.raises(req.exceptions.InvalidURL):
        discord.post_webhook_request(json={})


# ---------------------------------------------------------------------------
# The two channels together
# ---------------------------------------------------------------------------


# Verifies each enabled channel receives the same alert, and the return value reports delivery rather than the attempt
def test_each_enabled_channel_receives_the_alert(discord, webhook_session, smtp_double, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "STATUS_NOTIFICATION", True)
    webhook_session.responses.append(FakeWebhookResponse(204))

    email_delivered, webhook_delivered = discord.send_notification_channels("status", "subject", "body", email_enabled=True)

    assert (email_delivered, webhook_delivered) == (True, True)
    assert smtp_double.last.sent is not None
    assert len(webhook_session.posts) == 1


# Verifies a channel that failed reports no delivery, so the caller can retry it while leaving the other alone
def test_a_failed_channel_reports_no_delivery(discord, webhook_session, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "send_email", lambda *args, **kwargs: 1)
    webhook_session.responses.append(FakeWebhookResponse(500))
    webhook_session.responses.append(FakeWebhookResponse(500))

    email_delivered, webhook_delivered = discord.send_notification_channels("status", "subject", "body", email_enabled=True, webhook_enabled=True)

    assert (email_delivered, webhook_delivered) == (False, False)


# Verifies a channel the caller switched off is not contacted at all
def test_a_channel_the_caller_switched_off_is_not_contacted(discord, webhook_session, sent_emails):
    email_delivered, webhook_delivered = discord.send_notification_channels("status", "subject", "body", email_enabled=False, webhook_enabled=False)

    assert (email_delivered, webhook_delivered) == (False, False)
    assert sent_emails == []
    assert webhook_session.posts == []


# Verifies the configured alert settings decide the webhook channel when the caller does not say
def test_the_configured_settings_decide_the_channel_when_the_caller_does_not_say(discord, webhook_session, monkeypatch):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "WEBHOOK_STATUS_NOTIFICATION", False)

    assert discord.send_notification_channels("status", "subject", "body")[1] is False
    assert webhook_session.posts == []

    monkeypatch.setattr(discord, "WEBHOOK_STATUS_NOTIFICATION", True)
    webhook_session.responses.append(FakeWebhookResponse(204))
    assert discord.send_notification_channels("status", "subject", "body")[1] is True


# Verifies both channel names reach the screen, since a run with two channels has to say which one it used
def test_both_channel_names_reach_the_screen(discord, webhook_session, sent_emails, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(204))

    discord.send_notification_channels("status", "subject", "body", email_enabled=True, webhook_enabled=True)

    output = capsys.readouterr().out
    assert "Sending email notification to alerts@example.test" in output
    assert "Sending webhook notification via Discord" in output


# Verifies the send line names the service in every mode, since a run with the delivery confirmations off has no other clue
@pytest.mark.parametrize("provider,expected", [("discord", "Discord"), ("ntfy", "ntfy")])
def test_the_webhook_send_line_names_the_provider(discord, webhook_session, monkeypatch, capsys, provider, expected):
    from conftest import FakeWebhookResponse
    monkeypatch.setattr(discord, "WEBHOOK_PROVIDER", provider)
    monkeypatch.setattr(discord, "DELIVERY_CONFIRMATIONS", False)
    webhook_session.responses.append(FakeWebhookResponse(204))

    discord.send_notification_channels("status", "subject", "body", webhook_enabled=True)

    assert f"Sending webhook notification via {expected}" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


# Builds the parsed arguments the override step reads, with every webhook flag left unset
class WebhookArgs:
    def __init__(self, **overrides):
        self.webhook_enabled = None
        self.webhook_url = None
        self.webhook_provider = None
        self.webhook_status = None
        self.webhook_errors = None
        self.__dict__.update(overrides)


# Fails the run the way argparse does, so a rejected flag is not mistaken for an accepted one
class RecordingParser:
    # Raises the message argparse would print, rather than exiting the test process
    def error(self, message):
        raise ValueError(message)


# Verifies a destination passed on the command line switches the channel on, since nobody passes one to leave it off
def test_a_destination_on_the_command_line_switches_the_channel_on(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", False)

    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_url=NTFY_URL, webhook_provider="ntfy"), RecordingParser())

    assert lm_module.WEBHOOK_URL == NTFY_URL
    assert lm_module.WEBHOOK_ENABLED is True


# Verifies a destination the tool cannot use stops the run at the flag rather than at the first alert
def test_an_unusable_destination_on_the_command_line_stops_the_run(lm_module):
    with pytest.raises(ValueError, match="complete HTTPS link"):
        lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_url="http://ntfy.sh/topic"), RecordingParser())


# Verifies each alert flag switches its own alert on and switches the channel on with it
def test_each_alert_flag_switches_the_channel_on(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", False)
    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_status=True, webhook_provider="ntfy"), RecordingParser())
    assert (lm_module.WEBHOOK_ENABLED, lm_module.WEBHOOK_STATUS_NOTIFICATION) == (True, True)

    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", False)
    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_errors=True, webhook_provider="ntfy"), RecordingParser())
    assert (lm_module.WEBHOOK_ENABLED, lm_module.WEBHOOK_ERROR_NOTIFICATION) == (True, True)


# Verifies turning the error alert off leaves the channel as it was rather than switching it on
def test_turning_the_error_alert_off_does_not_switch_the_channel_on(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", False)

    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_errors=False, webhook_provider="ntfy"), RecordingParser())

    assert lm_module.WEBHOOK_ENABLED is False
    assert lm_module.WEBHOOK_ERROR_NOTIFICATION is False


# Verifies the master flag wins over a destination that would otherwise switch the channel on
def test_the_master_flag_wins_over_a_destination(lm_module):
    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_url=NTFY_URL, webhook_enabled=False, webhook_provider="ntfy"), RecordingParser())

    assert lm_module.WEBHOOK_ENABLED is False


# Verifies a provider the destination contradicts is corrected and the correction is said out loud
def test_a_provider_the_destination_contradicts_is_corrected(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(lm_module, "CONFIGURED_SETTING_NAMES", {"WEBHOOK_PROVIDER"})

    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_url=NTFY_URL), RecordingParser())

    assert lm_module.WEBHOOK_PROVIDER == "ntfy"
    assert "Using ntfy" in capsys.readouterr().out


# Verifies an explicitly chosen provider is left alone, since the flag is the operator saying what they meant
def test_an_explicitly_chosen_provider_is_left_alone(lm_module, monkeypatch, capsys):
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", "discord")

    lm_module.apply_webhook_cli_overrides(WebhookArgs(webhook_url=NTFY_URL, webhook_provider="discord"), RecordingParser())

    assert lm_module.WEBHOOK_PROVIDER == "discord"
    assert "Using" not in capsys.readouterr().out


# Verifies a reloaded destination that belongs to the other service moves the provider with it
def test_a_reloaded_destination_moves_the_provider_with_it(discord, monkeypatch, tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text(f'WEBHOOK_URL="{NTFY_URL}"\n', encoding="utf-8")
    monkeypatch.setattr(discord, "DOTENV_FILE", str(env_file))
    monkeypatch.setattr(discord, "EXPORTED_SECRET_KEYS", frozenset(), raising=False)

    discord.reload_secrets_signal_handler(1, None)

    assert discord.WEBHOOK_URL == NTFY_URL
    assert discord.WEBHOOK_PROVIDER == "ntfy"
    assert "Updated webhook provider to ntfy" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The doctor rows
# ---------------------------------------------------------------------------


# Returns the single Notifications row the webhook check produced
def webhook_row(lm_module, report=None):
    checks = lm_module.doctor_check_webhook_notifications(report or lm_module.DoctorReport())
    assert len(checks) == 1 and checks[0].section == "Notifications"
    return checks[0]


# Verifies a run that never set webhooks up says so without contacting a destination
def test_webhooks_that_were_never_set_up_are_reported_as_disabled(lm_module, monkeypatch, webhook_session):
    monkeypatch.setattr(lm_module, "WEBHOOK_ERROR_NOTIFICATION", True)

    check = webhook_row(lm_module)

    assert check.status == "PASS"
    assert check.label == "Webhook alerts are disabled"
    assert webhook_session.posts == []


# Verifies alert types selected while the channel is off is a warning rather than a silently ignored setting
def test_alert_types_selected_while_the_channel_is_off_warn(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)

    check = webhook_row(lm_module)

    assert check.status == "WARN"
    assert check.detail == "Nothing would ever be delivered"
    assert "Set WEBHOOK_ENABLED to True" in check.advice.fix


# Verifies the shipped error alert alone does not read as the operator switching webhooks on
def test_the_shipped_error_alert_alone_does_not_read_as_switched_on(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(lm_module, "WEBHOOK_ERROR_NOTIFICATION", True)

    assert webhook_row(lm_module).status == "PASS"


@pytest.mark.parametrize("setting,value", [("WEBHOOK_PROVIDER", "slack"), ("WEBHOOK_URL", "not-a-url"), ("WEBHOOK_HEADERS", {"Bad Name": "a"}), ("WEBHOOK_TRANSFORMS", [("title", "not_a_method")])])
# Verifies each unusable webhook setting fails the report rather than waiting for the first alert to be dropped
def test_each_unusable_webhook_setting_fails_the_report(discord, monkeypatch, webhook_session, setting, value):
    monkeypatch.setattr(discord, setting, value)

    check = webhook_row(discord)

    assert check.status == "FAIL"
    assert check.advice.code.startswith("webhook.")
    assert webhook_session.posts == []


# Verifies a channel switched on with no alert types selected warns that nothing would arrive
def test_a_channel_with_no_alert_types_warns(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_STATUS_NOTIFICATION", False)
    monkeypatch.setattr(discord, "WEBHOOK_ERROR_NOTIFICATION", False)

    check = webhook_row(discord)

    assert check.status == "WARN"
    assert check.detail == "Nothing would ever be delivered"


# Verifies the passing row names the service and the alerts without displaying the private destination
def test_the_ready_webhook_row_names_the_service_and_the_alerts(discord, webhook_session):
    report = discord.DoctorReport()

    check = webhook_row(discord, report)

    assert check.status == "PASS"
    assert check.label == f"{discord.WEBHOOK_READY_CHECK_LABEL} for Discord"
    assert check.detail == "Alerts: status changes, errors. The private link was not displayed. No webhook was sent during this passive check"
    assert DISCORD_URL not in check.detail
    assert report.webhook_ready is True
    assert webhook_session.posts == []


# Verifies an unready channel is never offered a delivery test, since there is nothing it could deliver
def test_an_unready_webhook_channel_is_not_offered(discord, monkeypatch):
    monkeypatch.setattr(discord, "WEBHOOK_URL", "not-a-url")
    report = discord.DoctorReport()
    webhook_row(discord, report)

    def refuse(_):
        raise AssertionError("an unready channel must not be offered")

    assert discord.doctor_offer_notification_tests(report, input_func=refuse, interactive=True) == []


# Verifies an approved webhook test sends exactly one real notification and records the pass
def test_an_approved_webhook_test_sends_one_notification(discord, webhook_session, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.append(FakeWebhookResponse(204))
    report = discord.DoctorReport()
    report.webhook_ready = True

    discord.doctor_offer_notification_tests(report, input_func=lambda _: "y", interactive=True)

    capsys.readouterr()
    assert len(webhook_session.posts) == 1
    assert webhook_session.posts[0]["json"]["embeds"][0]["title"] == discord.DOCTOR_TEST_WEBHOOK_TITLE
    assert [check.status for check in report.checks] == ["PASS"]
    assert report.checks[0].label == "Doctor test webhook through Discord delivered"


# Verifies a declined webhook test reaches the report rather than being printed and forgotten
def test_a_declined_webhook_test_is_recorded(discord, webhook_session, capsys):
    report = discord.DoctorReport()
    report.webhook_ready = True

    discord.doctor_offer_notification_tests(report, input_func=lambda _: "n", interactive=True)

    capsys.readouterr()
    assert webhook_session.posts == []
    assert [check.status for check in report.checks] == ["SKIP"]
    assert report.checks[0].label == "Test webhook through Discord was not sent"


# Verifies an approved webhook test that fails counts as a failure, so the verdict matches the run
def test_a_failed_webhook_test_counts_as_a_failure(discord, webhook_session, capsys):
    from conftest import FakeWebhookResponse
    webhook_session.responses.extend([FakeWebhookResponse(500), FakeWebhookResponse(500)])
    report = discord.DoctorReport()
    report.webhook_ready = True

    discord.doctor_offer_notification_tests(report, input_func=lambda _: "y", interactive=True)

    capsys.readouterr()
    assert [check.status for check in report.checks] == ["FAIL"]
    assert report.checks[0].label == "Doctor test webhook through Discord delivery failed"
    assert "1 check(s) failed" in discord.render_doctor_summary(report.checks)


# Verifies both channels are offered separately, so approving one never sends the other
def test_each_ready_channel_is_offered_separately(discord, webhook_session, sent_emails, capsys):
    report = discord.DoctorReport()
    report.email_ready = True
    report.webhook_ready = True
    answers = iter(["y", "n"])

    discord.doctor_offer_notification_tests(report, input_func=lambda _: next(answers), interactive=True)

    capsys.readouterr()
    assert len(sent_emails) == 1
    assert webhook_session.posts == []
    assert [check.status for check in report.checks] == ["PASS", "SKIP"]


# ---------------------------------------------------------------------------
# The shared wording
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("constant,expected", [
    ("TEST_EMAIL_SUBJECT", "LoL Monitor test email"),
    ("TEST_EMAIL_BODY", "This test email was sent by --send-test-email. Your SMTP settings work."),
    ("TEST_WEBHOOK_TITLE", "LoL Monitor test webhook"),
    ("TEST_WEBHOOK_BODY", "This test notification was sent by --send-test-webhook. Your webhook settings work."),
    ("DOCTOR_TEST_EMAIL_SUBJECT", "LoL Monitor doctor test email"),
    ("DOCTOR_TEST_EMAIL_BODY", "This test email was sent after approval in --doctor. Your SMTP delivery settings work."),
    ("DOCTOR_TEST_WEBHOOK_TITLE", "LoL Monitor doctor test webhook"),
    ("DOCTOR_TEST_WEBHOOK_BODY", "This test notification was sent after approval in --doctor. Your webhook delivery settings work."),
])
# Verifies each test message is worded the way every tool in this family words it, so one reader learns them once
def test_each_test_message_matches_the_shared_wording(lm_module, constant, expected):
    assert getattr(lm_module, constant) == expected


# Verifies the startup row reports the webhook channel with the alerts it would deliver
def test_the_startup_row_reports_the_webhook_channel(discord):
    rows = {row.label: row.value for row in discord.build_startup_summary("Faker#KR1 (kr)")}

    assert rows["Notifications (webhook)"] == "On (status changes, errors)"


# Verifies the startup row reports a switched-off channel as off rather than listing settings nothing reads
def test_the_startup_row_reports_a_switched_off_channel(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)

    rows = {row.label: row.value for row in lm_module.build_startup_summary("Faker#KR1 (kr)")}

    assert rows["Notifications (webhook)"] == "Off"


# Verifies a link whose text repeats its destination reaches Discord bare, because a masked link there prints as plain text
def test_self_labeled_links_stay_bare_in_discord_markdown(lm_module):
    profile_url = "https://op.gg/summoners/eune/misiektoja"
    markdown = lm_module.html_body_to_discord_markdown(f"Profile: <a href=\"{profile_url}\">{profile_url}</a><br>")
    assert markdown == f"Profile: {profile_url}"


# Verifies a link with its own text keeps the masked form Discord renders as a hyperlink
def test_labeled_links_keep_the_masked_discord_form(lm_module):
    body_html = "Match: <b><a href=\"https://op.gg/summoners/eune/misiektoja\">misiektoja</a></b><br>"
    assert lm_module.html_body_to_discord_markdown(body_html) == "Match: **[misiektoja](https://op.gg/summoners/eune/misiektoja)**"


# Verifies an image link becomes its alt text or a bare URL instead of an empty masked link
def test_image_links_never_produce_an_empty_discord_label(lm_module):
    with_alt = "<a href=\"https://op.gg/champions/ahri\"><img src=\"https://ddragon.gg/ahri.png\" alt=\"Ahri\"></a>"
    without_alt = "<a href=\"https://op.gg/champions/ahri\"><img src=\"https://ddragon.gg/ahri.png\"></a>"
    assert lm_module.html_body_to_discord_markdown(with_alt) == "[Ahri](https://op.gg/champions/ahri)"
    assert lm_module.html_body_to_discord_markdown(without_alt) == "https://op.gg/champions/ahri"
