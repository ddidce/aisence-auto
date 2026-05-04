# AIsence 프로젝트 지침

## 음악 제작 시작 시
사용자가 "음악 만들어보자" 또는 음악 제작 관련 말을 꺼내면 항상 먼저 질문할 것:
**"어떤 느낌의 음악을 만들 거야?"**

## 프로젝트 개요
- AIsence 유튜브 채널용 AI 음악 자동 생성 + 영상 제작 + 업로드 자동화 프로젝트
- Suno AI로 음악 생성, MoviePy/FFmpeg으로 영상 제작, YouTube API로 업로드
- 캡컷 등 외부 영상 편집 툴 없이 Python 스크립트로 전부 처리

## 작업 흐름 (시리즈 제작 순서)

### 1단계 — 음악 생성 (Claude가 처리)
- 사용자가 원하는 분위기/콘셉트 전달
- Claude가 곡 제목, 스타일, 가사 기획
- `scripts/suno_generate.py`로 Suno API 호출 → MP3 자동 다운로드
- 저장 경로: `music_file/{시리즈명}/`
- 파일명 규칙: `트랙명_1.mp3`, `트랙명_2.mp3` (같은 곡 버전별)

### 2단계 — 배경 이미지 준비 (사용자가 처리)
- 사용자가 직접 이미지 제작 (캔바 등 활용)
- 저장 경로: `music_file/{시리즈명}/` (MP3와 같은 폴더)
- 포맷: PNG, 해상도 1920×1080 권장
- 이미지를 폴더에 넣어줬다고 말하면 → Claude가 이후 작업 자동 처리

### 3단계 — 영상 제작 (Claude가 처리)
- 스크립트: `scripts/make_playlist_video.py`
- 동작: 해당 폴더의 PNG + MP3 전체를 자동 감지 → 합본 영상 1개 생성
- 출력: `music_file/{시리즈명}/{시리즈명}_플레이리스트.mp4`
- 사용 라이브러리: MoviePy (캡컷 불필요)

### 4단계 — 유튜브 업로드 (Claude가 처리)
- 스크립트: `scripts/upload_youtube.py`
- 제목 형식: `PLAYLIST 🎵 | {에센셜 스타일 감성 제목}`
  - 에센셜 스타일 예시:
    - `PLAYLIST 🎵 | 비 오는 날 혼자 듣는 음악`
    - `PLAYLIST 🎵 | 아무것도 하기 싫은 오후`
    - `PLAYLIST 🎵 | 새벽 4시, 잠 못 드는 밤`
    - `PLAYLIST 🎵 | 카페 창가에 앉아 멍 때리는 시간`
  - 규칙: 짧고 감성적, 상황/감정 묘사, 분위기에 맞는 이모지 1개 선택
  - 이모지 예시: ☕ 카페/커피, 🌙 새벽/밤, 🌧️ 비/감성, 🎷 재즈, 🌅 노을/저녁, 🍃 힐링/자연
- 설명 필수 포함 항목:
  - 추천 대상
- 태그: 분위기 관련 키워드

## 폴더 구조
```
music_ai_proj/
├── music_file/
│   └── {시리즈명}/
│       ├── 배경이미지.png          ← 사용자가 직접 준비
│       ├── 트랙명_1.mp3            ← Suno AI 생성
│       ├── 트랙명_2.mp3
│       └── {시리즈명}_플레이리스트.mp4  ← 자동 생성
├── scripts/
│   ├── make_video.py              ← 단일 영상 생성
│   ├── make_playlist_video.py     ← 합본 플레이리스트 영상 생성
│   ├── merge_video.py             ← 영상 이어붙이기
│   ├── upload_youtube.py          ← 유튜브 업로드
│   ├── suno_generate.py           ← Suno AI 음악 생성
│   └── full_run.py                ← 전체 자동화 실행
```

## 서버 실행
- 사용자가 "서버 켜줘", "실행해줘", "로컬 켜줘" 등 요청 시 즉시 실행:
  ```
  taskkill /F /IM python.exe 2>/dev/null; python -m uvicorn web.main:app --reload --port 8000 > server.log 2>&1 &
  ```
- 실행 후 `server.log` 확인해서 정상 기동 확인
- 주소: http://localhost:8000

## 규칙
- 영상은 MoviePy로 생성 (캡컷 사용 안 함)
- 배경 이미지는 사용자가 PNG로 직접 준비해서 해당 폴더에 넣어줌
- make_playlist_video.py는 폴더 내 PNG/MP3를 자동 감지하므로 경로만 맞으면 바로 실행 가능
