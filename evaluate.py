"""네이버 블로그 본문 fetch + Claude API로 쿠폰 코드 추출"""

import logging
import os
import re

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# 블로그 본문 추출 선택자 순서대로 시도
_BLOG_SELECTORS = [
    "div.se-main-container",   # 스마트에디터 ONE
    "div#postViewArea",         # 구 에디터
    "div.post-view",
    "div#content",
]

_client = None  # type: anthropic.Anthropic | None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def fetch_blog_text(url: str, timeout: int = 10) -> str:
    """네이버 블로그 URL → 본문 텍스트 (실패 시 빈 문자열)"""
    try:
        # 모바일 URL로 변환하면 파싱이 쉬움
        mobile_url = re.sub(
            r"blog\.naver\.com/([^/]+)/(\d+)",
            r"m.blog.naver.com/\1/\2",
            url,
        )
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PTEBot/1.0)"}
        resp = requests.get(mobile_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for sel in _BLOG_SELECTORS:
            tag, _, cls = sel.partition(".")
            if cls:
                el = soup.find(tag, class_=cls)
            else:
                _, _, id_ = sel.partition("#")
                el = soup.find(tag, id=id_) if id_ else soup.find(tag)
            if el:
                return el.get_text(" ", strip=True)[:4000]

        # 선택자 전부 실패 → body 전체
        body = soup.find("body")
        return body.get_text(" ", strip=True)[:4000] if body else ""
    except Exception as e:
        log.warning("Blog fetch failed (%s): %s", url, e)
        return ""


_TOOL = {
    "name": "extract_coupon",
    "description": "게시글에서 PTE(Pearson Test of English) 쿠폰/할인 코드를 추출합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "발견된 쿠폰/할인 코드 목록. 없으면 빈 배열.",
            },
            "context": {
                "type": "string",
                "description": "쿠폰 종류, 만료일, 할인율 등 관련 맥락 요약 (한국어, 1-2문장).",
            },
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10,
                "description": "추출 신뢰도 0-10. PTE 시험 관련 실제 코드면 높게.",
            },
        },
        "required": ["codes", "context", "confidence"],
    },
}

_SYSTEM = (
    "당신은 PTE(Pearson Test of English) 쿠폰 코드 추출 전문가입니다. "
    "제공된 게시글 텍스트에서 PTE 시험 등록/할인에 사용할 수 있는 쿠폰 코드나 프로모션 코드를 "
    "정확히 추출하세요. 일반 텍스트, 광고 문구, URL이나 이메일 주소 속 문자열은 코드로 취급하지 마세요. "
    "코드가 없으면 codes를 빈 배열로 반환하세요."
)


def extract_codes(title: str, text: str) -> dict:
    """Claude tool use로 코드 추출. 실패 시 {'codes':[], 'context':'', 'confidence':0}"""
    content = f"제목: {title}\n\n본문:\n{text[:3000]}"
    try:
        resp = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM,
            tools=[_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": content}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "extract_coupon":
                return block.input
    except Exception as e:
        log.warning("Claude API error: %s", e)
    return {"codes": [], "context": "", "confidence": 0}


# ── 테스트 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Claude 추출 테스트 (더미 텍스트)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — skipping live test")
    else:
        sample = (
            "PTE Academic 시험 등록 시 할인 코드 PTESAVE20을 입력하면 20% 할인됩니다. "
            "이 코드는 2025년 3월 31일까지 유효합니다."
        )
        result = extract_codes("PTE 할인쿠폰 공유", sample)
        print("추출 결과:", result)
        assert "PTESAVE20" in result.get("codes", []), "코드 추출 실패"
        print("evaluate.py: test passed")
