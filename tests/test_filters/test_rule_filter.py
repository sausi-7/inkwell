"""Tests for inkwell.filters.rule_filter."""

from inkwell.filters.rule_filter import apply_pre_filters


def test_no_filters_passes_everything_through(signal_factory):
    signals = [signal_factory(platform_id="a"), signal_factory(platform_id="b")]
    assert apply_pre_filters(signals, {}) == signals


def test_min_score_drops_low_scoring(signal_factory):
    signals = [
        signal_factory(platform_id="keep", score=10),
        signal_factory(platform_id="drop", score=1),
    ]
    result = apply_pre_filters(signals, {"thresholds": {"min_score": 5}})
    assert [s.platform_id for s in result] == ["keep"]


def test_max_comments_drops_megathreads(signal_factory):
    signals = [
        signal_factory(platform_id="keep", reply_count=10),
        signal_factory(platform_id="drop", reply_count=9999),
    ]
    result = apply_pre_filters(signals, {"thresholds": {"max_comments": 500}})
    assert [s.platform_id for s in result] == ["keep"]


def test_exclude_keyword_matches_in_body(signal_factory):
    signals = [
        signal_factory(platform_id="keep", body="Building a CRM tool"),
        signal_factory(platform_id="drop", body="We are HIRING a senior engineer"),
    ]
    result = apply_pre_filters(signals, {"keywords": {"exclude": ["hiring"]}})
    assert [s.platform_id for s in result] == ["keep"]


def test_include_keyword_requires_at_least_one_match(signal_factory):
    signals = [
        signal_factory(platform_id="yes", title="Need feedback on my app", body=""),
        signal_factory(platform_id="no", title="General discussion thread", body=""),
    ]
    result = apply_pre_filters(signals, {"keywords": {"include": ["feedback", "help"]}})
    assert [s.platform_id for s in result] == ["yes"]


def test_keyword_filtering_is_case_insensitive(signal_factory):
    signals = [signal_factory(title="I need HELP with pricing")]
    result = apply_pre_filters(signals, {"keywords": {"include": ["help"]}})
    assert len(result) == 1


def test_status_filter_defaults_to_active_only(signal_factory):
    signals = [
        signal_factory(platform_id="active", status="active"),
        signal_factory(platform_id="archived", status="archived"),
        signal_factory(platform_id="locked", status="inactive"),
    ]
    result = apply_pre_filters(signals, {"thresholds": {"min_score": 0}})
    assert [s.platform_id for s in result] == ["active"]


def test_allowed_statuses_overrides_default(signal_factory):
    signals = [
        signal_factory(platform_id="a", status="active"),
        signal_factory(platform_id="b", status="archived"),
    ]
    result = apply_pre_filters(signals, {"allowed_statuses": ["active", "archived"]})
    assert {s.platform_id for s in result} == {"a", "b"}


def test_post_type_self_only_drops_link_posts(signal_factory):
    signals = [
        signal_factory(platform_id="self", is_self=True),
        signal_factory(platform_id="link", is_self=False),
    ]
    result = apply_pre_filters(signals, {"post_type": {"allow": "self_only"}})
    assert [s.platform_id for s in result] == ["self"]


def test_flair_exclude_matches_case_insensitive(signal_factory):
    signals = [
        signal_factory(platform_id="good", flair="Question"),
        signal_factory(platform_id="bad", flair="MEME"),
    ]
    result = apply_pre_filters(signals, {"flairs": {"exclude": ["meme"]}})
    assert [s.platform_id for s in result] == ["good"]


def test_include_and_exclude_compose(signal_factory):
    signals = [
        signal_factory(platform_id="keep", title="help with onboarding flow", body=""),
        signal_factory(platform_id="drop_exclude", title="help us with crypto airdrop", body=""),
        signal_factory(platform_id="drop_no_include", title="random discussion", body=""),
    ]
    filters = {"keywords": {"include": ["help"], "exclude": ["crypto"]}}
    result = apply_pre_filters(signals, filters)
    assert [s.platform_id for s in result] == ["keep"]
