"""
AIsence Studio — FastAPI 웹 대시보드 백엔드
"""

import os
import sys
import uuid
import json
import asyncio
import shutil
import glob
import random
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AIsence Studio")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 상수 ──────────────────────────────────────────────────────────────────────
UPLOAD_DIR      = PROJECT_ROOT / "images" / "uploads"
MUSIC_FILE_ROOT = PROJECT_ROOT / "music_file"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MUSIC_FILE_ROOT.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ── 인메모리 상태 ──────────────────────────────────────────────────────────────
jobs: dict[str, dict] = {}
sample_events:  dict[str, asyncio.Event] = {}
confirm_events: dict[str, asyncio.Event] = {}


# ── 요청 모델 ──────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    series_name: str
    concept: str
    title: str
    genre: str = "lofi"
    image_path: Optional[str] = None
    extra_tracks: int = 4  # 샘플 승인 후 추가 생성할 배치 수 (1배치=2트랙)


class SeriesRequest(BaseModel):
    series_name: str


class TitleRequest(BaseModel):
    concept: str
    genre: str = "lofi"


# ── 시리즈명 분석 ──────────────────────────────────────────────────────────────
def analyze_series(series_name: str) -> dict:
    name = series_name.lower()

    if any(k in name for k in ['카페', '커피', 'cafe', 'coffee']):
        if any(k in name for k in ['재즈', 'jazz']):
            concept = "조용한 카페, 피아노와 베이스가 잔잔하게 흐르는 재즈 선율"
            genre   = "heal"
        else:
            concept = "따뜻한 카페 분위기, 커피 향과 함께 흐르는 잔잔한 음악"
            genre   = "lofi"
    elif any(k in name for k in ['새벽', 'dawn']):
        concept = "아무도 없는 새벽, 조용하고 감성적인 분위기"
        genre   = "dawn"
    elif any(k in name for k in ['드라이브', 'drive']):
        concept = "창문 열고 달리는 드라이브, 시원하고 감성적인 음악"
        if any(k in name for k in ['밤', '야간', 'night']):   genre = "drive_night"
        elif any(k in name for k in ['여름', 'summer']):       genre = "drive_summer"
        elif any(k in name for k in ['비', 'rain']):           genre = "drive_rain"
        else:                                                   genre = "drive"
    elif any(k in name for k in ['재즈', 'jazz']):
        concept = "느릿느릿 흐르는 재즈, 감성적인 선율과 리듬"
        genre   = "heal"
    elif any(k in name for k in ['로파이', 'lofi', 'lo-fi']):
        concept = "편안하고 감성적인 로파이 비트, 집중하기 좋은 음악"
        genre   = "lofi"
    elif any(k in name for k in ['힐링', '치유', 'healing']):
        concept = "지친 하루를 위로하는 힐링 음악, 편안하고 따뜻한 선율"
        genre   = "heal"
    elif any(k in name for k in ['비', '빗', 'rain']):
        concept = "비 오는 날 듣기 좋은 감성 음악, 빗소리와 함께"
        genre   = "heal"
    elif any(k in name for k in ['밤', '야간', 'night']):
        concept = "깊은 밤, 혼자만의 감성적인 시간"
        genre   = "dawn"
    elif any(k in name for k in ['여름', 'summer']):
        concept = "햇살 가득한 여름, 설레고 청량한 음악"
        genre   = "drive_summer"
    else:
        concept = f"{series_name} 분위기에 맞는 감성적이고 잔잔한 음악"
        genre   = "lofi"

    title = auto_generate_title(concept, genre)
    return {"concept": concept, "genre": genre, "title": title}


