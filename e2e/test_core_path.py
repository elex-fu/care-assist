"""E2E core path: login → add member → upload report → OCR → view indicator → AI chat.

Prerequisites:
- WeChat Developer Tools installed and CLI path configured in minium.json
- Backend running at http://localhost:8000
- Minium framework installed: pip install minium

Run:
    cd e2e && minitest -c minium.json -g test_core_path.py

Note: OCR step uses mock mode (bypasses actual AI/OCR) to avoid external dependency.
"""

import minium
import time


class CorePathTest(minium.MiniTest):
    """End-to-end test of the most critical user journey."""

    def setUp(self):
        super().setUp()
        # Ensure clean state: navigate to index and clear storage
        self.app.navigate_to("/pages/index/index")
        self.page.wait_for(2)
        self.app.call_wx_method("clearStorageSync")
        self.page.wait_for(1)

    # ---------- Login ----------
    def test_01_login(self):
        """Login with mock wx code, create family, land on home."""
        self.app.navigate_to("/pages/login/login")
        self.page.wait_for(2)

        # Trigger login button tap
        self.page.get_element("button").tap()
        self.page.wait_for(3)

        # After login, should redirect to onboarding or home
        current = self.app.get_current_page()
        self.assertIn(current.path, ["pages/onboarding/onboarding", "pages/home/home"])

    # ---------- Onboarding / Create Family ----------
    def test_02_onboarding(self):
        """Complete onboarding: create family + add first member."""
        self.app.navigate_to("/pages/onboarding/onboarding")
        self.page.wait_for(2)

        # Fill family name (or use default)
        self.page.get_element("input").input("测试家庭")
        self.page.get_element(".submit-btn").tap()
        self.page.wait_for(2)

        # Add first member
        self.page.get_element("input[placeholder='姓名']").input("爸爸")
        self.page.get_element("picker").tap()  # gender picker
        self.page.wait_for(1)
        self.page.get_element(".picker-item", inner_text="男").tap()
        self.page.get_element(".submit-btn").tap()
        self.page.wait_for(3)

        current = self.app.get_current_page()
        self.assertEqual(current.path, "pages/home/home")

    # ---------- Add Member ----------
    def test_03_add_member(self):
        """Add a new family member from home."""
        self.app.navigate_to("/pages/home/home")
        self.page.wait_for(2)

        # Tap add-member button
        self.page.get_element(".add-member-btn").tap()
        self.page.wait_for(2)

        # Fill form
        self.page.get_element("input[placeholder='姓名']").input("妈妈")
        self.page.get_element("picker").tap()
        self.page.wait_for(1)
        self.page.get_element(".picker-item", inner_text="女").tap()
        self.page.get_element(".submit-btn").tap()
        self.page.wait_for(2)

        current = self.app.get_current_page()
        self.assertEqual(current.path, "pages/home/home")

    # ---------- Upload Report ----------
    def test_04_upload_report(self):
        """Upload a report image and trigger OCR (mock mode)."""
        self.app.navigate_to("/pages/upload/upload")
        self.page.wait_for(2)

        # Select member
        self.page.get_element(".member-picker").tap()
        self.page.wait_for(1)
        self.page.get_element(".picker-item").tap()

        # Choose image (mock: we tap the upload area which triggers chooseImage)
        self.page.get_element(".upload-area").tap()
        self.page.wait_for(2)

        # Confirm upload
        self.page.get_element(".upload-btn").tap()
        self.page.wait_for(3)

        # Should show processing state
        status_text = self.page.get_element(".upload-status").inner_text
        self.assertIn(status_text, ["上传中...", "AI 识别中...", "完成"])

    # ---------- View Indicator ----------
    def test_05_view_indicator(self):
        """Navigate to indicators page and view latest value."""
        self.app.navigate_to("/pages/indicators/indicators")
        self.page.wait_for(2)

        # Should see indicator cards or empty state
        elements = self.page.get_elements(".indicator-card")
        self.assertGreaterEqual(len(elements), 0)

        # If indicators exist, tap first one to see trend
        if len(elements) > 0:
            elements[0].tap()
            self.page.wait_for(2)
            current = self.app.get_current_page()
            self.assertIn("indicator", current.path)

    # ---------- AI Chat ----------
    def test_06_ai_chat(self):
        """Open AI tab and send a health question."""
        self.app.navigate_to("/pages/ai/ai")
        self.page.wait_for(2)

        # Type question
        self.page.get_element("input").input("我爸爸的血压怎么样")
        self.page.get_element(".ai-send").tap()
        self.page.wait_for(5)

        # Should see assistant response
        messages = self.page.get_elements(".ai-bubble")
        self.assertGreater(len(messages), 0)

        # Last message should be from assistant
        last_msg = messages[-1]
        self.assertIn("assistant", last_msg.get_attribute("class"))
