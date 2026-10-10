from datetime import UTC, datetime

from network_assessment.report.summary import Assessment, Summary, TopologySummary
from network_assessment.store import AssessmentStore


def _assessment(i=0):
    now = datetime(2026, 10, 10, tzinfo=UTC)
    return Assessment(
        id=f"a{i}",
        created_at=now,
        source_format="arg-json",
        rules_version="v",
        model_version="m",
        summary=Summary(
            resource_count=0,
            row_count=0,
            subscriptions=[],
            by_type={},
            topology=TopologySummary(pattern="isolated"),
            findings_count=0,
            findings_by_severity={},
            unknown_rules=0,
            rules_evaluated=0,
            warnings=[],
            rules_version="v",
            model_version="m",
            generated_at=now,
        ),
        findings=[],
        resources=[],
        unknowns=[],
        warnings=[],
    )


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_put_get_delete_with_token_and_404_semantics():
    store = AssessmentStore(ttl_seconds=60, max_items=5)
    stored = store.put(_assessment(), {"report.md": b"x"})
    assert len(stored.owner_token) >= 32 and stored.id != stored.owner_token
    assert store.get(stored.id, stored.owner_token)[1] == {"report.md": b"x"}
    assert store.get(stored.id, "wrong") is None
    assert store.get(stored.id, None) is None and store.get("", stored.owner_token) is None
    assert store.get("nope", stored.owner_token) is None
    assert store.expires_at(stored.id, stored.owner_token) == stored.expires_at
    assert store.delete(stored.id, "wrong") is False
    assert store.delete(stored.id, stored.owner_token) is True
    assert store.delete(stored.id, stored.owner_token) is False
    assert store.size == 0


def test_ttl_sweep_and_expiry_on_read():
    clock = Clock()
    store = AssessmentStore(ttl_seconds=10, max_items=5, clock=clock)
    s = store.put(_assessment(), {})
    clock.now += 11
    assert store.get(s.id, s.owner_token) is None
    assert store.sweep() == 1 and store.size == 0


def test_eviction_oldest_first():
    clock = Clock()
    store = AssessmentStore(ttl_seconds=100, max_items=2, clock=clock)
    first = store.put(_assessment(1), {})
    clock.now += 1
    second = store.put(_assessment(2), {})
    clock.now += 1
    third = store.put(_assessment(3), {})
    assert store.size == 2
    assert store.get(first.id, first.owner_token) is None
    assert store.get(second.id, second.owner_token) is not None and store.get(third.id, third.owner_token) is not None
    store.clear()
    assert store.size == 0
