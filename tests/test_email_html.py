"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import difflib
import html as html_module
import json
import os
import re
from pathlib import Path

import pytest

from test_monitoring_loop import USER, always_failing, live_match_payload, run_checks, run_loop, script_profile


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Replaces every anchor with its destination, which is what a plain body prints on a bare URL line
def links_as_destinations(line):
    return re.sub(r'(?is)<a\s[^>]*?href="([^"]*)"[^>]*>.*?</a>', r"\1", line)


# Reports whether one HTML line says what its plain counterpart says, whether it links a name or a bare URL
def line_agrees(plain_line, html_line):
    return plain_line in (html_to_text(html_line), html_to_text(links_as_destinations(html_line)))


# Returns what differs between the plain body and the HTML body, empty when their lines and blank lines match
def structural_diff(body, body_html):
    plain_lines = body.split("\n")
    html_lines = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or "")).split("<br>")
    if len(plain_lines) == len(html_lines) and all(line_agrees(*pair) for pair in zip(plain_lines, html_lines, strict=True)):
        return ""
    return "\n".join(difflib.unified_diff(plain_lines, [html_to_text(line) for line in html_lines], fromfile="plain", tofile="html-reduced", lineterm=""))


@pytest.fixture(autouse=True)
# Keeps the CSV history and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
# Redirects the alerts of one run into a list of their own, without delivering any of them
def capture_alerts(lm_module, monkeypatch):

    # Starts collecting the alerts sent from here on and returns the list they land in
    def install():
        captured = []

        def fake_send(notification_type, subject, body, body_html="", **kwargs):
            captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": kwargs.get("webhook_body") or body, "discord": lm_module.html_body_to_discord_markdown(kwargs.get("webhook_body_html") or body_html)})
            return bool(kwargs.get("email_enabled")), bool(kwargs.get("webhook_enabled"))

        monkeypatch.setattr(lm_module, "send_notification_channels", fake_send)
        return captured

    return install


@pytest.fixture
# Every alert a timeline covering a started match, the match summary and the player leaving produces
def match_alerts(lm_module, riot_api, fake_clock, monkeypatch, capture_alerts, capsys):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", {103: "Ahri", 238: "Zed"})
    captured = capture_alerts()
    script_profile(riot_api)
    run_loop(lm_module, riot_api, [{"live": live_match_payload()}, {"live": None}, {"live": None, "match_ids": ["EUN1_2"]}], initial_match_ids=["EUN1_1"])
    capsys.readouterr()
    return captured


@pytest.fixture
# The alert a run whose checks keep failing sends, which every monitor words the same way
def failure_alerts(lm_module, riot_api, fake_clock, monkeypatch, capture_alerts, capsys):
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", True)
    captured = capture_alerts()
    run_checks(lm_module, riot_api, monkeypatch, always_failing, 8)
    capsys.readouterr()
    return captured


@pytest.fixture
# Every alert both runs produce, which is what the structural check and the preview cover
def timeline_alerts(match_alerts, failure_alerts):
    return match_alerts + failure_alerts


# Verifies the monitored player is highlighted in a team roster while teammates are not
def test_monitored_player_is_highlighted(lm_module):
    assert lm_module.format_team_member_html("misiektoja (Ahri)", "misiektoja") == "<b>misiektoja</b> (Ahri)"
    assert lm_module.format_team_member_html("someone else (Zed)", "misiektoja") == "someone else (Zed)"


# Verifies a member listed without a champion still renders
def test_member_without_a_champion_renders(lm_module):
    assert lm_module.format_team_member_html("misiektoja", "misiektoja") == "<b>misiektoja</b>"
    assert lm_module.format_team_member_html("", "misiektoja") == ""


# Verifies a Riot name containing markup is escaped, so a crafted name cannot inject HTML into the email
def test_player_names_are_escaped(lm_module):
    rendered = lm_module.format_team_member_html("<script>alert(1)</script> (Ahri)", "misiektoja")

    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


# Verifies the monitored player's own name is escaped before it is emphasized
def test_the_monitored_name_is_escaped_before_it_is_bolded(lm_module):
    rendered = lm_module.format_team_member_html("<b>me</b>", "<b>me</b>")

    assert rendered == "<b>&lt;b&gt;me&lt;/b&gt;</b>"


