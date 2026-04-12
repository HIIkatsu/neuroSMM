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

    def test_single_row_only(self) -> None:
        """Main menu is a single launch button — no broken sub-page URLs."""
        kb = main_menu_keyboard(_URL)
        assert len(kb.inline_keyboard) == 1

    def test_launch_button_label(self) -> None:
        kb = main_menu_keyboard(_URL)
        btn = kb.inline_keyboard[0][0]
        assert btn.text == "Open NeuroSMM"

    def test_launch_button_url_matches(self) -> None:
        kb = main_menu_keyboard(_URL)
        btn = kb.inline_keyboard[0][0]
        assert btn.web_app is not None
        assert btn.web_app.url == _URL
