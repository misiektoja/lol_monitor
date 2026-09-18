"""Tests for the HTML notification body, including escaping of names taken from Riot."""


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
