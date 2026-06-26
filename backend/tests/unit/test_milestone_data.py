import pytest

from app.core.milestone_data import get_all_milestones, get_milestones_for_age, get_milestone_categories


class TestMilestoneData:
    def test_get_all_milestones(self):
        milestones = get_all_milestones()
        assert len(milestones) > 0
        categories = {m.category for m in milestones}
        assert categories <= {"motor", "language", "cognitive", "social"}

    def test_get_milestones_for_age(self):
        milestones = get_milestones_for_age(12)
        assert all(m.age_months <= 12 for m in milestones)
        assert any(m.title == "独站" for m in milestones)

    def test_get_milestones_for_none_age(self):
        milestones = get_milestones_for_age(None)
        assert len(milestones) == len(get_all_milestones())

    def test_get_milestone_categories(self):
        categories = get_milestone_categories()
        assert "motor" in categories
        assert "language" in categories
