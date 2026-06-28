import pytest

from app.core.milestone_data import _milestone_status, get_milestones_for_age


@pytest.mark.parametrize(
    "age_months,expected_status",
    [
        (1, "normal"),   # far from expected
        (11, "warning"), # 1 month before 12
        (12, "achieved"),
        (13, "achieved"),
        (15, "delayed"), # > 12 + 2
    ],
)
def test_milestone_status(age_months, expected_status):
    assert _milestone_status(age_months, 12) == expected_status


def test_get_milestones_for_age_sets_status():
    milestones = get_milestones_for_age(12)
    assert len(milestones) > 0
    for m in milestones:
        assert m.status in {"normal", "warning", "achieved", "delayed"}
        if m.age_months <= 12 <= m.age_months + 2:
            assert m.status == "achieved"


def test_get_milestones_for_age_none_age():
    milestones = get_milestones_for_age(None)
    assert all(m.status == "normal" for m in milestones)
