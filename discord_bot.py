"""
Discord 봇: !invalid 코드명 → known_codes.txt에 추가 + GitHub 커밋

실행: python3 discord_bot.py
"""

import base64
import logging
import os

import discord
import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = os.environ.get("GH_REPO", "forbid403/pte-coupon-bot")
KNOWN_CODES_PATH = "known_codes.txt"

GH_API = f"https://api.github.com/repos/{GH_REPO}/contents/{KNOWN_CODES_PATH}"
GH_HEADERS = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}


# ── GitHub 파일 읽기/쓰기 ──────────────────────────────────────────────────

def _gh_get() -> tuple[str, str]:
    """(파일 내용, sha) 반환"""
    resp = requests.get(GH_API, headers=GH_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def _gh_put(content: str, sha: str, code: str):
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    resp = requests.put(
        GH_API,
        headers=GH_HEADERS,
        json={
            "message": f"chore: mark {code} as invalid [skip ci]",
            "content": encoded,
            "sha": sha,
        },
        timeout=10,
    )
    resp.raise_for_status()


def add_invalid_code_to_github(code: str) -> str:
    """
    GitHub의 known_codes.txt에 코드 추가.
    반환값: 'added' | 'already_exists'
    """
    code = code.upper()
    file_content, sha = _gh_get()

    existing = {
        line.strip().upper()
        for line in file_content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    if code in existing:
        return "already_exists"

    new_content = file_content.rstrip("\n") + f"\n{code}\n"
    _gh_put(new_content, sha, code)
    return "added"


# ── Discord 봇 ────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

HELP_TEXT = (
    "**PTE 쿠폰 봇 명령어**\n"
    "`!invalid 코드명` — 해당 코드를 무효 처리 (known_codes.txt에 추가)\n"
    "`!codes` — 현재 무효 코드 목록 확인\n"
    "`!help` — 이 도움말"
)


@client.event
async def on_ready():
    log.info("Discord bot ready: %s (channel_id=%d)", client.user, DISCORD_CHANNEL_ID)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    text = message.content.strip()

    # !invalid 코드명
    if text.lower().startswith("!invalid"):
        parts = text.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            await message.channel.send("사용법: `!invalid 코드명`\n예) `!invalid PTESAVE20`")
            return

        code = parts[1].strip()
        await message.channel.send(f"⏳ `{code.upper()}` 처리 중...")
        try:
            result = add_invalid_code_to_github(code)
            if result == "added":
                await message.channel.send(
                    f"✅ `{code.upper()}` 를 무효 코드 목록에 추가했습니다.\n"
                    f"_(GitHub `known_codes.txt` 자동 업데이트 완료)_"
                )
                log.info("Marked invalid: %s", code.upper())
            else:
                await message.channel.send(f"⚠️ `{code.upper()}` 는 이미 무효 코드 목록에 있습니다.")
        except Exception as e:
            log.exception("Failed to mark invalid: %s", e)
            await message.channel.send(f"❌ 오류 발생: `{e}`")

    # !codes — 현재 무효 코드 목록
    elif text.lower() == "!codes":
        try:
            file_content, _ = _gh_get()
            codes = [
                line.strip()
                for line in file_content.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if codes:
                code_list = "\n".join(f"• `{c}`" for c in codes)
                await message.channel.send(f"**현재 무효 코드 목록 ({len(codes)}개)**\n{code_list}")
            else:
                await message.channel.send("현재 무효 코드 목록이 비어있습니다.")
        except Exception as e:
            await message.channel.send(f"❌ 오류 발생: `{e}`")

    # !help
    elif text.lower() == "!help":
        await message.channel.send(HELP_TEXT)


def main():
    log.info("Starting Discord bot for repo: %s", GH_REPO)
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
