# YouTube API 설정 가이드

자동 업로드를 위해 최초 1회만 설정하면 됩니다.

---

## 1단계 — Google Cloud Console 설정

1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성 (이름: `aisence` 등 자유)
3. 왼쪽 메뉴 → **API 및 서비스** → **라이브러리**
4. `YouTube Data API v3` 검색 → **사용 설정**

---

## 2단계 — OAuth 클라이언트 ID 발급

1. **API 및 서비스** → **사용자 인증 정보**
2. **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID**
3. 애플리케이션 유형: **데스크톱 앱**
4. 이름: `aisence-uploader`
5. **만들기** 클릭
6. **JSON 다운로드** 클릭
7. 다운로드된 파일을 **`scripts/client_secrets.json`** 으로 저장

---

## 3단계 — 최초 인증 (1회만)

```bash
cd scripts
python upload_youtube.py --video test.mp4 --title "테스트"
```

- 브라우저가 자동으로 열립니다
- Google 계정 로그인 → 권한 허용
- 완료되면 `token.pickle` 파일 생성됨 (이후 자동 인증)

---

## 사용 예시

### 영상만 만들기
```bash
cd scripts
python make_video.py --image ../images/LOFI-20260315-001.png \
                     --audio ../audio/LOFI-20260315-001.mp3
```

### 업로드만 하기 (영상 파일 이미 있을 때)
```bash
python upload_youtube.py \
  --video ../output/LOFI-20260315-001_final.mp4 \
  --title "새벽 감성 lofi ~ 잠 못 이루는 밤에 🎵 aisence" \
  --genre lofi \
  --schedule "2026-03-21T18:00:00+09:00"
```

### 한 번에 (영상 생성 + 업로드)
```bash
python run.py \
  --image ../images/LOFI-20260315-001.png \
  --audio ../audio/LOFI-20260315-001.mp3 \
  --title "새벽 감성 lofi ~ 잠 못 이루는 밤에 🎵 aisence" \
  --genre lofi \
  --schedule "2026-03-21T18:00:00+09:00"
```

---

## 예약 업로드 시간 형식

```
"YYYY-MM-DDTHH:MM:SS+09:00"

예시 (금요일 오후 6시):
"2026-03-20T18:00:00+09:00"
```
