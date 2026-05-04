"""
Suno API 음악 생성 스크립트
사용법:
  python suno_generate.py --title "벚꽃 아래서" --style "J-pop, acoustic pop" --lyrics "가사내용"
  python suno_generate.py --credits
"""

import os
import re
import time
import argparse
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY  = os.getenv("SUNOAPI_KEY")
BASE_URL = "https://api.sunoapi.org/api/v1"
HEADERS  = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'music_file')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── 1. 음악 생성 요청 ─────────────────────────────────────────────────────────
def generate_music(title: str, style: str, lyrics: str,
                   model: str = "V4_5", instrumental: bool = False,
                   language: str = "English") -> str:
    if instrumental:
        # 반주 모드
        payload = {
            "customMode": True,
            "instrumental": True,
            "model": model,
            "title": title,
            "style": style,
            "prompt": lyrics or style,
            "callBackUrl": "https://webhook.site/aisence-callback",
        }
    elif lyrics:
        # 보컬 + 직접 가사
        payload = {
            "customMode": True,
            "instrumental": False,
            "model": model,
            "title": title,
            "style": style,
            "prompt": lyrics,
            "callBackUrl": "https://webhook.site/aisence-callback",
            "vocalGender": "f",
        }
    else:
        # 보컬 + 자동 가사: customMode=False로 Suno가 자동 생성
        lang_tag = f", lyrics in {language}, {language} only" if language and language.lower() != "korean" else ""
        payload = {
            "customMode": False,
            "instrumental": False,
            "model": model,
            "title": title,
            "prompt": f"{style}{lang_tag}",
            "callBackUrl": "https://webhook.site/aisence-callback",
            "vocalGender": "f",
        }

    print(f"[1/3] mode={'instrumental' if instrumental else 'vocal'} customMode={payload['customMode']} prompt_len={len(payload.get('prompt',''))}")
    import sys; sys.stdout.flush()
    resp = requests.post(f"{BASE_URL}/generate", headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"API 오류: {data}")

    task_id = data["data"]["taskId"]
    print(f"  → taskId: {task_id}")
    return task_id


# ── 2. 상태 폴링 ──────────────────────────────────────────────────────────────
def wait_for_result(task_id: str, timeout: int = 360) -> list[dict]:
    print(f"[2/3] 생성 완료 대기 중 (최대 {timeout}초)...")
    start = time.time()

    while time.time() - start < timeout:
        resp = requests.get(
            f"{BASE_URL}/generate/record-info",
            headers=HEADERS,
            params={"taskId": task_id}
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            raise RuntimeError(f"폴링 오류: {data}")

        status = data["data"].get("status", "")
        elapsed = int(time.time() - start)
        print(f"  상태: {status} ({elapsed}초 경과)")

        if status == "SUCCESS":
            return data["data"]["response"]["sunoData"]
        elif status in ("CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED",
                        "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"):
            raise RuntimeError(f"생성 실패: {status} — {data['data'].get('errorMessage')}")

        time.sleep(15)

    raise TimeoutError(f"타임아웃 ({timeout}초 초과)")


# ── 3. mp3 다운로드 ───────────────────────────────────────────────────────────
def _sanitize(name: str) -> str:
    """파일명으로 쓸 수 없는 문자 제거"""
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()[:80]


def download_mp3(tracks: list[dict], title: str) -> list[str]:
    print(f"[3/3] mp3 다운로드 중... ({len(tracks)}개 트랙)")
    paths = []

    for i, track in enumerate(tracks):
        audio_url = track.get("audioUrl") or track.get("audio_url")
        if not audio_url:
            print(f"  ✗ {i+1}번 트랙 audio_url 없음")
            continue

        suno_title = _sanitize(track.get("title", "").strip())
        if suno_title:
            filename = f"{suno_title}.mp3"
        else:
            suffix = f"_{i+1}" if len(tracks) > 1 else ""
            filename = f"{title}{suffix}.mp3"

        filepath = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(filepath):
            base = filename[:-4]
            filename = f"{base}_{i+1}.mp3"
            filepath = os.path.join(OUTPUT_DIR, filename)

        r = requests.get(audio_url, stream=True, timeout=60)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        duration = track.get("duration", 0)
        print(f"  [OK] {filename} ({duration:.0f}sec)")
        paths.append(filepath)

    return paths


# ── 크레딧 확인 ───────────────────────────────────────────────────────────────
def check_credits() -> None:
    resp = requests.get(f"{BASE_URL}/generate/credit", headers=HEADERS)
    resp.raise_for_status()
    print(f"크레딧 잔액: {resp.json()}")


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Suno API 음악 생성")
    parser.add_argument("--title",        default="untitled", help="곡 제목")
    parser.add_argument("--style",        default="",         help="음악 스타일")
    parser.add_argument("--lyrics",       default="",         help="가사")
    parser.add_argument("--model",        default="V4_5",
                        choices=["V4", "V4_5", "V4_5PLUS", "V4_5ALL", "V5"],
                        help="Suno 모델 버전")
    parser.add_argument("--instrumental", action="store_true", help="반주만 생성")
    parser.add_argument("--output",       default=None,        help="저장 폴더 경로")
    parser.add_argument("--credits",      action="store_true", help="크레딧 잔액 확인")
    args = parser.parse_args()

    if not API_KEY:
        print("오류: .env 파일에 SUNOAPI_KEY를 설정하세요.")
        return

    if args.credits:
        check_credits()
        return

    if args.output:
        global OUTPUT_DIR
        OUTPUT_DIR = args.output
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    task_id = generate_music(args.title, args.style, args.lyrics,
                              args.model, args.instrumental)
    tracks  = wait_for_result(task_id)
    paths   = download_mp3(tracks, args.title)

    print(f"\n완료! 저장된 파일:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
