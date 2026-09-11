"""Property-based tests for the answer normalizers and the dotenv values they end up as."""

from pathlib import Path

import pytest
from dotenv import dotenv_values
from hypothesis import given
from hypothesis import strategies as st

import lol_monitor as monitor

# The characters a Riot game name and tag line are made of, which is what the normalizer has to preserve
RIOT_NAME_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-."
TAG_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

riot_names = st.text(alphabet=RIOT_NAME_ALPHABET, min_size=1, max_size=16).map(str.strip).filter(bool)
tag_lines = st.text(alphabet=TAG_ALPHABET, min_size=1, max_size=5)


# Verifies the surrounding whitespace a user pastes never changes which account is monitored
@given(name=riot_names, tag=tag_lines, lead=st.sampled_from(["", " ", "\t", "  "]), trail=st.sampled_from(["", " ", "\t", "\n"]))
def test_every_pasted_form_reads_as_the_same_riot_id(name, tag, lead, trail):
    assert monitor.normalize_riot_id(f"{lead}{name}#{tag}{trail}") == f"{name}#{tag}"


# Verifies a Riot ID missing either half is refused rather than monitored as a partial target
@given(half=riot_names, separator=st.sampled_from(["", "#"]))
def test_a_riot_id_missing_a_half_is_refused(half, separator):
    with pytest.raises(ValueError):
        monitor.normalize_riot_id(f"{separator}{half}" if separator else half)


# Verifies normalizing an already normalized Riot ID changes nothing, since it is applied at more than one boundary
@given(name=riot_names, tag=tag_lines)
def test_normalizing_a_riot_id_twice_changes_nothing(name, tag):
    once = monitor.normalize_riot_id(f"{name}#{tag}")

    assert monitor.normalize_riot_id(once) == once


# Verifies a region reads the same however it was typed, since the routing table is keyed by one form
@given(region=st.sampled_from(sorted(monitor.REGION_TO_CONTINENT)), upper=st.booleans(), padding=st.sampled_from(["", " ", "  "]))
def test_a_region_resolves_the_same_however_it_was_typed(region, upper, padding):
    typed = f"{padding}{region.upper() if upper else region}{padding}"

    assert monitor.normalize_region(typed) == region
    assert monitor.region_continent(monitor.normalize_region(typed)) == monitor.REGION_TO_CONTINENT[region]


# Verifies a duration carries the unit it was typed with rather than being read as bare seconds
@given(amount=st.integers(min_value=1, max_value=999), unit=st.sampled_from(["s", "m", "h", "d"]))
def test_a_duration_carries_the_unit_it_was_typed_with(amount, unit):
    expected = amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]

    assert monitor.parse_duration_input(f"{amount}{unit}") == expected
    assert monitor.parse_duration_input(f"{amount} {unit}") == expected


# Verifies a duration written in parts adds them up, which is the form a user copies out of the help text
@given(hours=st.integers(min_value=0, max_value=48), minutes=st.integers(min_value=0, max_value=59), seconds=st.integers(min_value=0, max_value=59))
def test_a_duration_written_in_parts_adds_them_up(hours, minutes, seconds):
    total = hours * 3600 + minutes * 60 + seconds
    written = " ".join(part for part in (f"{hours}h" if hours else "", f"{minutes}m" if minutes else "", f"{seconds}s" if seconds else "") if part)

    assert monitor.parse_duration_input(written) == (total or None)


# Verifies a parsed duration is a positive whole number of seconds or nothing at all, never a float or a zero
@given(value=st.one_of(st.text(max_size=12), st.integers(min_value=-999, max_value=999), st.floats(allow_nan=False, allow_infinity=False, min_value=-999, max_value=999)))
def test_a_duration_is_a_positive_whole_number_of_seconds_or_nothing(value):
    parsed = monitor.parse_duration_input(value)

    assert parsed is None or (isinstance(parsed, int) and parsed > 0)


# Verifies a unit the tool does not know is refused rather than silently read as seconds
@given(amount=st.integers(min_value=1, max_value=999), unit=st.text(alphabet="abcdefgijklnopqrtuvwxyz", min_size=1, max_size=4))
def test_a_unit_the_tool_does_not_know_is_refused(amount, unit):
    known = {"s", "sec", "secs", "second", "seconds", "m", "min", "mins", "minute", "minutes", "h", "hr", "hrs", "hour", "hours", "d", "day", "days"}

    if unit.casefold() not in known:
        assert monitor.parse_duration_input(f"{amount}{unit}") is None


# Verifies a CSV path answer ends up with exactly one extension, whether or not the user typed one
@given(name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=12), extension=st.sampled_from(["", ".csv", ".txt"]))
def test_a_csv_path_answer_ends_up_with_one_extension(name, extension):
    normalized = monitor._wizard_normalize_csv_path(f"{name}{extension}")

    assert Path(normalized).suffix == (extension or ".csv")
    assert Path(normalized).stem == name


# Verifies a secret survives the dotenv file unchanged, whatever punctuation it carries
@given(value=st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=40))
def test_a_secret_survives_the_dotenv_file(tmp_path_factory, value):
    env_file = tmp_path_factory.mktemp("dotenv") / ".env"
    monitor.update_dotenv_file(str(env_file), {"RIOT_API_KEY": value})

    assert dotenv_values(str(env_file))["RIOT_API_KEY"] == value
