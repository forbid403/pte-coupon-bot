"""PTE 쿠폰 모니터링 봇 메인 엔트리포인트"""

import argparse
import logging
import sys

from dotenv import load_dotenv

import storage
from evaluate import extract_codes, fetch_blog_text
from notify import send_coupon_alert
from search import fetch_all_results

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run(bootstrap: bool = False):
    storage.init_db()
    invalid_codes = storage.load_invalid_codes()
    log.info("Loaded %d invalid codes", len(invalid_codes))

    posts = fetch_all_results()
    log.info("Total posts from Naver: %d", len(posts))

    new_urls: list[str] = []
    notified = 0

    for post in posts:
        url = post["url"]

        if storage.is_seen(url):
            log.debug("Skip (seen): %s", url)
            continue

        new_urls.append(url)

        if bootstrap:
            continue  # 알림 없이 seen 처리만

        # 본문 가져오기
        if post["source"] == "blog":
            text = fetch_blog_text(post["raw_url"])
            if not text:
                text = post["description"]
        else:
            # 카페: API description만 사용
            text = post["description"]

        full_text = f"{post['title']} {text}"
        result = extract_codes(post["title"], full_text)

        codes = result.get("codes", [])
        context = result.get("context", "")
        confidence = result.get("confidence", 0)

        # invalid 필터
        new_codes = [c for c in codes if c.upper() not in invalid_codes]

        if new_codes and confidence >= 3:
            send_coupon_alert(
                codes=new_codes,
                title=post["title"],
                url=url,
                context=context,
                confidence=confidence,
            )
            notified += 1
        else:
            log.info(
                "No new codes (codes=%s, conf=%d): %s",
                codes, confidence, post["title"][:40],
            )

    storage.mark_seen(new_urls)
    log.info(
        "Done. new_posts=%d, notified=%d, bootstrap=%s",
        len(new_urls), notified, bootstrap,
    )


def main():
    parser = argparse.ArgumentParser(description="PTE 쿠폰 모니터링 봇")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="첫 실행용: 검색 결과 전부 seen 처리하고 알림 없음 (알림 폭탄 방지)",
    )
    args = parser.parse_args()

    try:
        run(bootstrap=args.bootstrap)
    except KeyboardInterrupt:
        log.info("Interrupted")
        sys.exit(0)
    except Exception as e:
        log.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
