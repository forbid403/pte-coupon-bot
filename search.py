"""네이버 검색 API로 블로그/카페 글 검색"""

import logging
import os
import re
from urllib.parse import urlparse, urlunparse

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

NAVER_BLOG_URL = "https://openapi.naver.com/v1/search/blog.json"
NAVER_CAFE_URL = "https://openapi.naver.com/v1/search/cafearticle.json"

QUERIES = ["PTE 쿠폰", "PTE 할인코드", "PTE 할인쿠폰", "PTE 프로모코드"]

TAG_RE = re.compile(r"<[^>]+>")


def _headers() -> dict:
    return {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
    }


def _normalize_url(url: str) -> str:
    """쿼리 파라미터·프래그먼트 제거해서 중복 방지"""
    p = urlparse(url)
    return urlunparse(p._replace(query="", fragment=""))


def _strip_tags(text: str) -> str:
    return TAG_RE.sub("", text).strip()


def _search(api_url: str, query: str, display: int = 20) -> list[dict]:
    try:
        resp = requests.get(
            api_url,
            headers=_headers(),
            params={"query": query, "display": display, "sort": "date"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results = []
        for item in items:
            link = item.get("link") or item.get("url", "")
            results.append(
                {
                    "url": _normalize_url(link),
                    "raw_url": link,
                    "title": _strip_tags(item.get("title", "")),
                    "description": _strip_tags(item.get("description", "")),
                    "source": "blog" if "blog" in api_url else "cafe",
                    "query": query,
                }
            )
        return results
    except Exception as e:
        log.warning("Naver API error (query=%s, api=%s): %s", query, api_url, e)
        return []


def fetch_all_results() -> list[dict]:
    """모든 쿼리 × 블로그/카페 검색 결과 합산, URL 중복 제거"""
    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in QUERIES:
        for api_url in (NAVER_BLOG_URL, NAVER_CAFE_URL):
            for item in _search(api_url, query):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    results.append(item)

    log.info("Fetched %d unique posts from Naver", len(results))
    return results


# ── 테스트 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not os.getenv("NAVER_CLIENT_ID"):
        print("NAVER_CLIENT_ID not set — skipping live test")
    else:
        items = fetch_all_results()
        print(f"총 {len(items)}개 결과")
        for i in items[:3]:
            print(f"  [{i['source']}] {i['title'][:40]}  {i['url'][:60]}")
