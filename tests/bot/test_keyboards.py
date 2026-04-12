"""Unit tests for bot keyboards.

Verifies that:
- open_miniapp_keyboard() produces a Web App button with the correct URL
- main_menu_keyboard() contains a launch button and quick-action entries
"""

from __future__ import annotations

from app.bot.keyboards import main_menu_keyboard, open_miniapp_keyboard

_URL = "https://t.me/neurosmm_bot/app"


class TestOpenMiniappKeyboard:
    def test_returns_inline_keyboard(self) -> None:
        kb = open_miniapp_keyboard(_URL)
        assert len(kb.inline_keyboard) == 1

    def test_button_has_web_app(self) -> None:
        kb = open_miniapp_keyboard(_URL)
        btn = kb.inline_keyboard[0][0]
        assert btn.web_app is not None
        assert btn.web_app.url == _URL

    def test_button_label(self) -> None:
        kb = open_miniapp_keyboard(_URL)
        btn = kb.inline_keyboard[0][0]
        assert btn.text == "Open NeuroSMM"


class TestMainMenuKeyboard:
    def test_first_row_is_launch_button(self) -> None:
        kb = main_menu_keyboard(_URL)
        btn = kb.inline_keyboard[0][0]
        assert btn.web_app is not None
        assert btn.web_app.url == _URL

    def test_contains_projects_button(self) -> None:
        kb = main_menu_keyboard(_URL)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        labels = [b.text for b in all_buttons]
        assert "Projects" in labels

    def test_contains_drafts_button(self) -> None:
        kb = main_menu_keyboard(_URL)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        labels = [b.text for b in all_buttons]
        assert "Drafts" in labels

    def test_contains_schedule_button(self) -> None:
        kb = main_menu_keyboard(_URL)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        labels = [b.text for b in all_buttons]
        assert "Schedule" in labels

    def test_projects_button_url_contains_miniapp_base(self) -> None:
        kb = main_menu_keyboard(_URL)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        projects_btn = next(b for b in all_buttons if b.text == "Projects")
        assert projects_btn.web_app is not None
        assert _URL in projects_btn.web_app.url
