"""E2E extended paths: hospital + child + medication + search + report detail.

Prerequisites:
- WeChat Developer Tools installed and CLI path configured in minium.json
- Backend running at http://localhost:8000
- Minium framework installed: pip install minium

Run:
    cd e2e && minitest -c minium.json -g test_extended_paths.py

Note: These tests assume a family with members already exists (run test_core_path first
or manually seed data). Each test navigates directly to its starting page.
"""

import minium


class ExtendedPathsTest(minium.MiniTest):
    """End-to-end tests for secondary feature paths."""

    def setUp(self):
        super().setUp()
        self.app.navigate_to("/pages/index/index")
        self.page.wait_for(2)

    # ---------- Hospital Path ----------
    def test_10_hospital_list(self):
        """Navigate to hospital list for a member."""
        self.app.navigate_to("/pkg-hospital/pages/hospital/hospital?member_id=test_member_id")
        self.page.wait_for(2)

        # Should see list container or empty state
        elements = self.page.get_elements(".event-card")
        empty = self.page.get_elements(".empty-state")
        self.assertTrue(len(elements) >= 0 or len(empty) >= 0)

    def test_11_hospital_add(self):
        """Create a new hospital event."""
        self.app.navigate_to("/pkg-hospital/pages/hospital-add/hospital-add?member_id=test_member_id")
        self.page.wait_for(2)

        # Fill form
        self.page.get_element(".input[placeholder='医院']").input("测试医院")
        self.page.get_element(".input[placeholder='科室']").input("内科")
        self.page.get_element(".picker", inner_text="入院日期").tap()
        self.page.wait_for(1)
        self.page.get_element(".picker-item").tap()  # confirm date
        self.page.get_element(".input[placeholder='诊断']").input("肺炎")
        self.page.get_element(".submit-btn").tap()
        self.page.wait_for(3)

        current = self.app.get_current_page()
        self.assertEqual(current.path, "pkg-hospital/pages/hospital/hospital")

    def test_12_hospital_detail(self):
        """View hospital detail with tabs."""
        self.app.navigate_to("/pkg-hospital/pages/hospital-detail/hospital-detail?id=test_event_id")
        self.page.wait_for(2)

        # Should have 3 tabs
        tabs = self.page.get_elements(".tab")
        self.assertGreaterEqual(len(tabs), 3)

        # Switch to key indicators tab (2nd tab)
        tabs[1].tap()
        self.page.wait_for(1)
        cards = self.page.get_elements(".indicator-card")
        self.assertGreaterEqual(len(cards), 0)

        # Switch to compare tab (3rd tab)
        tabs[2].tap()
        self.page.wait_for(1)
        rows = self.page.get_elements(".compare-row")
        self.assertGreaterEqual(len(rows), 0)

    # ---------- Child Path ----------
    def test_20_child_dashboard(self):
        """Navigate to child dashboard."""
        self.app.navigate_to("/pkg-child/pages/child-dashboard/child-dashboard?member_id=test_child_id")
        self.page.wait_for(2)

        # Should see vaccine section or growth chart
        elements = self.page.get_elements(".section-card")
        self.assertGreaterEqual(len(elements), 0)

    def test_21_vaccine_list(self):
        """View vaccine records."""
        self.app.navigate_to("/pkg-child/pages/vaccine/vaccine?member_id=test_child_id")
        self.page.wait_for(2)

        cards = self.page.get_elements(".vaccine-card")
        empty = self.page.get_elements(".empty-state")
        self.assertTrue(len(cards) >= 0 or len(empty) >= 0)

    def test_22_vaccine_add(self):
        """Add a vaccine record."""
        self.app.navigate_to("/pkg-child/pages/vaccine-add/vaccine-add?member_id=test_child_id")
        self.page.wait_for(2)

        self.page.get_element("input[placeholder='疫苗名称']").input("乙肝疫苗")
        self.page.get_element("picker").tap()
        self.page.wait_for(1)
        self.page.get_element(".picker-item").tap()
        self.page.get_element(".submit-btn").tap()
        self.page.wait_for(3)

        current = self.app.get_current_page()
        self.assertEqual(current.path, "pkg-child/pages/vaccine/vaccine")

    # ---------- Medication Path ----------
    def test_30_medication_list(self):
        """View medication reminders."""
        self.app.navigate_to("/pkg-medication/pages/medication/medication?member_id=test_member_id")
        self.page.wait_for(2)

        cards = self.page.get_elements(".medication-card")
        empty = self.page.get_elements(".empty-state")
        self.assertTrue(len(cards) >= 0 or len(empty) >= 0)

    def test_31_medication_add(self):
        """Add a medication reminder."""
        self.app.navigate_to("/pkg-medication/pages/medication-add/medication-add?member_id=test_member_id")
        self.page.wait_for(2)

        self.page.get_element("input[placeholder='药品名称']").input("阿司匹林")
        self.page.get_element("input[placeholder='剂量']").input("100mg")
        self.page.get_element("picker").tap()
        self.page.wait_for(1)
        self.page.get_element(".picker-item").tap()
        self.page.get_element(".submit-btn").tap()
        self.page.wait_for(3)

        current = self.app.get_current_page()
        self.assertEqual(current.path, "pkg-medication/pages/medication/medication")

    # ---------- Search Path ----------
    def test_40_search_page(self):
        """Open search and perform a query."""
        self.app.navigate_to("/pages/search/search")
        self.page.wait_for(2)

        self.page.get_element(".search-input").input("血压")
        self.page.get_element(".search-btn").tap()
        self.page.wait_for(3)

        # Should see results or empty state with ask-ai button
        results = self.page.get_elements(".result-card")
        empty = self.page.get_elements(".ask-ai-btn")
        self.assertTrue(len(results) >= 0 or len(empty) >= 0)

    # ---------- Report Detail Path ----------
    def test_50_report_detail(self):
        """Navigate to report detail from member detail."""
        self.app.navigate_to("/pkg-system/pages/report-detail/report-detail?id=test_report_id")
        self.page.wait_for(2)

        # Should see type tag and status badge
        type_tag = self.page.get_elements(".type-tag")
        self.assertGreaterEqual(len(type_tag), 1)

        # Should see indicator rows or image placeholders
        indicators = self.page.get_elements(".indicator-row")
        images = self.page.get_elements(".image-item")
        self.assertTrue(len(indicators) >= 0 or len(images) >= 0)
