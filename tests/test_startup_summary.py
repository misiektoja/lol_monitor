"""Tests for the startup summary: the shared row order, the two views and what each one is allowed to show."""

import ast
import inspect
import io
import re

import pytest

RIOT_ID = "misiektoja#EUNE"
REGION = "eun1"

# The rows every tool in this family prints, in the order section 15.18 fixes. A tool's own rows are filtered out
SHARED_ROW_ORDER = ("Target", "Polling intervals", "Notifications (email)", "Output", "Output logging", "Config", "Dotenv", "Liveness output", "CSV output", "Install method", "Secrets from dotenv", "Secrets from environment", "Secrets from config file", "Secrets from command line", "TLS verification", "ASCII log separators", "Verbose mode", "Debug mode", "More details")

# Where every value starts, which is what makes the column line up across tools
VALUE_COLUMN = 32


@pytest.fixture
# Builds the rows a run with a target, a config file, a dotenv file and a log file would print
def rows(lm_module):
    return lm_module.build_startup_summary(f"{RIOT_ID} ({REGION})", "lol_monitor.conf", ".env", "lol_monitor_misiektoja.log")


# Renders one view of the summary into a plain string, the way a run without a log file would
def render(lm_module, rows, show_full=False):
    stream = io.StringIO()
    lm_module.emit_startup_summary(rows, show_full=show_full, stream=stream)
    return stream.getvalue()


# Verifies the shared rows appear in the order every sibling uses, since the screen is only readable across tools while they match
def test_the_shared_summary_rows_match_the_sibling_tools(rows):
    assert [row.label for row in rows if row.label in SHARED_ROW_ORDER] == list(SHARED_ROW_ORDER)


# Verifies no label runs into its own value, which is what a label wider than the column does
def test_no_label_is_wider_than_the_column(rows):
    assert max(len(row.label) for row in rows) <= 28


# Verifies every label declared anywhere in the module fits, including one only a branch would build
def test_every_declared_label_fits_the_column(lm_module):
    tree = ast.parse(inspect.getsource(lm_module))
    labels = [call.args[0] for call in ast.walk(tree) if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "StartupSummaryRow" and call.args]

    assert labels, "the sweep found no summary rows"
    for label in labels:
        assert isinstance(label, ast.Constant) and isinstance(label.value, str), f"line {label.lineno}: the label is not a string literal"
        assert len(label.value) <= 28, f"line {label.lineno}: '{label.value}' is {len(label.value)} characters"


# Verifies every value starts in the same column, which tabs cannot do because they depend on the terminal
def test_every_value_starts_in_the_same_column(lm_module, rows):
    starts = {match.start(1) for match in (re.match(r"\* [^:]+: +(\S)", lm_module.format_startup_summary_row(row)) for row in rows) if match}

    assert starts == {VALUE_COLUMN}


# Verifies the short view is the one a default run gets and that it stays short
def test_the_concise_view_shows_only_the_rows_that_opted_in(lm_module, rows):
    shown = {line.split(":", 1)[0][2:].strip() for line in render(lm_module, rows).splitlines() if line.startswith("* ")}

    assert shown == {row.label for row in rows if row.concise}
    assert "Secrets from dotenv" not in shown


# Verifies asking for more detail shows every row that belongs to the full view and drops the two pointers
def test_the_full_view_shows_every_row_that_belongs_to_it(lm_module, rows):
    shown = {line.split(":", 1)[0][2:].strip() for line in render(lm_module, rows, show_full=True).splitlines() if line.startswith("* ")}

    assert shown == {row.label for row in rows if row.full}
    assert not {"Output", "More details"} & shown


# Verifies only the two pointer rows invert the routing, since a third would be a row the full view silently loses
def test_only_the_two_pointer_rows_are_concise_without_being_full(rows):
    assert [row.label for row in rows if row.concise and not row.full] == ["Output", "More details"]


# Verifies the two halves of one setting stay next to each other rather than reading as unrelated settings
def test_the_output_rows_stay_adjacent(rows):
    labels = [row.label for row in rows]

    assert labels.index("Output logging") - labels.index("Output") == 1


