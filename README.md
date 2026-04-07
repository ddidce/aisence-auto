# AIsence — AI 음악 자동화 프로젝트

AIsence 유튜브 채널용 AI 음악 생성 · 영상 제작 · 업로드 자동화 파이프라인

## 기술 스택

- **음악 생성** : [Suno AI](https://suno.com)
- **영상 제작** : Python (MoviePy / FFmpeg)
- **이미지 제작** : Canva
- **업로드** : YouTube Data API v3

## 폴더 구조

```
music_ai_proj/
├── music_file/
│   └── {시리즈명}/
│       ├── 배경이미지.png
│       ├── 곡제목.mp3
│       └── {시리즈명}_플레이리스트.mp4
├── scripts/
│   ├── suno_generate.py       # Suno API 음악 생성
│   ├── make_playlist_video.py # 합본 플레이리스트 영상 생성
│   ├── upload_youtube.py      # 유튜브 업로드
│   └── full_run.py            # 전체 자동화 실행
└── web/
    ├── main.py                # FastAPI 대시보드 백엔드
    └── index.html             # 웹 UI
```

## 실행 방법

```bash
# 웹 대시보드
uvicorn web.main:app --reload

# 음악 생성 (단독)
python scripts/suno_generate.py --title "곡 제목" --style "lofi, chill" --instrumental

# 유튜브 업로드 (단독)
python scripts/upload_youtube.py --video "경로.mp4" --title "제목" --genre lofi
```

## 환경 변수

`.env` 파일에 아래 항목을 설정하세요.

```
SUNOAPI_KEY=your_suno_api_key
```

---

## 저작권 안내

해당 채널에 업로드된 모든 음악, 가사는 **@AIsense**가 직접 제작한 콘텐츠입니다.
무단 사용 및 재 업로드는 금지되어 있습니다.

© AIsense. All rights reserved.