# ── 제목 자동 생성 ─────────────────────────────────────────────────────────────
def auto_generate_title(concept: str, genre: str) -> str:
    c = concept.lower()
    if any(k in c for k in ['카페', '커피', 'cafe']):
        emoji = '☕'
        templates = ["카페 창가에 앉아 멍 때리는 오후", "아무 말 없이 커피 한 잔",
                     "그냥 멍 때리고 싶은 오후", "조용한 카페에서 혼자인 시간", "오늘은 그냥 커피나 마시자"]
    elif any(k in c for k in ['새벽', 'dawn']):
        emoji = '🌙'
        templates = ["잠 못 드는 새벽, 혼자만의 시간", "새벽 4시 아무도 없을 때", "아무도 모르는 새벽에"]
    elif any(k in c for k in ['밤', 'night']):
        emoji = '🌙'
        templates = ["오늘 밤은 그냥 이대로", "아무 생각 없이 흘려듣는 밤", "혼자인 밤이 좋은 날"]
    elif any(k in c for k in ['비', 'rain']):
        emoji = '🌧️'
        templates = ["비 오는 날 창문 밖을 바라보며", "빗소리에 기대어", "빗속에서 혼자 앉아있을 때"]
    elif any(k in c for k in ['재즈', 'jazz']):
        emoji = '🎷'
        templates = ["선율이 흐르는 조용한 오후", "재즈가 흐르는 저녁", "느릿느릿 흐르는 재즈"]
    elif any(k in c for k in ['노을', '저녁', 'sunset']):
        emoji = '🌅'
        templates = ["노을이 지는 창가에서", "하루가 끝나가는 시간", "저녁이 되면 듣는 음악"]
    elif any(k in c for k in ['드라이브', 'drive']):
        emoji = '🚗'
        templates = ["아무 생각 없이 달릴 때", "혼자 떠나는 밤 드라이브"]
    elif genre == 'dawn':
        emoji = '🌙'
        templates = ["잠 못 드는 새벽, 혼자만의 시간"]
    elif genre == 'lofi':
        emoji = '🎧'
        templates = ["오늘도 수고한 나를 위한 음악", "집중하고 싶을 때 틀어두는 음악"]
    else:
        emoji = '🍃'
        templates = ["아무것도 하기 싫은 오늘", "그냥 이대로 있고 싶은 날", "오늘 하루도 수고했어"]

    return f"PLAYLIST {emoji} | {random.choice(templates)}"


# ── 설명 생성 ──────────────────────────────────────────────────────────────────
def generate_description(concept: str, genre: str) -> str:
    openers = {
        "lofi":  "🎧 오늘도 수고한 나를 위한 로파이.",
        "heal":  "🍃 지친 하루 끝에 듣는 음악.",
        "bass":  "🌑 무거운 베이스, 혼자만의 시간.",
        "dawn":  "🌙 아무도 없는 새벽, 혼자만의 감성.",
        "drive": "🚗 아무 생각 없이 달릴 때.",
    }
    opener = openers.get(genre, "🎵 당신을 위한 플레이리스트.")
    short  = concept[:40] + ("..." if len(concept) > 40 else "")
    return f"""{opener}

━━━━━━━━━━━━━━━━━━━━━━
🎧 이런 분들께 추천해요
━━━━━━━━━━━━━━━━━━━━━━
✔ {short}
✔ 집중이 필요한 시간
✔ 그냥 흘려듣고 싶을 때

━━━━━━━━━━━━━━━━━━━━━━
🛠 제작 도구
━━━━━━━━━━━━━━━━━━━━━━
Music : Suno AI
Image : Canva
Video : Python (MoviePy)

AI로 만든 감성 음악 채널, aisence
구독 & 좋아요는 큰 힘이 됩니다 🙏"""


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def push_message(job_id: str, msg: str):
    if job_id in jobs:
        jobs[job_id]["messages"].append({"text": msg, "time": datetime.now().strftime("%H:%M:%S")})


# ── Suno 한 배치 생성 (2트랙) ──────────────────────────────────────────────────
async def generate_one_batch(job_id: str, series_dir: Path, track_title: str, concept: str, batch_num: int) -> list[str]:
    loop = asyncio.get_event_loop()
    try:
        from scripts.suno_generate import generate_music, wait_for_result, download_mp3
    except ImportError:
        from suno_generate import generate_music, wait_for_result, download_mp3

    import scripts.suno_generate as sg
    original = sg.OUTPUT_DIR
    sg.OUTPUT_DIR = str(series_dir)

    try:
        task_id = await loop.run_in_executor(None, lambda: generate_music(
            title=track_title, style=concept, lyrics="", instrumental=True))
        push_message(job_id, f"  → 배치 {batch_num} task: {task_id}")
        tracks = await loop.run_in_executor(None, lambda: wait_for_result(task_id))
        paths  = await loop.run_in_executor(None, lambda: download_mp3(tracks, track_title))
    finally:
        sg.OUTPUT_DIR = original

    return paths