# Verifies a champion name containing markup is escaped along with the player name
def test_champion_names_are_escaped(lm_module):
    rendered = lm_module.format_team_member_html("misiektoja (<img src=x>)", "misiektoja")

    assert "<img" not in rendered
    assert "&lt;img src=x&gt;" in rendered


# Verifies the roster becomes HTML with team headers in bold and one line break per entry
def test_team_rosters_render_as_html(lm_module):
    lines = ["Team id 100: ⭐", "- misiektoja (Ahri)", "- teammate (Lux)", "", "Team id 200:", "- rival (Zed)"]

    rendered = lm_module.format_teams_html(lines, "misiektoja")

    assert rendered == ("<b>Team id 100: ⭐</b><br>- <b>misiektoja</b> (Ahri)<br>- teammate (Lux)<br><br><b>Team id 200:</b><br>- rival (Zed)<br>")


# Verifies an empty roster produces nothing rather than an empty HTML block
def test_empty_roster_renders_as_nothing(lm_module):
    assert lm_module.format_teams_html([], "misiektoja") == ""
    assert lm_module.format_banned_champions_html([]) == ""


# Verifies banned champions render with team headers in bold and blank lines as breaks
def test_banned_champions_render_as_html(lm_module):
    lines = ["Team id 100:", "- Lux (pick 1)", "", "Team id 200:", "- Zed (pick 2)"]

    rendered = lm_module.format_banned_champions_html(lines)

    assert rendered == ("<b>Team id 100:</b><br>- Lux (pick 1)<br><br><b>Team id 200:</b><br>- Zed (pick 2)<br>")


# Verifies a ban line containing markup is escaped
def test_ban_lines_are_escaped(lm_module):
    rendered = lm_module.format_banned_champions_html(["- <b>Lux</b> (pick 1)"])

    assert rendered == "- &lt;b&gt;Lux&lt;/b&gt; (pick 1)<br>"


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once(lm_module):
    assert lm_module.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert lm_module.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body(lm_module):
    body_html = f'<html><head></head><body>LoL user <b>{USER}</b> is in game now<br><br>Guide: <a href="https://example.test/a">docs</a></body></html>'

    assert lm_module.html_body_to_discord_markdown(body_html) == f"LoL user **{USER}** is in game now\n\nGuide: [docs](https://example.test/a)"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields(lm_module):
    advice = lm_module.make_recovery_advice("riot.unavailable", "Riot answered the request with HTTP 500", lm_module.recovery_fix_with_guide("Retry later", "https://example.test/guide"), True)

    rendered = lm_module.recovery_alert_body_html(advice, 60, failed_checks=2, failing_since=1767226800)

    assert rendered.startswith("<b>Riot answered the request with HTTP 500</b><br><br>")
    assert 'Guide: <a href="https://example.test/guide">' in rendered
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered


# Verifies the timeline reaches both alert types, so the structural check is not silently narrow
def test_the_timeline_covers_the_match_and_failure_alerts(timeline_alerts):
    assert {alert["type"] for alert in timeline_alerts} == {"status", "error"}


# Verifies the match alerts cover the start, the summary and the player leaving
def test_the_match_alerts_cover_the_whole_session(match_alerts):
    subjects = [alert["subject"] for alert in match_alerts]

    assert any(subject.startswith(f"LoL user {USER} is in game now") for subject in subjects)
    assert any(subject.startswith(f"LoL user {USER} match summary") for subject in subjects)
    assert f"LoL user {USER} stopped playing" in subjects


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(timeline_alerts):
    assert [alert["subject"] for alert in timeline_alerts if not alert["body_html"]] == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(timeline_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in timeline_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(timeline_alerts):
    for alert in timeline_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Verifies the Discord body keeps the wording the ntfy body carries once its markers are removed
def test_discord_bodies_keep_the_plain_wording(timeline_alerts):
    for alert in timeline_alerts:
        stripped = re.sub(r"\[([^\]]*)\]\((?:[^)]*)\)", r"\1", alert["discord"]).replace("**", "").replace("*", "")

        assert stripped == alert["webhook_body"].strip()


# Verifies the monitored player is the bold subject of every alert that names them
def test_alerts_bold_the_player_they_name(match_alerts):
    for alert in match_alerts:
        assert f"<b>{USER}</b>" in alert["body_html"]


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(timeline_alerts):
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(timeline_alerts, indent=2), encoding="utf-8")
