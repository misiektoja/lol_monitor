"""Tests that a config file is read as data and never executed, including every released template."""

import re
from pathlib import Path

import pytest

import lol_monitor as monitor

# One config template per released shape, extracted from the tag that shipped it. A user upgrading from any
# published version arrives with one of these on disk, so the current parser has to read all of them
RELEASED_TEMPLATES = sorted((Path(__file__).resolve().parent / "data" / "config_templates").glob("*.conf"), key=lambda path: [int(part) for part in path.stem.lstrip("v").split(".")])


HOSTILE_CONTENT = (
    "import os\n"
    "os.environ['LOL_CONFIG_EXEC_PROBE'] = 'yes'\n",
    "__import__('os').system('touch pwned')\n",
    "CHECK_INTERNET_TIMEOUT = __import__('os').getpid()\n",
    "def helper():\n    return 1\n",
    "for index in range(3):\n    pass\n",
)


# Returns a setting name the built-in configuration template actually defines
def first_allowed_setting():
    return sorted(monitor._config_allowed_names())[0]


@pytest.mark.parametrize("content", HOSTILE_CONTENT)
# Verifies executable content is refused without running, so a config in the working directory cannot run code
def test_executable_config_content_is_refused_without_running(tmp_path, monkeypatch, content):
    monkeypatch.delenv("LOL_CONFIG_EXEC_PROBE", raising=False)
    config = tmp_path / "hostile.conf"
    config.write_text(content, encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is False
    assert namespace == {}

    import os

    assert os.environ.get("LOL_CONFIG_EXEC_PROBE") is None
    assert not (tmp_path / "pwned").exists()


# Verifies a plain literal assignment still reaches the namespace
def test_literal_settings_are_applied(tmp_path):
    setting = first_allowed_setting()
    config = tmp_path / "good.conf"
    config.write_text(f"{setting} = 123\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace[setting] == 123


# Verifies one setting may reuse another, which the built-in template relies on
def test_a_setting_may_reference_another_setting(tmp_path):
    allowed = sorted(monitor._config_allowed_names())
    source, target = allowed[0], allowed[1]
    config = tmp_path / "reference.conf"
    config.write_text(f'{source} = "shared"\n{target} = {source}\n', encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert namespace[target] == "shared"


# Verifies a setting this version does not define is named instead of silently landing in the namespace
def test_unknown_setting_is_rejected(tmp_path):
    config = tmp_path / "unknown.conf"
    config.write_text("NOT_A_REAL_SETTING = 1\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is False
    assert "NOT_A_REAL_SETTING" not in namespace


# Verifies a rejected file leaves the namespace untouched rather than applying the lines before the bad one
def test_a_rejected_config_applies_nothing(tmp_path):
    setting = first_allowed_setting()
    config = tmp_path / "partial.conf"
    config.write_text(f"{setting} = 5\nimport os\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is False
    assert namespace == {}


# Verifies the built-in template and the config the tool generates both survive the parser
def test_generated_configuration_round_trips():
    monitor.validate_config_content(monitor.CONFIG_BLOCK, "<built-in>")


# Verifies a file that is not valid UTF-8 is reported rather than raising
def test_invalid_encoding_is_reported(tmp_path):
    config = tmp_path / "binary.conf"
    config.write_bytes(b"\xff\xfe\x00bad\n")

    assert monitor.load_config_file(config, namespace={}, report_errors=False) is False


# Verifies a config written by an older version still loads when it carries a retired setting
def test_retired_setting_is_ignored_instead_of_rejected(tmp_path):
    retired = sorted(monitor.RETIRED_CONFIG_SETTINGS)[0]
    config = tmp_path / "retired.conf"
    config.write_text(f"{retired} = 30\n", encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True
    assert retired not in namespace


# Verifies the suite still carries a template per released config shape, so a replay cannot quietly cover nothing
def test_every_released_config_shape_is_replayed():
    assert [path.name for path in RELEASED_TEMPLATES] == ["v1.6.conf", "v1.7.conf", "v1.7.2.conf", "v1.8.1.conf"]


@pytest.mark.parametrize("template", RELEASED_TEMPLATES, ids=lambda path: path.stem)
# Verifies a config file written by any released version still loads, so an upgrade does not start with an error
def test_a_released_config_template_still_loads(template, tmp_path):
    config = tmp_path / "upgraded.conf"
    config.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    namespace = {}

    assert monitor.load_config_file(config, namespace=namespace, report_errors=False) is True


@pytest.mark.parametrize("template", RELEASED_TEMPLATES, ids=lambda path: path.stem)
# Verifies every setting a released template assigns still reaches the run, apart from the ones deliberately retired
def test_every_setting_a_released_template_assigns_still_arrives(template, tmp_path):
    config = tmp_path / "upgraded.conf"
    content = template.read_text(encoding="utf-8")
    config.write_text(content, encoding="utf-8")
    assigned = {match.group(1) for match in re.finditer(r"^([A-Z][A-Z0-9_]*)\s*=", content, re.M)}
    namespace = {}

    monitor.load_config_file(config, namespace=namespace, report_errors=False)

    missing = assigned - set(namespace) - monitor.RETIRED_CONFIG_SETTINGS
    assert not missing, f"{template.name} sets values the current parser drops: {sorted(missing)}"


# The part of the configuration template every sibling monitor shares, in the order they all use
SHARED_SETTING_ORDER = ("WEBHOOK_HEADERS", "NTFY_ACCESS_TOKEN", "WEBHOOK_TEMPLATE", "WEBHOOK_TRANSFORMS", "DISABLE_LOGGING", "ASCII_LOG_SEPARATORS", "TRUNCATE_CHARS", "CLEAR_SCREEN", "COLORED_OUTPUT", "COLOR_THEME", "VERBOSE_MODE", "DEBUG_MODE", "DELIVERY_CONFIRMATIONS")


# Returns every setting the built-in template declares, in template order, including the commented theme block
def template_setting_order(module):
    order = []
    for line in module.CONFIG_BLOCK.split("\n"):
        match = re.match(r"^([A-Z][A-Z0-9_]*)\s*[:=]", line) or re.match(r"^# ([A-Z][A-Z0-9_]*)\s*=", line)
        if match and match.group(1) not in order:
            order.append(match.group(1))
    return order


# Verifies the template keeps the order shared with the sibling monitors, so one tool's config reads like the next
def test_the_template_keeps_the_shared_setting_order():
    order = template_setting_order(monitor)

    assert set(SHARED_SETTING_ORDER) <= set(order), f"the template no longer declares {sorted(set(SHARED_SETTING_ORDER) - set(order))}"
    assert [name for name in order if name in SHARED_SETTING_ORDER] == list(SHARED_SETTING_ORDER)


# Verifies the linter defaults below the template repeat it in the same order, so a setting cannot drift or be filed twice
def test_the_linter_defaults_follow_the_template_order():
    source = Path(monitor.__file__).read_text(encoding="utf-8").split("\n")
    start = next(index for index, line in enumerate(source) if line.startswith("# Do not change values below")) + 1
    end = next(index for index, line in enumerate(source) if line.startswith("exec(CONFIG_BLOCK"))
    order = template_setting_order(monitor)
    mirrored = [match.group(1) for match in (re.match(r"^([A-Z][A-Z0-9_]*)\s*[:=]", line) for line in source[start:end]) if match and match.group(1) in set(order)]

    assert len(mirrored) == len(set(mirrored)), "a setting is repeated in the linter defaults"
    assert mirrored == [name for name in order if name in set(mirrored)]