# ── 파이프라인 ─────────────────────────────────────────────────────────────────
async def run_pipeline(job_id: str, req: GenerateRequest):
    jobs[job_id]["status"] = "running"
    loop = asyncio.get_event_loop()

    # ── 0. 폴더 생성 ────────────────────────────────────────────────────────────
    series_dir = MUSIC_FILE_ROOT / req.series_name
    series_dir.mkdir(parents=True, exist_ok=True)
    jobs[job_id]["series_dir"] = str(series_dir)
    push_message(job_id, f"📁 폴더 생성: {series_dir.name}/")

    # 업로드 이미지 → 시리즈 폴더로 복사
    image_path = req.image_path
    if image_path and os.path.exists(image_path):
        dest = series_dir / Path(image_path).name
        if str(Path(image_path).resolve()) != str(dest.resolve()):
            shutil.copy2(image_path, dest)
        image_path = str(dest)

    try:
        all_mp3_paths = []

        # ── 1. 샘플 1배치 생성 (2트랙) ──────────────────────────────────────────
        push_message(job_id, "🎵 샘플 생성 중... (Suno AI)")
        sample_title = f"{req.series_name}_sample"
        sample_paths = await generate_one_batch(job_id, series_dir, sample_title, req.concept, 1)

        if not sample_paths:
            raise RuntimeError("샘플 MP3 다운로드 실패")

        # 샘플 승인 루프
        while True:
            jobs[job_id]["sample_path"] = sample_paths[0]
            jobs[job_id]["status"] = "sample_ready"
            push_message(job_id, f"👂 샘플 준비됨 — 들어보고 확인해주세요")

            event = asyncio.Event()
            sample_events[job_id] = event
            await event.wait()

            if jobs[job_id].get("sample_approved"):
                all_mp3_paths.extend(sample_paths)
                push_message(job_id, "✅ 샘플 승인 — 나머지 음악 생성 시작")
                break
            else:
                push_message(job_id, "🔄 샘플 다시 생성 중...")
                jobs[job_id]["status"] = "running"
                sample_paths = await generate_one_batch(job_id, series_dir, sample_title, req.concept, 1)
                if not sample_paths:
                    raise RuntimeError("재생성 실패")

        # ── 2. 나머지 트랙 생성 ──────────────────────────────────────────────────
        push_message(job_id, f"🎵 나머지 음악 생성 중... ({req.extra_tracks}배치 추가)")
        jobs[job_id]["status"] = "running"

        track_titles = [
            f"{req.series_name}_트랙{i+1}" for i in range(req.extra_tracks)
        ]
        for i, t_title in enumerate(track_titles, 2):
            paths = await generate_one_batch(job_id, series_dir, t_title, req.concept, i)
            all_mp3_paths.extend(paths)
            push_message(job_id, f"  → 트랙 {i}/{req.extra_tracks+1} 완료 ({len(paths)}개)")

        push_message(job_id, f"  → 총 {len(all_mp3_paths)}개 MP3 생성 완료")

        # ── 3. 영상 제작 ─────────────────────────────────────────────────────────
        video_path = None
        if not image_path:
            png_files = glob.glob(str(series_dir / "*.png"))
            image_path = png_files[0] if png_files else None

        if image_path:
            push_message(job_id, "🎬 영상 제작 중... (MoviePy)")

            def _make_video():
                from moviepy import AudioFileClip, ImageClip, concatenate_audioclips
                from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
                mp3s = sorted(glob.glob(str(series_dir / "*.mp3")))
                clips = [AudioFileClip(p) for p in mp3s]
                combined = concatenate_audioclips(clips)
                combined = combined.with_effects([AudioFadeIn(2.0), AudioFadeOut(4.0)])
                video = ImageClip(image_path).with_duration(combined.duration).with_audio(combined)
                out = str(series_dir / f"{req.series_name}_플레이리스트.mp4")
                video.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None)
                for c in clips:
                    c.close()
                return out

            video_path = await loop.run_in_executor(None, _make_video)
            push_message(job_id, f"  → 영상 저장: {Path(video_path).name}")
        else:
            push_message(job_id, "  ⚠️ 이미지 없음 — 영상 제작 생략")

        # ── 4. 미리보기 대기 ─────────────────────────────────────────────────────
        if video_path:
            thumbnail_url = None
            if req.image_path and os.path.exists(req.image_path):
                thumbnail_url = f"/uploads/{Path(req.image_path).name}"

            jobs[job_id]["preview"] = {
                "title":         req.title,
                "description":   generate_description(req.concept, req.genre),
                "thumbnail_url": thumbnail_url,
            }
            jobs[job_id]["status"] = "preview_ready"
            push_message(job_id, "👁️ 미리보기 준비됨 — 확인 후 업로드해주세요")

            event = asyncio.Event()
            confirm_events[job_id] = event
            await event.wait()

            if jobs[job_id].get("cancelled"):
                push_message(job_id, "⛔ 업로드 취소됨")
                jobs[job_id]["status"] = "cancelled"
                return

        # ── 5. 유튜브 업로드 ─────────────────────────────────────────────────────
        youtube_url = None
        if video_path and os.path.exists(video_path):
            push_message(job_id, "📤 유튜브 업로드 중...")

            def _upload():
                try:    from scripts.upload_youtube import upload_video
                except: from upload_youtube import upload_video
                vid_id = upload_video(
                    video_path=video_path,
                    title=req.title,
                    genre=req.genre,
                    description=generate_description(req.concept, req.genre),
                    thumbnail_path=image_path if image_path and os.path.exists(image_path) else None,
                )
                return f"https://www.youtube.com/watch?v={vid_id}"

            try:
                youtube_url = await loop.run_in_executor(None, _upload)
                push_message(job_id, "  → 업로드 완료!")
            except Exception as e:
                push_message(job_id, f"  ⚠️ 업로드 실패: {e}")

        jobs[job_id]["status"]      = "done"
        jobs[job_id]["youtube_url"] = youtube_url
        push_message(job_id, f"✅ 완료!{' ' + youtube_url if youtube_url else ''}")

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"]  = str(e)
        push_message(job_id, f"❌ 오류: {e}")


