"""SQLite 상태 관리: seen_posts, known_invalid_codes"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"
KNOWN_CODES_PATH = Path(__file__).parent / "known_codes.txt"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_posts (
                url TEXT PRIMARY KEY,
                seen_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS known_invalid_codes (
                code TEXT PRIMARY KEY,
                added_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()


def is_seen(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM seen_posts WHERE url = ?", (url,)).fetchone()
        return row is not None


def mark_seen(urls: list[str]):
    if not urls:
        return
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_posts (url) VALUES (?)",
            [(u,) for u in urls],
        )
        conn.commit()


def load_invalid_codes() -> set[str]:
    """known_codes.txt + DB의 무효 코드를 합쳐서 반환 (대소문자 무시)"""
    codes: set[str] = set()

    # 텍스트 파일
    if KNOWN_CODES_PATH.exists():
        for line in KNOWN_CODES_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                codes.add(line.upper())

    # DB
    with get_conn() as conn:
        rows = conn.execute("SELECT code FROM known_invalid_codes").fetchall()
        for row in rows:
            codes.add(row["code"].upper())

    return codes


def add_invalid_code(code: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO known_invalid_codes (code) VALUES (?)",
            (code.upper(),),
        )
        conn.commit()


# ── 테스트 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print(f"DB initialized: {DB_PATH}")

    mark_seen(["https://example.com/post/1", "https://example.com/post/2"])
    print("mark_seen OK")

    print("is_seen(post/1):", is_seen("https://example.com/post/1"))
    print("is_seen(post/9):", is_seen("https://example.com/post/9"))

    add_invalid_code("TESTCODE99")
    codes = load_invalid_codes()
    print("invalid codes:", codes)
    assert "TESTCODE99" in codes
    print("storage.py: all tests passed")
