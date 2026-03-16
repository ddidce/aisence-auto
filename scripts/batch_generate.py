"""
카페 공부 시리즈 10곡 일괄 생성 스크립트
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

API_KEY  = os.getenv("SUNOAPI_KEY")
BASE_URL = "https://api.sunoapi.org/api/v1"
HEADERS  = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'music_file', '카페공부시리즈')
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_STYLE = "lo-fi hip hop, chillhop, cafe music, study beats, piano, acoustic guitar, soft drums, warm bass, cozy, calm, focused, relaxing, instrumental"

SONGS = [
    {"title": "오늘도 카페에서",   "style": BASE_STYLE + ", morning cafe, bright, BPM 85"},
    {"title": "창가 자리",         "style": BASE_STYLE + ", gentle, sunlight, warm, BPM 80"},
    {"title": "집중하는 오후",     "style": BASE_STYLE + ", deep focus, steady beat, BPM 90"},
    {"title": "따뜻한 라떼",       "style": BASE_STYLE + ", smooth, cozy, soft jazz, BPM 78"},
    {"title": "빗소리와 함께",     "style": BASE_STYLE + ", rain sounds, ambient, melancholic, BPM 75"},
    {"title": "노트 한 장",        "style": BASE_STYLE + ", light, simple, minimal piano, BPM 82"},
    {"title": "마감 전날 밤",      "style": BASE_STYLE + ", late night, mellow, atmospheric, BPM 88"},
    {"title": "잠깐 쉬어가",       "style": BASE_STYLE + ", breathy, relaxed, soft, BPM 72"},
    {"title": "해질녘 카페",       "style": BASE_STYLE + ", sunset, nostalgic, warm synth, BPM 83"},
    {"title": "집에 가기 전에",    "style": BASE_STYLE + ", ending, peaceful, gentle close, BPM 76"},
]


def generate(title, style):
    payload = {
        "customMode": True,
        "instrumental": True,
        "model": "V4_5",
        "title": title,
        "style": style,
        "prompt": "",
        "vocalGender": "f",
        "callBackUrl": "https://webhook.site/aisence-callback",
    }
    resp = requests.post(f"{BASE_URL}/generate", headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"생성 오류: {data}")
    return data["data"]["taskId"]


def wait(task_id, timeout=360):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{BASE_URL}/generate/record-info", headers=HEADERS, params={"taskId": task_id})
        resp.raise_for_status()
        data = resp.json()
        status = data["data"].get("status", "")
        elapsed = int(time.time() - start)
        print(f"    상태: {status} ({elapsed}초)")

        if status == "SUCCESS":
            return data["data"]["response"]["sunoData"]
        elif status in ("CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"):
            raise RuntimeError(f"실패: {status}")

        time.sleep(15)
    raise TimeoutError("타임아웃")


def download(tracks, title):
    paths = []
    for i, track in enumerate(tracks):
        url = track.get("audioUrl") or track.get("audio_url")
        if not url:
            continue
        suffix = f"_{i+1}" if len(tracks) > 1 else ""
        filename = f"{title}{suffix}.mp3"
        filepath = os.path.join(OUTPUT_DIR, filename)

        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        duration = track.get("duration", 0)
        print(f"    [OK] {filename} ({duration:.0f}sec)")
        paths.append(filepath)
    return paths


def check_credits():
    resp = requests.get(f"{BASE_URL}/generate/credit", headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("data", 0)


def main():
    print(f"시작 크레딧: {check_credits()}")
    print(f"저장 폴더: {OUTPUT_DIR}\n")

    for idx, song in enumerate(SONGS, 1):
        title = song["title"]
        style = song["style"]
        print(f"[{idx}/10] {title}")

        try:
            task_id = generate(title, style)
            print(f"  taskId: {task_id}")
            tracks = wait(task_id)
            download(tracks, title)
        except Exception as e:
            print(f"  오류: {e}")

        print()
        if idx < len(SONGS):
            time.sleep(5)

    print(f"완료! 남은 크레딧: {check_credits()}")


if __name__ == "__main__":
    main()