# Verifies the pointer to the two modes is the last row, so nothing can be appended where no view would show it
def test_the_pointer_row_is_last(rows):
    assert rows[-1].label == "More details"


# Verifies the short row names the destination in effect and the full row names the configured state
def test_the_output_rows_report_the_live_destination_and_the_setting(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False)
    enabled = {row.label: row.value for row in lm_module.build_startup_summary(RIOT_ID, None, None, "lol_monitor_misiektoja.log")}
    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", True)
    disabled = {row.label: row.value for row in lm_module.build_startup_summary(RIOT_ID, None, None, None)}

    assert (enabled["Output"], enabled["Output logging"]) == ("lol_monitor_misiektoja.log", "lol_monitor_misiektoja.log")
    assert (disabled["Output"], disabled["Output logging"]) == ("Terminal only (logging disabled)", "Disabled")


# Verifies a feature row joins the short view exactly while the feature is on, so the short view reports what is running
@pytest.mark.parametrize("label,setting,on,off", [
    ("CSV output", "CSV_FILE", "matches.csv", ""),
    ("Liveness output", "LIVENESS_CHECK_INTERVAL", 43200, 0),
    ("Forbidden matches", "INCLUDE_FORBIDDEN_MATCHES", True, False),
])
def test_a_feature_row_is_concise_while_the_feature_is_on(lm_module, monkeypatch, label, setting, on, off):
    monkeypatch.setattr(lm_module, setting, on)
    switched_on = next(row for row in lm_module.build_startup_summary() if row.label == label)
    monkeypatch.setattr(lm_module, setting, off)
    switched_off = next(row for row in lm_module.build_startup_summary() if row.label == label)

    assert (switched_on.concise, switched_off.concise) == (True, False)
    assert switched_off.value == "Disabled" or switched_off.value == "False"


# Verifies the one row that is short while it is off, since a run that stopped checking certificates should say so unasked
def test_tls_verification_is_concise_while_it_is_off(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", True)
    verifying = next(row for row in lm_module.build_startup_summary() if row.label == "TLS verification")
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)
    not_verifying = next(row for row in lm_module.build_startup_summary() if row.label == "TLS verification")

    assert (verifying.concise, not_verifying.concise) == (False, True)
    assert not_verifying.value == "Off, server certificates are not checked"


# Verifies each source has its own row, since one packed row stops lining up as soon as a name is long
def test_each_secret_source_has_its_own_row(rows):
    labels = [row.label for row in rows if row.label.startswith("Secrets from")]

    assert labels == ["Secrets from dotenv", "Secrets from environment", "Secrets from config file", "Secrets from command line"]


# Verifies an empty bucket says so, so the block keeps its shape whatever a run happens to have set
def test_an_empty_secret_bucket_reports_none(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "")
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "")

    values = [row.value for row in lm_module.build_startup_summary() if row.label.startswith("Secrets from")]

    assert values == ["None"] * 4


# Verifies the summary names secrets and never prints one, since it is the block that gets pasted into a bug report
def test_the_summary_never_prints_a_secret_value(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "RIOT_API_KEY", "RGAPI-intraces-0000-0000-0000-000000000000")
    monkeypatch.setattr(lm_module, "SMTP_PASSWORD", "an-app-password")

    rendered = render(lm_module, lm_module.build_startup_summary(RIOT_ID), show_full=True)

    assert "RIOT_API_KEY" in rendered
    assert "RGAPI-intraces-0000-0000-0000-000000000000" not in rendered
    assert "an-app-password" not in rendered


# Verifies a run with no target still prints the row, so the block has the same shape whatever the run was given
def test_a_run_without_a_target_still_reports_the_row(lm_module):
    rows = {row.label: row.value for row in lm_module.build_startup_summary()}

    assert (rows["Target"], rows["Config"], rows["Dotenv"]) == ("None", "None", "None")


# Verifies a config file search that was switched off is reported as such rather than as no file
def test_disabled_config_discovery_is_reported(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "CONFIG_DISCOVERY_DISABLED", True)

    assert next(row.value for row in lm_module.build_startup_summary() if row.label == "Config") == "Discovery disabled"


