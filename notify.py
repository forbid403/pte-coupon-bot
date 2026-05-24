"""Discord / Telegram 알림 전송"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


def _discord(message: str) -> bool:
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        resp = requests.post(url, json={"content": message}, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        log.warning("Discord notify failed: %s", e)
        return False


def _telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log.warning("Telegram notify failed: %s", e)
        return False


def send_coupon_alert(
    codes: list[str],
    title: str,
    url: str,
    context: str,
    confidence: int,
) -> bool:
    """새 쿠폰 코드 발견 알림. 하나라도 전송 성공 시 True."""
    code_block = "\n".join(f"  `{c}`" for c in codes)
    message = (
        "🎟 **PTE 새 쿠폰 코드 발견!**\n\n"
        f"**코드**\n{code_block}\n\n"
        f"**출처**: {title}\n"
        f"**URL**: {url}\n"
        f"**내용**: {context}\n"
        f"**신뢰도**: {confidence}/10\n\n"
        "_만료/무효 코드는 `known_codes.txt`에 추가하세요._"
    )

    sent = _discord(message) or _telegram(message)
    if sent:
        log.info("Notified: codes=%s url=%s", codes, url)
    else:
        log.warning("No notification channel configured or all failed")
    return sent


# ── 테스트 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ok = send_coupon_alert(
        codes=["TESTCODE10", "PTEDEMO"],
        title="PTE 할인쿠폰 테스트 글",
        url="https://blog.naver.com/example/123456789",
        context="PTE Academic 10% 할인, 2025년 12월까지 유효",
        confidence=8,
    )
    print("전송 성공:", ok)
    if not ok:
        print("(DISCORD_WEBHOOK_URL 또는 Telegram 환경변수를 설정하세요)")
