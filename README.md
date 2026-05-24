# PTE 쿠폰 모니터링 봇

네이버에서 PTE 할인쿠폰 관련 글을 매일 검색하고, 새 쿠폰 코드를 Discord/Telegram으로 알림합니다.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일에 API 키 입력
```

## 환경변수

| 변수 | 설명 |
|------|------|
| `NAVER_CLIENT_ID` | 네이버 검색 API 클라이언트 ID |
| `NAVER_CLIENT_SECRET` | 네이버 검색 API 시크릿 |
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `DISCORD_WEBHOOK_URL` | Discord 웹훅 URL |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 (Discord 대신 사용 시) |
| `TELEGRAM_CHAT_ID` | Telegram 채팅 ID (Discord 대신 사용 시) |

## 사용법

```bash
# 첫 실행 (기존 게시글 전부 seen 처리, 알림 없음)
python bot.py --bootstrap

# 일반 실행
python bot.py

# 특정 모듈 테스트
python storage.py    # DB 초기화 테스트
python search.py     # 네이버 검색 테스트
python evaluate.py   # Claude 추출 테스트
python notify.py     # 알림 전송 테스트
```

## 무효 코드 관리

알림을 받은 쿠폰 코드가 만료/무효로 확인되면 `known_codes.txt`에 추가하세요.

```
EXPIRED_CODE_HERE
```

봇이 다음 실행 시 해당 코드는 건너뜁니다.

## GitHub Actions 자동화

`.github/workflows/daily.yml`이 매일 KST 09:00에 자동 실행됩니다.

Repository Settings > Secrets에 다음을 등록하세요:
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `ANTHROPIC_API_KEY`
- `DISCORD_WEBHOOK_URL`

실행 후 `data.db` 변경분은 자동으로 커밋됩니다.

## 디렉토리 구조

```
pte-coupon-bot/
├── bot.py              # 메인 엔트리포인트
├── search.py           # 네이버 검색 API
├── evaluate.py         # Claude API 코드 추출
├── notify.py           # Discord/Telegram 알림
├── storage.py          # SQLite 상태 관리
├── known_codes.txt     # 무효 코드 목록 (직접 편집)
├── data.db             # SQLite DB (상태 유지용, git에 포함)
├── .env.example
├── requirements.txt
└── .github/workflows/daily.yml
```