# Verifies the alert categories are named, since a channel reported as On tells the reader nothing about what it delivers
def test_the_email_row_names_the_categories(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "ERROR_NOTIFICATION", False)
    on = next(row.value for row in lm_module.build_startup_summary() if row.label == "Notifications (email)")
    monkeypatch.setattr(lm_module, "STATUS_NOTIFICATION", False)
    off = next(row.value for row in lm_module.build_startup_summary() if row.label == "Notifications (email)")

    assert (on, off) == ("On (status changes)", "Off")


# Verifies the log keeps every effective setting whatever the terminal showed, which is what makes a log worth attaching
def test_the_log_keeps_the_full_view_while_the_terminal_shows_the_short_one(lm_module, rows):
    class SplitStream:
        def __init__(self):
            self.terminal, self.log = [], []

        def log_only(self, message):
            self.log.append(message)

        def terminal_only(self, message):
            self.terminal.append(message)

        def flush(self):
            return

    stream = SplitStream()
    lm_module.emit_startup_summary(rows, show_full=False, stream=stream)

    assert "".join(stream.terminal).count("* ") == len([row for row in rows if row.concise])
    assert "".join(stream.log).count("* ") == len([row for row in rows if row.full])
    assert "Secrets from dotenv" in "".join(stream.log)


# Verifies a stream with no log file still prints, since a run started with -d has nowhere to keep the full view
def test_a_stream_without_a_log_file_still_prints(lm_module, rows):
    rendered = render(lm_module, rows)

    assert rendered.startswith("* Target:")
    assert rendered.endswith("\n\n")


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after the summary has printed
def monitor_calls(monkeypatch, lm_module, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(lm_module, "DEFAULT_CONFIG_FILENAME", "lol_monitor_test_only.conf")
    monkeypatch.setattr(lm_module, "DOTENV_FILE", "none")
    monkeypatch.setattr(lm_module, "check_internet", lambda *args, **kwargs: True)
    recorded = []

    # Records the arguments the monitoring loop was started with
    async def fake_monitor(riotid, region, csv_file_name):
        recorded.append(riotid)

    monkeypatch.setattr(lm_module, "lol_monitor_user", fake_monitor)
    return recorded


# Verifies a default run gets the short screen and asking for detail gets the long one, which is the whole point of the two views
def test_a_real_run_shows_the_short_screen_unless_detail_is_asked_for(lm_module, monkeypatch, monitor_calls, capsys):
    from test_cli_startup import run_main

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0
    concise = capsys.readouterr().out
    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, "--verbose"]) == 0
    full = capsys.readouterr().out

    assert "* More details:" in concise and "Secrets from dotenv" not in concise
    assert "Secrets from dotenv" in full and "* More details:" not in full


# Verifies either mode on its own opens the full view, since a debug run needs the settings its trace was produced under
@pytest.mark.parametrize("flag", ["--verbose", "--debug"])
def test_either_mode_opens_the_full_view(lm_module, monkeypatch, monitor_calls, capsys, flag):
    from test_cli_startup import run_main

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION, flag]) == 0

    assert "Secrets from dotenv" in capsys.readouterr().out


# Verifies the log file a real run opens keeps the full view even though the terminal only showed the short one
def test_the_log_file_of_a_real_run_keeps_the_full_view(lm_module, monkeypatch, monitor_calls, tmp_path, capsys):
    from test_cli_startup import run_main

    monkeypatch.setattr(lm_module, "DISABLE_LOGGING", False)
    monkeypatch.setattr(lm_module, "LOL_LOGFILE", str(tmp_path / "lol_monitor"))

    assert run_main(lm_module, monkeypatch, [RIOT_ID, REGION]) == 0

    logged = (tmp_path / "lol_monitor_misiektoja.log").read_text(encoding="utf-8")
    assert "Secrets from dotenv" in logged
    assert "Secrets from dotenv" not in capsys.readouterr().out
    assert "* Output:" not in logged
