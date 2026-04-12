"""Inline and reply keyboards for the NeuroSMM bot.

Keyboards are built from config so that the Mini App URL stays testable
and easy to change without touching handler code.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def open_miniapp_keyboard(miniapp_url: str) -> InlineKeyboardMarkup:
    """Return a keyboard with a single Web App launch button.

    Parameters
    ----------
    miniapp_url:
        The HTTPS URL of the NeuroSMM Mini App.  Must be non-empty.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open NeuroSMM",
                    web_app=WebAppInfo(url=miniapp_url),
                )
            ]
        ]
    )


def main_menu_keyboard(miniapp_url: str) -> InlineKeyboardMarkup:
    """Return the main quick-action keyboard shown after /start.

    Provides a Mini App launcher plus lightweight navigation shortcuts.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open NeuroSMM",
                    web_app=WebAppInfo(url=miniapp_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Projects",
                    web_app=WebAppInfo(url=f"{miniapp_url}/projects"),
                ),
                InlineKeyboardButton(
                    text="Drafts",
                    web_app=WebAppInfo(url=f"{miniapp_url}/drafts"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Schedule",
                    web_app=WebAppInfo(url=f"{miniapp_url}/schedule"),
                ),
            ],
        ]
    )
