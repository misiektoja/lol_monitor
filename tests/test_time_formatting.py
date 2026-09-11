"""Tests for the duration and timestamp helpers used across the match reports."""

from datetime import datetime

import pytest

TS = 1767226800  # Thu 01 Jan 2026, 00:20:00 UTC


@pytest.mark.parametrize("seconds,expected", [
    (0, "0 seconds"),
    (-5, "0 seconds"),
    (1, "1 second"),
    (59, "59 seconds"),
    (60, "1 minute"),
    (90, "1 minute, 30 seconds"),
    (1830, "30 minutes, 30 seconds"),
    (3600, "1 hour"),
    (3661, "1 hour, 1 minute"),
    (86400, "1 day"),
])
# Verifies match durations and polling intervals are rendered in the units a reader expects
def test_durations_are_rendered_in_readable_units(lm_module, seconds, expected):
    assert lm_module.display_time(seconds) == expected


# Verifies granularity limits how many units are printed, which keeps the subject line short
def test_duration_granularity_limits_the_units_shown(lm_module):
    assert lm_module.display_time(90061, granularity=1) == "1 day"
    assert lm_module.display_time(90061, granularity=3) == "1 day, 1 hour, 1 minute"


# Verifies the time since the last match is described from the larger unit down
def test_timespan_between_epoch_timestamps(lm_module):
    assert lm_module.calculate_timespan(TS + 3661, TS) == "1 hour, 1 minute"


# Verifies the span is the same regardless of which timestamp is passed first
def test_timespan_is_order_independent(lm_module):
    assert lm_module.calculate_timespan(TS, TS + 7200) == lm_module.calculate_timespan(TS + 7200, TS)


# Verifies seconds are included when the caller asks for them, which the in-game report does
def test_timespan_can_include_seconds(lm_module):
    assert lm_module.calculate_timespan(TS + 3661, TS, show_seconds=True) == "1 hour, 1 minute, 1 second"


# Verifies seconds are still shown for a sub-minute span, so a short gap is not reported as nothing
def test_short_spans_keep_seconds(lm_module):
    assert lm_module.calculate_timespan(TS + 30, TS) == "30 seconds"


# Verifies datetimes and floats are accepted alongside epoch integers
def test_timespan_accepts_every_supported_input_type(lm_module):
    earlier = datetime(2026, 1, 1, 12, 0, 0)
    later = datetime(2026, 1, 1, 14, 30, 0)

    assert lm_module.calculate_timespan(later, earlier) == "2 hours, 30 minutes"
    assert lm_module.calculate_timespan(later.timestamp(), earlier.timestamp()) == "2 hours, 30 minutes"


# Verifies weeks can be folded into days for the shorter lines
def test_timespan_can_hide_weeks(lm_module):
    ten_days = TS + 10 * 86400

    assert lm_module.calculate_timespan(ten_days, TS) == "1 week, 3 days"
    assert lm_module.calculate_timespan(ten_days, TS, show_weeks=False) == "10 days"


# Verifies an identical pair of timestamps reports no elapsed time
def test_identical_timestamps_report_zero(lm_module):
    assert lm_module.calculate_timespan(TS, TS) == "0 seconds"


@pytest.mark.parametrize("value", [None, "not a timestamp", object()])
# Verifies an unusable value produces an empty string instead of raising inside the monitoring loop
def test_unusable_timespan_inputs_return_empty(lm_module, value):
    assert lm_module.calculate_timespan(value, TS) == ""
    assert lm_module.calculate_timespan(TS, value) == ""


# Verifies the long timestamp format carries weekday, date and full time
def test_long_timestamp_format(lm_module):
    assert lm_module.get_date_from_ts(TS) == "Thu 01 Jan 2026, 00:20:00"
    assert lm_module.get_date_from_ts(float(TS)) == "Thu 01 Jan 2026, 00:20:00"
    assert lm_module.get_date_from_ts(datetime(2026, 1, 1, 0, 20, 0)) == "Thu 01 Jan 2026, 00:20:00"


# Verifies an unusable timestamp renders as empty rather than breaking a notification body
def test_long_timestamp_of_an_unusable_value_is_empty(lm_module):
    assert lm_module.get_date_from_ts(None) == ""
    assert lm_module.get_date_from_ts("yesterday") == ""


# Verifies the short format drops the year and can drop the time as well
def test_short_timestamp_switches(lm_module):
    assert lm_module.get_short_date_from_ts(TS) == "Thu 01 Jan 00:20"
    assert lm_module.get_short_date_from_ts(TS, show_hour=False) == "Thu 01 Jan"


# Verifies the year appears only when the timestamp is not from the current year
def test_short_timestamp_adds_the_year_only_when_it_differs(lm_module):
    now = datetime.now()
    same_year = now.replace(month=6, day=15, hour=12, minute=0, second=0, microsecond=0)
    other_year = same_year.replace(year=now.year - 3)

    assert lm_module.get_short_date_from_ts(same_year, show_year=True) == lm_module.get_short_date_from_ts(same_year)
    assert str(other_year.year)[2:] in lm_module.get_short_date_from_ts(other_year, show_year=True)


# Verifies the time-only format honors the seconds switch
def test_hour_and_minute_format(lm_module):
    assert lm_module.get_hour_min_from_ts(TS) == "00:20"
    assert lm_module.get_hour_min_from_ts(TS, show_seconds=True) == "00:20:00"


# Verifies a match inside one day prints the date once and then only the end time
def test_range_within_one_day_prints_the_date_once(lm_module):
    assert lm_module.get_range_of_dates_from_tss(TS, TS + 1800) == "Thu 01 Jan 2026, 00:20:00 - 00:50:00"
    assert lm_module.get_range_of_dates_from_tss(TS, TS + 1800, short=True) == "Thu 01 Jan 00:20 - 00:50"


# Verifies a match spanning midnight prints both dates
def test_range_across_days_prints_both_dates(lm_module):
    assert lm_module.get_range_of_dates_from_tss(TS, TS + 86400, short=True) == "Thu 01 Jan 00:20 - Fri 02 Jan 00:20"


# Verifies the separator between the two ends of a range is configurable
def test_range_separator_is_configurable(lm_module):
    assert " to " in lm_module.get_range_of_dates_from_tss(TS, TS + 1800, between_sep=" to ")


# Verifies an unusable end of a range collapses to an empty string
def test_range_with_an_unusable_end_is_empty(lm_module):
    assert lm_module.get_range_of_dates_from_tss(None, TS) == ""
    assert lm_module.get_range_of_dates_from_tss(TS, None) == ""


# Verifies the current timestamp line carries the prefix the caller supplied
def test_current_timestamp_carries_its_prefix(lm_module, fake_clock):
    assert lm_module.get_cur_ts("Timestamp: ") == "Timestamp: Thu 01 Jan 2026, 00:20:00"
