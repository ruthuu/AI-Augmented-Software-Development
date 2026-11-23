from app.prompt import SYSTEM_PROMPT, build_user_message


def test_a_time_without_a_day_must_be_clarified() -> None:
    assert "at 5pm" in SYSTEM_PROMPT
    assert "Do not assume today" in SYSTEM_PROMPT


def test_explicit_today_and_durations_are_still_allowed() -> None:
    assert '"today"' in SYSTEM_PROMPT
    assert "in 2 hours" in SYSTEM_PROMPT


def test_a_day_without_a_time_must_be_clarified() -> None:
    assert '"on Friday"' in SYSTEM_PROMPT
    assert "default hour" in SYSTEM_PROMPT


def test_user_text_is_wrapped_as_data() -> None:
    message = build_user_message("hello", "2026-11-23T10:00:00+05:30")
    assert message == "now: 2026-11-23T10:00:00+05:30\n<request>\nhello\n</request>"