# ── API 라우터 ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    html = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html.read_text(encoding="utf-8"))


@app.post("/analyze-series")
async def analyze_series_api(req: SeriesRequest):
    return analyze_series(req.series_name)


@app.post("/generate-title")
async def generate_title_api(req: TitleRequest):
    return {"title": auto_generate_title(req.concept, req.genre)}


@app.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending", "messages": [], "youtube_url": None,
        "video_path": None, "sample_path": None, "preview": None,
        "error": None, "title": req.title, "series_name": req.series_name,
        "created_at": datetime.now().isoformat(),
    }
    background_tasks.add_task(run_pipeline, job_id, req)
    return {"job_id": job_id}


@app.get("/sample/{job_id}")
async def get_sample(job_id: str):
    """샘플 오디오 파일 스트리밍"""
    if job_id not in jobs:
        raise HTTPException(404)
    path = jobs[job_id].get("sample_path")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "샘플 파일 없음")
    return FileResponse(path, media_type="audio/mpeg")


@app.post("/approve-sample/{job_id}")
async def approve_sample(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404)
    jobs[job_id]["sample_approved"] = True
    if job_id in sample_events:
        sample_events[job_id].set()
    return {"ok": True}


@app.post("/retry-sample/{job_id}")
async def retry_sample(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404)
    jobs[job_id]["sample_approved"] = False
    if job_id in sample_events:
        sample_events[job_id].set()
    return {"ok": True}


@app.post("/confirm-upload/{job_id}")
async def confirm_upload(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404)
    if job_id in confirm_events:
        confirm_events[job_id].set()
    return {"ok": True}


@app.post("/cancel-upload/{job_id}")
async def cancel_upload(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404)
    jobs[job_id]["cancelled"] = True
    if job_id in confirm_events:
        confirm_events[job_id].set()
    return {"ok": True}


@app.get("/progress/{job_id}")
async def progress(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404)

    async def event_generator():
        sent = 0
        while True:
            job      = jobs.get(job_id, {})
            messages = job.get("messages", [])
            while sent < len(messages):
                msg  = messages[sent]
                data = json.dumps({"type": "log", "text": msg["text"], "time": msg["time"]}, ensure_ascii=False)
                yield f"data: {data}\n\n"
                sent += 1

            status = job.get("status", "pending")

            if status == "sample_ready":
                payload = json.dumps({"type": "sample_ready", "job_id": job_id}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                while jobs.get(job_id, {}).get("status") == "sample_ready":
                    await asyncio.sleep(0.5)
                continue

            if status == "preview_ready":
                preview = job.get("preview", {})
                payload = json.dumps({"type": "preview", "job_id": job_id, **preview}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                while jobs.get(job_id, {}).get("status") == "preview_ready":
                    await asyncio.sleep(0.5)
                continue

            if status in ("done", "error", "cancelled"):
                final = json.dumps({
                    "type": "done", "status": status,
                    "youtube_url": job.get("youtube_url"),
                    "error": job.get("error"),
                }, ensure_ascii=False)
                yield f"data: {final}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        raise HTTPException(400, "PNG/JPG/WEBP만 가능합니다.")
    filename = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"image_path": str(dest), "filename": filename}


@app.get("/jobs")
async def list_jobs():
    result = [
        {"job_id": jid, "status": j["status"], "title": j.get("title",""),
         "series_name": j.get("series_name",""), "youtube_url": j.get("youtube_url"),
         "error": j.get("error"), "created_at": j.get("created_at")}
        for jid, j in jobs.items()
    ]
    result.sort(key=lambda x: x.get("created_at",""), reverse=True)
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}
