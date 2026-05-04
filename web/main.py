"""
AIsence Studio — FastAPI 웹 대시보드 백엔드
"""

import os
import re
import sys
import uuid
import json
import pickle
import asyncio
import shutil
import glob
import random
import requests as http_requests
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

# ── 장르별 Suno 스타일 매핑 (영어 키워드로 음색을 완전히 다르게) ─────────────────
SUNO_STYLE_MAP: dict[str, str] = {
    "lofi":          "lo-fi hip hop, vinyl crackle, mellow jazzy chords, 70 BPM, dusty boom-bap drums, Rhodes piano, warm tape hiss, chill study beats",
    "heal":          "ambient healing, soft fingerpicked guitar, gentle strings, nature ambience, 58 BPM, spa music, airy pads, peaceful, no drums",
    "bass":          "dark bass music, deep sub-bass, moody synth pads, 85 BPM, underground electronic, dark atmospheric, minor key",
    "dawn":          "late-night lo-fi, melancholic synth arpeggios, 65 BPM, 3am city lights, minimal sparse beats, introspective, slow tempo",
    "drive":         "synthwave, cinematic highway drive, 110 BPM, electric guitar lead, pulsing bass, open-road energy, 80s retro synth",
    "drive_summer":  "summer indie pop, bright upbeat acoustic, 120 BPM, carefree, beach vibes, jangling guitar, warm sunny production",
    "drive_night":   "night drive synthwave, neon city, 100 BPM, dark pulsing synth, reverb electric guitar, moody cinematic, nocturnal",
    "drive_hype":    "hype EDM, festival drop, 128 BPM, heavy kick, massive synth lead, adrenaline rush, energetic buildup",
    "drive_chill":   "chill indie road trip, mellow acoustic, 90 BPM, laid-back groove, sunset vibe, fingerpicked guitar, relaxed",
    "drive_rain":    "rainy day jazz, melancholic piano, 75 BPM, soft rainfall ambience, bossa nova sway, minor chord progression, reflective",
    "kpop":          "K-pop dance, punchy synth bass, 130 BPM, powerful female group vocal, tight production, catchy hook, SM Entertainment style",
    "aespa":         "K-pop cyberpunk, heavy EDM drop, glitchy synth distortion, 135 BPM, dark futuristic beat, intense bridge, aespa Next Level style",
    "shinee":        "K-pop funk pop, neo soul groove, punchy synth bass, 125 BPM, sophisticated R&B, tight rhythmic hook, SHINee Sherlock style",
    "snsd":          "K-pop bubbly dance pop, cheerful synth hook, 128 BPM, bright girl group energy, clean soprano vocal, Girls Generation Gee style",
    "cafe":          "cafe background, bossa nova guitar, warm upright bass, 80 BPM, afternoon sunlight, relaxed jazz-pop, light percussion",
    "cafe_jazz":     "cafe jazz, acoustic piano trio, brushed snare, 85 BPM, upright bass walk, intimate warm atmosphere, classic jazz swing",
    "cinematic":     "cinematic orchestral, sweeping strings, 80 BPM, emotional film score, dramatic build, full orchestra, epic and powerful",
    "cinematic_jazz":"film noir jazz, muted trumpet, moody piano, 75 BPM, saxophone melody, cinematic atmosphere, sophisticated noir",
    "jazz":          "acoustic jazz, bebop piano, upright bass, brushed drums, 100 BPM, improvisation, classic jazz club, swinging",
    "piano":         "solo classical piano, expressive dynamics, 70 BPM, intimate concert hall, Chopin-influenced, no other instruments",
    "acoustic":      "acoustic guitar fingerpicking, 80 BPM, warm indie folk, singer-songwriter, organic, natural room sound",
    "spring":        "spring acoustic pop, bright cheerful, 95 BPM, acoustic guitar, birds chirping, fresh blossom, light and airy",
    "autumn":        "autumn folk, melancholic cello, 75 BPM, fingerpicked guitar, leaf-fall nostalgia, minor key, wistful",
    "winter":        "winter ambient piano, sparse crystalline, 65 BPM, cold breath atmosphere, snowfall imagery, quiet peaceful",
    "rain":          "rainy day ambient, piano melody, 70 BPM, soft rainfall texture, introspective, grey sky mood, cozy indoors",
    "sleep":         "sleep music, deep ambient drone, 55 BPM, binaural soft pads, no melody, pure tone, peaceful lullaby",
    "study":         "focus study music, minimal piano, 75 BPM, background ambient, no lyrics, no drums, clean concentration music",
    "meditation":    "meditation, Tibetan singing bowls, ambient drone, 50 BPM, breathing rhythm, zen, spiritual, no melody",
    "ambient":       "pure ambient electronic, atmospheric pads, 60 BPM, spacious reverb, drone texture, minimalist, Brian Eno style",
    "sunset":        "sunset soft rock, warm acoustic guitar, 85 BPM, golden hour nostalgia, emotional, Americana influenced",
    "travel":        "travel world folk, uplifting acoustic, 95 BPM, global instruments, sense of adventure, open sky",
    "walk":          "morning walk indie pop, light and bouncy, 100 BPM, acoustic guitar strum, cheerful, fresh air energy",
    "citypop":       "city pop, 80s Japanese funk, smooth bass groove, bright synth chord stab, 110 BPM, Mariya Takeuchi style, sophisticated",
    "chillwave":     "chillwave, dreamy reverb synth, 85 BPM, hazy nostalgic, tape-saturated, summer memories, Washed Out style",
    "swing":         "swing jazz big band, brass section, 140 BPM, walking bass, tight drums, upbeat 1940s dance hall energy",
    "latin":         "bossa nova latin jazz, nylon guitar, 105 BPM, clave rhythm, warm tropical, Brazilian influenced, samba groove",
    "reggae":        "roots reggae, offbeat skank guitar, deep bass groove, 80 BPM, Jamaican rhythm, relaxed, laid-back",
    "disco":         "disco funk, four-on-the-floor kick, 120 BPM, string section stab, wah guitar, 70s groove, danceable",
    "rock":          "indie rock, distorted guitar riff, 120 BPM, live drums, bass, energetic, alternative rock, gritty",
    "electronic":    "electronic dance, progressive synth, 125 BPM, punchy kick, layered pads, modern club production",
    "rnb":           "neo soul R&B, warm soulful, 85 BPM, smooth bass, Rhodes chord, groove pocket, intimate vocal",
    "newage":        "new age piano, 65 BPM, ambient pads, peaceful spiritual, gentle, George Winston style, no percussion",
    "ballad":        "emotional pop ballad, piano and strings, 70 BPM, heartfelt, slow build, orchestral swell, tender",
    "lullaby":       "gentle lullaby, music box melody, 55 BPM, soft plucked strings, soothing, nursery, tender and quiet",
    "easylistening": "easy listening, smooth jazz guitar, 85 BPM, light background, pleasant, hotel lobby, mellow saxophone",
}

# ── 인메모리 상태 ──────────────────────────────────────────────────────────────
jobs: dict[str, dict] = {}
sample_events:  dict[str, asyncio.Event] = {}
confirm_events: dict[str, asyncio.Event] = {}
order_events:   dict[str, asyncio.Event] = {}


# ── 요청 모델 ──────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    series_name: str
    concept: str
    title: str
    genre: str = "lofi"
    image_path: Optional[str] = None
    extra_tracks: int = 19  # 샘플 승인 후 추가 생성할 배치 수 (1배치=1트랙)
    instrumental: bool = True
    lyrics: str = ""
    language: str = "English"


class SeriesRequest(BaseModel):
    series_name: str


class TitleRequest(BaseModel):
    concept: str
    genre: str = "lofi"


class TrackOrderRequest(BaseModel):
    ordered_paths: list[str]


class ApproveRequest(BaseModel):
    selected_index: int = 0
    next_lyrics: str = ""


# ── 시리즈명 분석 ──────────────────────────────────────────────────────────────
def analyze_series(series_name: str) -> dict:
    name = series_name.lower()

    if any(k in name for k in ['카페', '커피', 'cafe', 'coffee']):
        if any(k in name for k in ['재즈', 'jazz']):
            concept = "조용한 카페, 피아노와 베이스가 잔잔하게 흐르는 재즈 선율"
            genre   = "cafe_jazz"
        else:
            concept = "따뜻한 카페 분위기, 커피 향과 함께 흐르는 잔잔한 음악"
            genre   = "cafe"
    elif any(k in name for k in ['시네마틱', 'cinematic', '영화']):
        if any(k in name for k in ['재즈', 'jazz', '로파이', 'lofi']):
            concept = "영화 한 장면 같은 감성, 재즈와 로파이가 섞인 시네마틱 사운드"
            genre   = "cinematic_jazz"
        else:
            concept = "웅장하고 감성적인 시네마틱 사운드, 영화 OST 느낌의 음악"
            genre   = "cinematic"
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
        genre   = "jazz"
    elif any(k in name for k in ['로파이', 'lofi', 'lo-fi']):
        concept = "편안하고 감성적인 로파이 비트, 집중하기 좋은 음악"
        genre   = "lofi"
    elif any(k in name for k in ['힐링', '치유', 'healing']):
        concept = "지친 하루를 위로하는 힐링 음악, 편안하고 따뜻한 선율"
        genre   = "heal"
    elif any(k in name for k in ['공부', '집중', 'study', 'focus']):
        concept = "집중력을 높여주는 잔잔한 배경음악, 방해받지 않는 소리"
        genre   = "study"
    elif any(k in name for k in ['수면', '잠', 'sleep', '자장가']):
        concept = "잠들기 좋은 편안하고 나른한 음악, 긴장을 풀어주는 선율"
        genre   = "sleep"
    elif any(k in name for k in ['비', '빗', 'rain']):
        concept = "비 오는 날 듣기 좋은 감성 음악, 빗소리와 함께"
        genre   = "rain"
    elif any(k in name for k in ['밤', '야간', 'night']):
        concept = "깊은 밤, 혼자만의 감성적인 시간"
        genre   = "dawn"
    elif any(k in name for k in ['여름', 'summer']):
        concept = "햇살 가득한 여름, 설레고 청량한 음악"
        genre   = "drive_summer"
    elif any(k in name for k in ['봄', 'spring', '벚꽃']):
        concept = "따뜻한 봄날, 꽃이 피는 계절의 설레는 감성"
        genre   = "spring"
    elif any(k in name for k in ['가을', 'autumn', 'fall']):
        concept = "낙엽 지는 가을, 쓸쓸하고 감성적인 분위기"
        genre   = "autumn"
    elif any(k in name for k in ['겨울', 'winter', '눈', 'snow']):
        concept = "조용한 겨울날, 차갑고 고요한 감성의 음악"
        genre   = "winter"
    elif any(k in name for k in ['피아노', 'piano']):
        concept = "감성적인 피아노 선율, 조용하고 아름다운 음악"
        genre   = "piano"
    elif any(k in name for k in ['기타', 'guitar', '어쿠스틱', 'acoustic']):
        concept = "따뜻한 기타 선율, 감성적이고 편안한 어쿠스틱 사운드"
        genre   = "acoustic"
    elif any(k in name for k in ['산책', 'walk', '걷기']):
        concept = "가볍게 걷고 싶은 날, 상쾌하고 경쾌한 산책 음악"
        genre   = "walk"
    elif any(k in name for k in ['독서', '책', 'book', 'reading']):
        concept = "책 읽을 때 틀어두는 방해받지 않는 잔잔한 음악"
        genre   = "study"
    elif any(k in name for k in ['노을', '저녁', 'sunset', '황혼']):
        concept = "하루가 저물어가는 노을 빛 감성, 따뜻하고 서정적인 음악"
        genre   = "sunset"
    elif any(k in name for k in ['여행', 'travel', '바다', 'ocean', 'sea']):
        concept = "어딘가로 떠나고 싶은 감성, 설레고 자유로운 여행의 음악"
        genre   = "travel"
    elif any(k in name for k in ['명상', '요가', 'meditation', 'yoga', '마음']):
        concept = "마음을 비우는 시간, 명상과 호흡에 어울리는 고요한 음악"
        genre   = "meditation"
    elif any(k in name for k in ['앰비언트', 'ambient', '공간']):
        concept = "공간을 채우는 아름다운 앰비언트 사운드, 몽환적이고 넓은 느낌"
        genre   = "ambient"
    elif any(k in name for k in ['에스파', 'aespa']):
        concept = "K-pop, cyberpunk synth pop, heavy EDM drop, dark futuristic beat, glitchy distortion, powerful female vocal, 135 BPM, intense chorus, aespa Next Level style, SM Entertainment"
        genre   = "aespa"
    elif any(k in name for k in ['샤이니', 'shinee']):
        concept = "K-pop, funky dance pop, neo soul groove, sophisticated R&B, punchy synth bass, tight rhythm, catchy hook, upbeat 125 BPM, SHINee Sherlock style, polished SM production"
        genre   = "shinee"
    elif any(k in name for k in ['소녀시대', 'snsd', 'girls generation', 'girlsgeneration']):
        concept = "K-pop, bright bubbly dance pop, cheerful synth hook, energetic chorus, clean girl group vocal, catchy upbeat 128 BPM, Girls Generation Gee style, fun and lively SM pop"
        genre   = "snsd"
    elif any(k in name for k in ['sm mix', 'sm_mix', 'sm스타일', 'kpop mix', '케이팝']):
        concept = "K-pop, high energy dance pop, heavy synth drop, powerful female vocal, catchy hook, upbeat 130 BPM, aespa cyberpunk EDM meets SHINee funk pop meets Girls Generation bright pop, SM Entertainment style, polished production, dynamic chorus"
        genre   = "kpop"
    elif any(k in name for k in ['시티팝', 'city pop', 'citypop']):
        concept = "80년대 일본 시티팝 감성, 세련되고 도시적인 사운드"
        genre   = "citypop"
    elif any(k in name for k in ['칠웨이브', 'chillwave', 'chill wave']):
        concept = "몽환적이고 나른한 칠웨이브 사운드, 여름 추억 감성"
        genre   = "chillwave"
    elif any(k in name for k in ['스윙', 'swing', '빅밴드', 'big band']):
        concept = "신나는 스윙 재즈, 빅밴드 에너지"
        genre   = "swing"
    elif any(k in name for k in ['라틴', 'latin', '보사노바', 'bossa nova']):
        concept = "따뜻한 라틴 재즈, 보사노바 리듬"
        genre   = "latin"
    elif any(k in name for k in ['레게', 'reggae']):
        concept = "편안한 레게 리듬, 자메이카 바이브"
        genre   = "reggae"
    elif any(k in name for k in ['디스코', 'disco']):
        concept = "70년대 디스코 펑크, 신나는 댄스 비트"
        genre   = "disco"
    elif any(k in name for k in ['록', 'rock', '인디록', 'indie rock']):
        concept = "에너지 넘치는 인디록 사운드"
        genre   = "rock"
    elif any(k in name for k in ['r&b', 'rnb', 'r and b', '알앤비']):
        concept = "따뜻하고 감성적인 R&B 소울"
        genre   = "rnb"
    elif any(k in name for k in ['뉴에이지', 'new age', 'newage']):
        concept = "영적이고 고요한 뉴에이지 음악"
        genre   = "newage"
    elif any(k in name for k in ['발라드', 'ballad']):
        concept = "감성적인 팝 발라드, 피아노와 현악"
        genre   = "ballad"
    elif any(k in name for k in ['이지리스닝', 'easy listening', 'easylistening']):
        concept = "편안한 이지리스닝, 가벼운 배경음악"
        genre   = "easylistening"
    elif any(k in name for k in ['자장가', 'lullaby']):
        concept = "부드러운 자장가, 잠들기 좋은 음악"
        genre   = "lullaby"
    elif any(k in name for k in ['명상', 'meditation', '요가', 'yoga']):
        concept = "고요한 명상 음악, 마음을 비우는 소리"
        genre   = "meditation"
    elif any(k in name for k in ['전자음악', 'electronic', 'edm']):
        concept = "모던 전자음악, 댄스 일렉트로닉"
        genre   = "electronic"
    else:
        concept = f"{series_name} 분위기에 맞는 감성적이고 잔잔한 음악"
        genre   = "lofi"

    title = auto_generate_title(concept, genre)
    return {"concept": concept, "genre": genre, "title": title}


# ── 제목 자동 생성 ─────────────────────────────────────────────────────────────
def auto_generate_title(concept: str, genre: str) -> str:
    c = concept.lower()

    if any(k in c for k in ['시네마틱', 'cinematic', '영화']):
        emoji = '🎬'
        templates = [
            "영화 같은 오늘 하루", "어느 영화의 엔딩 크레딧처럼",
            "혼자 보는 영화, 혼자 듣는 음악", "아무도 없는 극장에서",
            "내 인생의 OST", "감성 영화 한 편 같은 오후",
            "마치 영화 속 한 장면처럼", "혼자만의 엔딩씬",
            "스크린 밖으로 흘러나오는 선율", "오늘의 배경음악은 내가 정한다",
        ]
    elif any(k in c for k in ['카페', '커피', 'cafe']):
        emoji = '☕'
        templates = [
            "카페 창가에 앉아 멍 때리는 오후", "아무 말 없이 커피 한 잔",
            "그냥 멍 때리고 싶은 오후", "조용한 카페에서 혼자인 시간",
            "오늘은 그냥 커피나 마시자", "카페에서 혼자 앉아있을 때",
            "커피 식어가는 줄도 모르고", "오후 2시, 아무것도 안 해도 되는 시간",
            "창가 자리에 앉아 아무 생각 없이", "카페인이 필요한 오후",
        ]
    elif any(k in c for k in ['새벽']):
        emoji = '🌙'
        templates = [
            "잠 못 드는 새벽, 혼자만의 시간", "새벽 4시 아무도 없을 때",
            "아무도 모르는 새벽에", "새벽에 혼자 깨어있을 때",
            "새벽 3시, 세상이 잠든 시간", "아무도 없는 새벽 거리",
            "새벽에만 들을 수 있는 음악", "모두가 잠든 새벽에 혼자",
            "새벽 감성, 나만 아는 시간", "창문 너머 새벽빛이 들어올 때",
        ]
    elif any(k in c for k in ['수면', '잠', 'sleep']):
        emoji = '😴'
        templates = [
            "잠들기 전 5분", "눈이 감기는 밤에 틀어두는 음악",
            "오늘 하루도 수고했어, 이제 자도 돼", "천천히 눈을 감아도 좋아",
            "잠드는 순간까지 함께", "침대에 누워 멍하니 천장 볼 때",
            "이 음악 들으면 잠들어", "오늘 밤은 빨리 잠들고 싶어",
            "꿈속으로 데려다 줄 음악", "밤이 되면 켜두는 음악",
        ]
    elif any(k in c for k in ['공부', '집중', 'study', 'focus', '독서', '책']):
        emoji = '📚'
        templates = [
            "집중이 필요한 순간에", "공부할 때 틀어두는 음악",
            "방해받지 않고 집중하고 싶을 때", "머리를 맑게 해주는 음악",
            "오늘도 책상 앞에 앉아", "집중력이 올라가는 플레이리스트",
            "시험 전날 밤 틀어두는 음악", "생각을 정리하고 싶을 때",
            "공부도 되고 힐링도 되는 음악", "책상 위 커피 한 잔과 함께",
        ]
    elif any(k in c for k in ['밤', 'night']):
        emoji = '🌙'
        templates = [
            "오늘 밤은 그냥 이대로", "아무 생각 없이 흘려듣는 밤",
            "혼자인 밤이 좋은 날", "밤이 되어야 들리는 음악",
            "오늘 밤도 혼자인 게 좋아", "밤 11시, 하루를 정리하는 시간",
            "이 밤이 끝나지 않았으면", "혼자 있는 밤이 제일 편해",
            "아무도 없는 밤, 음악만 있으면 돼", "오늘 밤만큼은 아무 생각 하지 말자",
        ]
    elif any(k in c for k in ['비', 'rain']):
        emoji = '🌧️'
        templates = [
            "비 오는 날 창문 밖을 바라보며", "빗소리에 기대어",
            "빗속에서 혼자 앉아있을 때", "비가 오면 생각나는 음악",
            "우산 없이 맞아도 좋을 것 같은 날", "빗소리와 함께 흘러가는 오후",
            "비 오는 날엔 이 음악이 딱이야", "창문에 빗방울이 맺힐 때",
            "오늘 하루 비랑 같이 흘려보내기", "비 오는 날만의 감성",
        ]
    elif any(k in c for k in ['재즈', 'jazz']):
        emoji = '🎷'
        templates = [
            "선율이 흐르는 조용한 오후", "재즈가 흐르는 저녁",
            "느릿느릿 흐르는 재즈", "재즈바에서 혼자 마시는 한 잔",
            "오늘 저녁은 재즈가 필요해", "빈티지 재즈, 오래된 감성",
            "LP판이 돌아가는 오후", "재즈가 흐르는 카페에 앉아서",
            "느리게 흘러가도 괜찮은 하루", "저녁 7시, 재즈가 필요한 순간",
        ]
    elif any(k in c for k in ['노을', '저녁', 'sunset', '황혼']):
        emoji = '🌅'
        templates = [
            "노을이 지는 창가에서", "하루가 끝나가는 시간",
            "저녁이 되면 듣는 음악", "노을 빛이 방 안으로 들어올 때",
            "오늘 하루도 이렇게 저물어간다", "붉게 물드는 저녁 하늘 아래",
            "퇴근길 노을을 보며", "하루의 마지막을 감성으로 채우는 시간",
            "저녁 6시, 하루가 마무리되는 느낌", "노을 지는 시간만큼은 멈추고 싶어",
        ]
    elif any(k in c for k in ['드라이브', 'drive']):
        emoji = '🚗'
        templates = [
            "아무 생각 없이 달릴 때", "혼자 떠나는 밤 드라이브",
            "목적지 없이 그냥 달리는 중", "창문 열고 달리고 싶은 날",
            "도로 위에서 혼자인 시간", "드라이브하기 딱 좋은 날씨",
            "아무 데나 가도 좋을 것 같은 날", "혼자 드라이브할 때 트는 음악",
            "속도보다 감성이 중요한 드라이브", "달리다 보면 뭔가 해결될 것 같아",
        ]
    elif any(k in c for k in ['봄', 'spring', '벚꽃']):
        emoji = '🌸'
        templates = [
            "벚꽃이 피는 날에", "봄이 오면 생각나는 음악",
            "따뜻한 봄바람 같은 플레이리스트", "봄날 오후의 설렘",
            "꽃잎이 날리는 거리에서", "봄이라서 괜히 설레는 날",
            "이 계절이 영원했으면 좋겠다", "봄 냄새 나는 오후",
            "따뜻해진 날씨에 기분도 따뜻해지는 음악", "벚꽃 아래서 멍 때리기",
        ]
    elif any(k in c for k in ['가을', 'autumn', 'fall']):
        emoji = '🍂'
        templates = [
            "낙엽이 지는 계절에", "가을이 되면 생각나는 음악",
            "쓸쓸하지만 좋아, 가을 감성", "낙엽 밟으며 걷고 싶은 날",
            "가을 하늘 아래 혼자인 시간", "이 계절이 좀 더 길었으면",
            "가을비와 함께 듣는 플레이리스트", "낙엽처럼 흘러가는 감성",
            "가을 감성이 폭발하는 계절", "텅 빈 공원 벤치에 앉아서",
        ]
    elif any(k in c for k in ['겨울', 'winter', '눈', 'snow']):
        emoji = '❄️'
        templates = [
            "눈 오는 날 창문 밖을 보며", "겨울 감성 가득한 플레이리스트",
            "차갑지만 따뜻한 겨울 음악", "이불 속에서 듣는 겨울 음악",
            "첫눈이 오는 날에", "겨울밤, 따뜻한 차 한 잔과 함께",
            "눈 내리는 조용한 밤", "겨울에만 들을 수 있는 감성",
            "차가운 공기와 따뜻한 선율", "올 겨울도 이 음악과 함께",
        ]
    elif any(k in c for k in ['피아노', 'piano']):
        emoji = '🎹'
        templates = [
            "피아노 선율이 흐르는 오후", "감성 피아노로 채우는 하루",
            "아무 말 없이 피아노만", "피아노 소리에 기대는 저녁",
            "건반 위를 흐르는 감성", "피아노가 대신 말해주는 것 같아",
            "조용한 방에 피아노 소리만", "피아노 한 곡으로 충분한 오후",
            "감정을 건반에 담은 음악", "말보다 피아노가 더 잘 표현해줄 때",
        ]
    elif any(k in c for k in ['기타', 'guitar', '어쿠스틱', 'acoustic']):
        emoji = '🎸'
        templates = [
            "어쿠스틱 기타 한 줄에 담긴 감성", "따뜻한 기타 소리가 필요한 날",
            "기타 하나면 충분한 오후", "어쿠스틱 감성 가득한 플레이리스트",
            "통기타 소리가 그리운 날", "감성 기타 선율에 기대는 저녁",
            "아무것도 없어도 기타 하나면 돼", "기타 소리가 마음을 건드릴 때",
            "줄 하나하나에 담긴 감정", "어쿠스틱 기타로 채우는 조용한 오후",
        ]
    elif any(k in c for k in ['산책', 'walk', '걷기']):
        emoji = '🚶'
        templates = [
            "아무 생각 없이 걷고 싶은 날", "혼자 걷는 게 좋은 오후",
            "이어폰 꽂고 동네 한 바퀴", "목적 없이 걷는 산책길",
            "걷다 보면 생각이 정리되는 음악", "느리게 걷고 싶은 날의 플레이리스트",
            "혼자 걸을 때 듣는 음악", "발걸음과 리듬이 맞아떨어질 때",
            "산책하기 딱 좋은 날씨에", "걷는 것만으로도 충분한 오후",
        ]
    elif any(k in c for k in ['여행', 'travel', '바다', 'ocean', 'sea']):
        emoji = '✈️'
        templates = [
            "어딘가로 떠나고 싶은 날", "짐 싸고 그냥 떠나버리고 싶어",
            "여행지에서 혼자 듣는 음악", "바다가 보고 싶어지는 플레이리스트",
            "창밖 풍경과 함께 흘러가는 음악", "비행기 안에서 창밖 바라보며",
            "혼자 떠나는 여행, 혼자 듣는 음악", "새로운 곳에서 새로운 감성으로",
            "바다 냄새가 나는 것 같은 음악", "떠나지 않아도 여행 기분 나는 플레이리스트",
        ]
    elif any(k in c for k in ['명상', '요가', 'meditation', 'yoga', '마음']):
        emoji = '🧘'
        templates = [
            "마음을 비우고 싶을 때", "아무 생각 없이 숨만 쉬어도 되는 음악",
            "고요함이 필요한 순간", "명상할 때 틀어두는 플레이리스트",
            "잠깐 멈추고 나를 돌아볼 때", "마음이 복잡할 때 듣는 음악",
            "호흡과 함께 흘러가는 선율", "아무것도 안 해도 괜찮은 시간",
            "내 안의 고요함을 찾아서", "바쁜 하루 속 잠깐의 쉼표",
        ]
    elif any(k in c for k in ['앰비언트', 'ambient', '공간']):
        emoji = '🌌'
        templates = [
            "공간을 채우는 음악", "아무도 없는 공간에 흐르는 소리",
            "멍하니 천장 바라볼 때", "소리로 채우는 고요한 공간",
            "배경이 되는 음악, 존재감 없이 스며드는 선율", "그냥 틀어두면 되는 음악",
            "공간이 달라지는 것 같은 앰비언트", "아무것도 하지 않아도 좋은 시간",
            "소리가 공기처럼 퍼져나갈 때", "아무도 없는 방에서 혼자 듣는 음악",
        ]
    elif genre == 'aespa' or any(k in c for k in ['cyberpunk', 'aespa', '에스파', 'synth pop', 'futuristic']):
        emoji = '🤖'
        templates = [
            "현실과 가상의 경계에서", "디지털 세계로 초대합니다",
            "미래에서 온 비트", "사이버 세계에 빠져드는 밤",
            "현실을 초월한 사운드", "AI가 만든 미래의 음악",
            "글리치 속에 숨겨진 감성", "메타버스 속 나만의 플레이리스트",
            "미래형 K-pop, 지금 바로 재생", "디지털 감성 폭발하는 플레이리스트",
        ]
    elif genre == 'shinee' or any(k in c for k in ['shinee', '샤이니', 'funk pop', 'neo soul', 'sophisticated']):
        emoji = '✨'
        templates = [
            "세련된 감각이 흐르는 밤", "어른스러운 팝의 정석",
            "귀에 꽂히는 세련미", "펑크와 소울이 만나는 지점",
            "트렌디하지만 시간이 지나도 좋은 음악", "감각적인 비트 위에서",
            "스타일리시한 K-pop 플레이리스트", "멋있게 살고 싶은 날 트는 음악",
            "도시적인 감성, 세련된 사운드", "매끄럽게 흘러가는 그루브",
        ]
    elif genre == 'snsd' or any(k in c for k in ['snsd', '소녀시대', 'girl group', 'girls generation', 'cheerful']):
        emoji = '🌟'
        templates = [
            "신나고 설레는 그 느낌", "듣는 순간 기분 좋아지는 음악",
            "에너지 충전이 필요한 순간", "밝고 캐치한 K-pop 플레이리스트",
            "오늘도 힘차게 시작하는 하루", "기분 업! 에너지 업!",
            "걸그룹 감성 가득한 플레이리스트", "볼륨 올리고 싶어지는 음악",
            "웃음이 나오는 이유 없는 설렘", "신나서 발 구르게 되는 음악",
        ]
    elif genre == 'kpop' or any(k in c for k in ['kpop', 'k-pop', 'sm entertainment', 'sm mix']):
        emoji = '🎤'
        templates = [
            "SM 감성이 담긴 플레이리스트", "K-pop의 정수를 담아서",
            "에스파부터 소녀시대까지, SM의 모든 것", "K-pop 좋아하는 사람 모여라",
            "SM 스타일로 채우는 한 시간", "K-pop AI 커버 플레이리스트",
            "AI가 재해석한 K-pop 사운드", "장르를 초월한 K-pop 믹스",
            "K-pop 최전선의 사운드", "SM 엔터 감성 AI 음악 모음",
        ]
    elif any(k in c for k in ['힐링', '치유']):
        emoji = '🍃'
        templates = [
            "지친 하루 끝에 듣는 음악", "아무것도 하기 싫은 오늘",
            "그냥 이대로 있고 싶은 날", "오늘 하루도 수고했어",
            "위로가 필요한 날의 플레이리스트", "아무 말 없이 그냥 들어줘",
            "지쳐있어도 괜찮아", "오늘만큼은 아무 생각 안 해도 돼",
            "마음이 무거울 때 틀어두는 음악", "힐링이 필요한 모든 순간에",
        ]
    elif genre in ('dawn', 'lofi'):
        emoji = '🎧'
        templates = [
            "오늘도 수고한 나를 위한 음악", "집중하고 싶을 때 틀어두는 음악",
            "아무것도 안 해도 되는 시간", "그냥 흘려듣기 좋은 플레이리스트",
            "귀에 꽂고 멍 때리기 딱 좋은 음악", "오늘 하루 어떻게 보냈어",
            "아무 생각 없이 듣기 좋은 음악", "퇴근하고 바로 틀어두는 음악",
            "혼자 있을 때 가장 잘 어울리는 음악", "그냥 흘러가도 괜찮은 하루",
        ]
    elif genre == 'citypop':
        emoji = '🌆'
        templates = [
            "도시가 빛나는 밤, 시티팝 한 곡", "80년대 일본 감성이 흐르는 밤",
            "네온사인 아래 걷고 싶은 밤", "도시 한복판에서 혼자인 시간",
            "시티팝으로 채우는 세련된 오후", "저 빌딩 불빛처럼 반짝이는 음악",
        ]
    elif genre == 'chillwave':
        emoji = '🌊'
        templates = [
            "기억 속 어느 여름날처럼", "몽환적인 파도 위에서",
            "흐릿하고 나른한 오후의 음악", "테이프가 늘어지는 것 같은 감성",
            "칠웨이브로 채우는 게으른 오후", "기억이 왜곡되는 것 같은 사운드",
        ]
    elif genre == 'swing':
        emoji = '🎺'
        templates = [
            "신나는 스윙 재즈, 발이 절로 움직여", "빅밴드가 연주하는 설레는 밤",
            "1940년대 재즈클럽으로 떠나는 여행", "재즈가 살아있는 그 시절처럼",
        ]
    elif genre == 'latin':
        emoji = '🌴'
        templates = [
            "보사노바가 흐르는 따뜻한 오후", "라틴 리듬에 몸을 맡겨",
            "브라질의 여름을 담은 플레이리스트", "기타 선율에 흔들리는 오후",
        ]
    elif genre == 'reggae':
        emoji = '🏝️'
        templates = [
            "레게 리듬에 몸을 맡기는 오후", "자메이카 바이브, 아무 걱정 없이",
            "느릿느릿 흘러가도 좋은 시간", "레게가 있으면 다 괜찮아",
        ]
    elif genre == 'disco':
        emoji = '💿'
        templates = [
            "디스코볼이 돌아가는 밤", "70년대 댄스플로어로 초대합니다",
            "펑키한 베이스에 몸이 저절로", "오늘 밤은 디스코로 채워",
        ]
    elif genre == 'rock':
        emoji = '🎸'
        templates = [
            "기타 리프가 터지는 순간", "록이 필요한 하루",
            "볼륨 올리고 싶은 날의 플레이리스트", "에너지 넘치는 록 한 판",
        ]
    elif genre == 'rnb':
        emoji = '🎵'
        templates = [
            "소울 가득한 R&B 오후", "그루브에 몸을 실어",
            "따뜻하고 감성적인 R&B 모음", "밤이 깊어질수록 좋아지는 음악",
        ]
    elif genre == 'newage':
        emoji = '🌠'
        templates = [
            "마음이 고요해지는 뉴에이지", "우주처럼 넓은 소리",
            "영적인 평화가 흐르는 플레이리스트", "아무 생각 없이 흘러가는 음악",
        ]
    elif genre == 'ballad':
        emoji = '🎵'
        templates = [
            "감성 발라드 한 곡이 필요한 밤", "피아노 선율에 눈물이 날 것 같아",
            "마음을 건드리는 발라드 모음", "오늘 밤은 발라드가 딱이야",
        ]
    elif genre == 'easylistening':
        emoji = '🎶'
        templates = [
            "편안하게 흘려듣기 좋은 음악", "아무 생각 없이 틀어두는 플레이리스트",
            "배경음악으로 완벽한 이지리스닝", "귀가 편안해지는 음악 모음",
        ]
    elif genre == 'lullaby':
        emoji = '🌛'
        templates = [
            "오늘 밤 잠들기 좋은 자장가", "꿈 나라로 데려다줄 음악",
            "눈이 스르르 감기는 플레이리스트", "아기처럼 잠들고 싶은 밤",
        ]
    elif genre == 'electronic':
        emoji = '🎛️'
        templates = [
            "전자음악이 울려 퍼지는 밤", "사운드가 공간을 가득 채울 때",
            "일렉트로닉 사운드로 채우는 오늘", "현대적인 전자음악 플레이리스트",
        ]
    else:
        emoji = '🍃'
        templates = [
            "아무것도 하기 싫은 오늘", "그냥 이대로 있고 싶은 날",
            "오늘 하루도 수고했어", "아무 말 없이 그냥 듣는 음악",
            "혼자인 게 좋은 날", "아무도 없어도 괜찮아",
            "오늘도 별 거 없었지만 그게 좋아", "그냥 멍 때리고 싶을 때",
            "말로 표현 안 되는 감정이 있을 때", "이 음악 하나면 충분한 하루",
        ]

    return f"PLAYLIST {emoji} | {random.choice(templates)}"


# ── 설명 생성 ──────────────────────────────────────────────────────────────────
def generate_description(concept: str, genre: str, tracklist: list[dict] = None) -> str:
    openers = {
        "lofi":   "🎧 오늘도 수고한 나를 위한 로파이.",
        "heal":   "🍃 지친 하루 끝에 듣는 음악.",
        "bass":   "🌑 무거운 베이스, 혼자만의 시간.",
        "dawn":   "🌙 아무도 없는 새벽, 혼자만의 감성.",
        "drive":  "🚗 아무 생각 없이 달릴 때.",
        "aespa":  "🤖 현실과 가상의 경계, AI가 만든 사이버 K-pop.",
        "shinee": "✨ 세련된 펑크팝, 시간이 지나도 빛나는 사운드.",
        "snsd":   "🌟 밝고 에너지 넘치는 걸그룹 K-pop 플레이리스트.",
        "kpop":   "🎤 SM 스타일로 재해석한 AI K-pop 컬렉션.",
    }
    opener = openers.get(genre, "🎵 당신을 위한 플레이리스트.")
    short  = concept[:40] + ("..." if len(concept) > 40 else "")

    tl_block = ""
    if tracklist:
        lines = "\n".join(f'{t["timestamp"]} ─ {t["name"]}' for t in tracklist)
        tl_block = f"""
━━━━━━━━━━━━━━━━━━━━━━
🕐 Tracklist
━━━━━━━━━━━━━━━━━━━━━━
{lines}
"""
    return f"""{opener}
{tl_block}
━━━━━━━━━━━━━━━━━━━━━━
🎧 이런 분들께 추천해요
━━━━━━━━━━━━━━━━━━━━━━
✔ {short}
✔ 집중이 필요한 시간
✔ 그냥 흘려듣고 싶을 때

━━━━━━━━━━━━━━━━━━━━━━
🔔 더 많은 음악 보러오기
━━━━━━━━━━━━━━━━━━━━━━
→ youtube.com/@AIsense

AI로 만든 감성 음악 채널, aisence
구독 & 좋아요는 큰 힘이 됩니다 🙏"""


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def push_message(job_id: str, msg: str):
    if job_id in jobs:
        jobs[job_id]["messages"].append({"text": msg, "time": datetime.now().strftime("%H:%M:%S")})


# ── Suno 한 배치 생성 (2트랙) — 자동 재시도 포함 ────────────────────────────
async def generate_one_batch(job_id: str, series_dir: Path, track_title: str, concept: str, batch_num: int,
                             max_retries: int = 2, retry_delay: int = 30,
                             instrumental: bool = True, lyrics: str = "", language: str = "English") -> list[str]:
    loop = asyncio.get_event_loop()
    try:
        from scripts.suno_generate import generate_music, wait_for_result, download_mp3
    except ImportError:
        from suno_generate import generate_music, wait_for_result, download_mp3

    import scripts.suno_generate as sg
    original = sg.OUTPUT_DIR
    sg.OUTPUT_DIR = str(series_dir)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            task_id = await loop.run_in_executor(None, lambda: generate_music(
                title=track_title, style=concept, lyrics=lyrics, instrumental=instrumental, language=language))
            push_message(job_id, f"  → 배치 {batch_num} task: {task_id}")
            tracks = await loop.run_in_executor(None, lambda: wait_for_result(task_id))
            paths  = await loop.run_in_executor(None, lambda: download_mp3(tracks, track_title))
            sg.OUTPUT_DIR = original
            return paths
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                push_message(job_id, f"  ⚠️ 배치 {batch_num} 실패 ({attempt+1}/{max_retries} 재시도) — {retry_delay}초 후 재시도...")
                await asyncio.sleep(retry_delay)
            else:
                sg.OUTPUT_DIR = original
                raise last_error


# ── 메타데이터 저장/로드 ────────────────────────────────────────────────────────
def save_job_meta(series_dir: Path, data: dict):
    with open(series_dir / ".job_meta.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_job_meta(series_dir: Path) -> dict | None:
    p = series_dir / ".job_meta.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _finalize_selected(selected: str) -> str:
    """선택된 트랙 파일명에서 _숫자 접미사 제거. 충돌 시 원본 경로 반환."""
    p = Path(selected)
    clean_stem = re.sub(r'_\d+$', '', p.stem)
    clean_path = p.parent / f"{clean_stem}{p.suffix}"
    if clean_path != p and not clean_path.exists():
        p.rename(clean_path)
        return str(clean_path)
    return selected


# ── 트랙 순서 지정 → 영상 → 업로드 공통 파이프라인 ────────────────────────────
async def run_post_generation(job_id: str, series_dir: Path,
                               title: str, concept: str, genre: str,
                               image_path: str | None,
                               selected_paths: list[str] | None = None):
    loop = asyncio.get_event_loop()

    # ── 트랙 순서 지정 대기 ──────────────────────────────────────────────────────
    track_list = selected_paths if selected_paths else sorted(glob.glob(str(series_dir / "*.mp3")))
    jobs[job_id]["tracks"] = track_list
    jobs[job_id]["status"] = "tracks_ready"
    push_message(job_id, f"🎼 트랙 순서를 지정해주세요 ({len(track_list)}개)")

    order_event = asyncio.Event()
    order_events[job_id] = order_event
    await order_event.wait()

    ordered_tracks = jobs[job_id].get("ordered_tracks", track_list)
    push_message(job_id, f"✅ 트랙 순서 확정 — {len(ordered_tracks)}개")
    jobs[job_id]["status"] = "running"

    # ── 영상 제작 ─────────────────────────────────────────────────────────────────
    if not image_path:
        png_files = glob.glob(str(series_dir / "*.png"))
        image_path = png_files[0] if png_files else None

    video_path  = None
    tracklist   = []
    series_name = series_dir.name

    if image_path:
        push_message(job_id, "🎬 영상 제작 중... (MoviePy)")

        def _make_video():
            from moviepy import AudioFileClip, ImageClip, concatenate_audioclips
            from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
            _tl, clips, current = [], [], 0.0
            for p in ordered_tracks:
                clip = AudioFileClip(p)
                m, s = divmod(int(current), 60)
                _tl.append({"name": Path(p).stem, "timestamp": f"{m:02d}:{s:02d}"})
                current += clip.duration
                clips.append(clip)
            combined = concatenate_audioclips(clips)
            combined = combined.with_effects([AudioFadeIn(2.0), AudioFadeOut(4.0)])
            video    = ImageClip(image_path).with_duration(combined.duration).with_audio(combined)
            out      = str(series_dir / f"{series_name}_플레이리스트.mp4")
            video.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None)
            for c in clips:
                c.close()
            return out, _tl

        video_path, tracklist = await loop.run_in_executor(None, _make_video)
        push_message(job_id, f"  → 영상 저장: {Path(video_path).name}")
    else:
        push_message(job_id, "  ⚠️ 이미지 없음 — 영상 제작 생략")

        def _calc_tl():
            from moviepy import AudioFileClip
            _tl, current = [], 0.0
            for p in ordered_tracks:
                try:
                    clip = AudioFileClip(p)
                    dur  = clip.duration
                    clip.close()
                except Exception:
                    dur = 0.0
                m, s = divmod(int(current), 60)
                _tl.append({"name": Path(p).stem, "timestamp": f"{m:02d}:{s:02d}"})
                current += dur
            return _tl

        tracklist = await loop.run_in_executor(None, _calc_tl)

    # ── 미리보기 대기 ─────────────────────────────────────────────────────────────
    if video_path:
        thumb_url = None
        if image_path and image_path.startswith(str(UPLOAD_DIR)):
            thumb_url = f"/uploads/{Path(image_path).name}"

        desc = generate_description(concept, genre, tracklist)
        jobs[job_id]["preview"] = {
            "title":         title,
            "description":   desc,
            "thumbnail_url": thumb_url,
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

    # ── 유튜브 업로드 ─────────────────────────────────────────────────────────────
    youtube_url = None
    if video_path and os.path.exists(video_path):
        push_message(job_id, "📤 유튜브 업로드 중...")

        def _upload():
            try:    from scripts.upload_youtube import upload_video
            except: from upload_youtube import upload_video
            vid_id = upload_video(
                video_path=video_path,
                title=title,
                genre=genre,
                description=generate_description(concept, genre, tracklist),
                thumbnail_path=image_path if image_path and os.path.exists(image_path) else None,
            )
            return f"https://www.youtube.com/watch?v={vid_id}"

        try:
            youtube_url = await loop.run_in_executor(None, _upload)
            push_message(job_id, "  → 업로드 완료!")
        except Exception as e:
            push_message(job_id, f"  ⚠️ 업로드 실패: {e}")
            jobs[job_id]["upload_context"] = {
                "video_path": video_path,
                "tracklist":  tracklist,
                "title":      title,
                "concept":    concept,
                "genre":      genre,
                "image_path": image_path,
            }
            jobs[job_id]["status"] = "upload_failed"
            push_message(job_id, "🔁 업로드 재시도 가능 — 미리보기 화면에서 다시 시도해주세요")
            return

    jobs[job_id]["status"]      = "done"
    jobs[job_id]["youtube_url"] = youtube_url
    push_message(job_id, f"✅ 완료!{' ' + youtube_url if youtube_url else ''}")


# ── 업로드 재시도 (미리보기 → 업로드만 다시 실행) ───────────────────────────────
async def run_upload_retry(job_id: str):
    ctx = jobs[job_id].get("upload_context")
    if not ctx:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"]  = "업로드 컨텍스트 없음"
        push_message(job_id, "❌ 업로드 컨텍스트 없음")
        return

    jobs[job_id]["status"]    = "running"
    jobs[job_id]["cancelled"] = False
    loop = asyncio.get_event_loop()

    video_path = ctx["video_path"]
    tracklist  = ctx["tracklist"]
    title      = ctx["title"]
    concept    = ctx["concept"]
    genre      = ctx["genre"]
    image_path = ctx["image_path"]

    # ── 미리보기 ─────────────────────────────────────────────────────────────────
    thumb_url = None
    if image_path and image_path.startswith(str(UPLOAD_DIR)):
        thumb_url = f"/uploads/{Path(image_path).name}"

    desc = generate_description(concept, genre, tracklist)
    jobs[job_id]["preview"] = {
        "title":         title,
        "description":   desc,
        "thumbnail_url": thumb_url,
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

    # ── 업로드 ───────────────────────────────────────────────────────────────────
    push_message(job_id, "📤 유튜브 업로드 중...")

    def _upload_retry():
        try:    from scripts.upload_youtube import upload_video
        except: from upload_youtube import upload_video
        vid_id = upload_video(
            video_path=video_path,
            title=title,
            genre=genre,
            description=generate_description(concept, genre, tracklist),
            thumbnail_path=image_path if image_path and os.path.exists(image_path) else None,
        )
        return f"https://www.youtube.com/watch?v={vid_id}"

    try:
        youtube_url = await loop.run_in_executor(None, _upload_retry)
        push_message(job_id, "  → 업로드 완료!")
        jobs[job_id]["status"]      = "done"
        jobs[job_id]["youtube_url"] = youtube_url
        push_message(job_id, f"✅ 완료! {youtube_url}")
    except Exception as e:
        push_message(job_id, f"  ⚠️ 업로드 실패: {e}")
        jobs[job_id]["status"] = "upload_failed"
        push_message(job_id, "🔁 업로드 재시도 가능 — 미리보기 화면에서 다시 시도해주세요")


# ── 파이프라인 ─────────────────────────────────────────────────────────────────
async def run_pipeline(job_id: str, req: GenerateRequest):
    jobs[job_id]["status"] = "running"
    loop = asyncio.get_event_loop()

    # ── 0. 폴더 생성 ────────────────────────────────────────────────────────────
    safe_series_name = re.sub(r'[/\\:*?"<>|]', '-', req.series_name).strip()
    series_dir = Path(os.path.join(str(MUSIC_FILE_ROOT), safe_series_name))
    series_dir.mkdir(parents=True, exist_ok=True)
    jobs[job_id]["series_dir"]   = str(series_dir)
    jobs[job_id]["concept"]      = req.concept
    jobs[job_id]["instrumental"] = req.instrumental
    jobs[job_id]["lyrics"]       = req.lyrics
    jobs[job_id]["language"]     = req.language
    push_message(job_id, f"📁 폴더 생성: {series_dir.name}/")

    # 업로드 이미지 → 시리즈 폴더로 복사
    image_path = req.image_path
    if image_path and os.path.exists(image_path):
        dest = series_dir / Path(image_path).name
        if str(Path(image_path).resolve()) != str(dest.resolve()):
            shutil.copy2(image_path, dest)
        image_path = str(dest)

    # ── 메타데이터 저장 (재개를 위해) ───────────────────────────────────────────
    save_job_meta(series_dir, {
        "series_name":  req.series_name,
        "concept":      req.concept,
        "title":        req.title,
        "genre":        req.genre,
        "extra_tracks": req.extra_tracks,
        "target_count": req.extra_tracks + 1,
        "image_path":   image_path,
        "instrumental": req.instrumental,
        "lyrics":       req.lyrics,
        "language":     req.language,
    })

    try:
        all_mp3_paths = []

        # ── 1. 샘플 1배치 생성 (2트랙) ──────────────────────────────────────────
        mode_label = "반주 모드" if req.instrumental else "보컬 모드"
        push_message(job_id, f"🎵 샘플 생성 중... (Suno AI) [{mode_label}]")
        sample_title = f"track_sample" if req.language and req.language.lower() != "korean" else f"{req.series_name}_sample"
        suno_style = SUNO_STYLE_MAP.get(req.genre, req.concept)
        sample_paths = await generate_one_batch(job_id, series_dir, sample_title, suno_style, 1,
                                                instrumental=req.instrumental, lyrics=req.lyrics, language=req.language)

        if not sample_paths:
            raise RuntimeError("샘플 MP3 다운로드 실패")

        # 샘플 승인 루프
        sample_lyrics = req.lyrics  # 이 배치에 쓸 가사
        while True:
            jobs[job_id]["sample_path"]  = sample_paths[0]
            jobs[job_id]["sample_paths"] = sample_paths
            jobs[job_id]["status"] = "sample_ready"
            push_message(job_id, f"👂 샘플 준비됨 — A/B 들어보고 선택해주세요")

            event = asyncio.Event()
            sample_events[job_id] = event
            await event.wait()

            if jobs[job_id].get("sample_approved"):
                idx = jobs[job_id].get("selected_track_index", 0)
                selected = sample_paths[idx] if idx < len(sample_paths) else sample_paths[0]
                for i, p in enumerate(sample_paths):
                    if i != idx and os.path.exists(p):
                        os.remove(p)
                selected = _finalize_selected(selected)
                all_mp3_paths.append(selected)
                _m = load_job_meta(series_dir) or {}
                _m["selected_paths"] = all_mp3_paths
                save_job_meta(series_dir, _m)
                current_lyrics = jobs[job_id].get("next_lyrics", "")  # 다음 배치 가사
                push_message(job_id, "✅ 샘플 승인 — 나머지 음악 생성 시작")
                break
            else:
                push_message(job_id, "🔄 샘플 다시 생성 중...")
                jobs[job_id]["status"] = "running"
                sample_paths = await generate_one_batch(job_id, series_dir, sample_title, suno_style, 1,
                                                        instrumental=req.instrumental, lyrics=sample_lyrics, language=req.language)
                if not sample_paths:
                    raise RuntimeError("재생성 실패")

        # ── 2. 나머지 트랙 — 한 곡씩 승인 후 진행 ──────────────────────────────
        total_batches = req.extra_tracks + 1  # 샘플 포함 전체 배치 수
        for i in range(req.extra_tracks):
            batch_num = i + 2  # 샘플이 1번이므로 2번부터
            t_title = f"track_{i+1}" if req.language and req.language.lower() != "korean" else f"{safe_series_name}_트랙{i+1}"
            batch_lyrics = current_lyrics  # 이 배치에 쓸 가사
            push_message(job_id, f"🎵 트랙 {batch_num}/{total_batches} 생성 중...{'(가사 직접 입력)' if batch_lyrics else ''}")
            jobs[job_id]["status"] = "running"

            # 생성 (재시도 포함)
            track_paths = await generate_one_batch(job_id, series_dir, t_title, suno_style, batch_num,
                                                   instrumental=req.instrumental, lyrics=batch_lyrics, language=req.language)
            if not track_paths:
                push_message(job_id, f"  ⚠️ 트랙 {batch_num} 생성 실패 — 스킵")
                continue

            # 승인 루프
            while True:
                jobs[job_id]["sample_path"]  = track_paths[0]
                jobs[job_id]["sample_paths"] = track_paths
                jobs[job_id]["status"] = "sample_ready"
                jobs[job_id]["track_num"] = batch_num
                jobs[job_id]["total_tracks"] = total_batches
                push_message(job_id, f"👂 트랙 {batch_num}/{total_batches} 준비됨 — A/B 선택해주세요")

                event = asyncio.Event()
                sample_events[job_id] = event
                await event.wait()

                if jobs[job_id].get("sample_approved"):
                    idx = jobs[job_id].get("selected_track_index", 0)
                    selected = track_paths[idx] if idx < len(track_paths) else track_paths[0]
                    for i, p in enumerate(track_paths):
                        if i != idx and os.path.exists(p):
                            os.remove(p)
                    selected = _finalize_selected(selected)
                    all_mp3_paths.append(selected)
                    _m = load_job_meta(series_dir) or {}
                    _m["selected_paths"] = all_mp3_paths
                    save_job_meta(series_dir, _m)
                    current_lyrics = jobs[job_id].get("next_lyrics", "")  # 다음 배치 가사
                    push_message(job_id, f"✅ 트랙 {batch_num} 승인")
                    break
                else:
                    push_message(job_id, f"🔄 트랙 {batch_num} 다시 생성 중...")
                    jobs[job_id]["status"] = "running"
                    track_paths = await generate_one_batch(job_id, series_dir, t_title, req.concept, batch_num,
                                                           instrumental=req.instrumental, lyrics=batch_lyrics, language=req.language)
                    if not track_paths:
                        push_message(job_id, f"  ⚠️ 재생성 실패 — 스킵")
                        break

        push_message(job_id, f"  → 총 {len(all_mp3_paths)}개 MP3 생성 완료")

        if not all_mp3_paths:
            raise RuntimeError("생성된 MP3가 없습니다. 나중에 다시 시도해주세요.")

        await run_post_generation(job_id, series_dir,
                                   req.title, req.concept, req.genre, image_path,
                                   selected_paths=all_mp3_paths)

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"]  = str(e)
        push_message(job_id, f"❌ 오류: {e}")


# ── 재개 파이프라인 ────────────────────────────────────────────────────────────
async def run_resume_pipeline(job_id: str, series_dir: Path, meta: dict):
    series_name  = meta["series_name"]
    concept      = meta["concept"]
    title        = meta["title"]
    genre        = meta["genre"]
    extra_tracks = meta.get("extra_tracks", 9)
    target_count = meta.get("target_count", extra_tracks + 1)
    image_path   = meta.get("image_path")
    instrumental = meta.get("instrumental", True)
    lyrics       = meta.get("lyrics", "")
    language     = meta.get("language", "English")

    jobs[job_id]["status"]       = "running"
    jobs[job_id]["series_dir"]   = str(series_dir)
    jobs[job_id]["concept"]      = concept
    jobs[job_id]["instrumental"] = instrumental
    jobs[job_id]["lyrics"]       = lyrics
    jobs[job_id]["language"]     = language

    # 이미지 경로 유효성 확인 (없으면 폴더 내 PNG 검색)
    if not image_path or not os.path.exists(image_path):
        png_files  = glob.glob(str(series_dir / "*.png"))
        image_path = png_files[0] if png_files else None

    try:
        push_message(job_id, f"📋 이전 작업 콘셉트: {concept}")
        push_message(job_id, f"🎵 장르: {genre}  |  제목: {title}")

        # ── 저장된 선택 트랙 복원 ───────────────────────────────────────────────
        all_mp3_paths = [p for p in meta.get("selected_paths", []) if os.path.exists(p)]

        if all_mp3_paths:
            push_message(job_id, f"📂 이전 진행 복원: {len(all_mp3_paths)}개 트랙 확인됨")
        else:
            # 저장된 진행 없음 — 스타일 확인용 샘플 A/B 생성
            push_message(job_id, "🎵 샘플 생성 중... (Suno AI)")
            resume_sample_title = f"{series_name}_재개샘플"
            sample_paths = await generate_one_batch(job_id, series_dir, resume_sample_title, concept, 0,
                                                    instrumental=instrumental, lyrics=lyrics, language=language)
            if not sample_paths:
                raise RuntimeError("샘플 MP3 다운로드 실패")

            while True:
                jobs[job_id]["sample_path"]  = sample_paths[0]
                jobs[job_id]["sample_paths"] = sample_paths
                jobs[job_id]["status"] = "sample_ready"
                push_message(job_id, "👂 샘플 준비됨 — A/B 들어보고 선택해주세요")

                event = asyncio.Event()
                sample_events[job_id] = event
                await event.wait()

                if jobs[job_id].get("sample_approved"):
                    idx = jobs[job_id].get("selected_track_index", 0)
                    selected = sample_paths[idx] if idx < len(sample_paths) else sample_paths[0]
                    for i, p in enumerate(sample_paths):
                        if i != idx and os.path.exists(p):
                            os.remove(p)
                    selected = _finalize_selected(selected)
                    all_mp3_paths.append(selected)
                    _m = load_job_meta(series_dir) or {}
                    _m["selected_paths"] = all_mp3_paths
                    save_job_meta(series_dir, _m)
                    push_message(job_id, "✅ 샘플 승인 — 나머지 음악 생성 시작")
                    jobs[job_id]["status"] = "running"
                    break
                else:
                    push_message(job_id, "🔄 샘플 다시 생성 중...")
                    jobs[job_id]["status"] = "running"
                    sample_paths = await generate_one_batch(job_id, series_dir, resume_sample_title, concept, 0,
                                                            instrumental=instrumental, lyrics=lyrics, language=language)
                    if not sample_paths:
                        raise RuntimeError("재생성 실패")

        # ── 나머지 트랙 — A/B 선택 포함 ─────────────────────────────────────────
        remaining = max(0, target_count - len(all_mp3_paths))
        push_message(job_id, f"📁 현재 {len(all_mp3_paths)}개 / 목표 {target_count}개 — {remaining}개 더 생성")

        for i in range(remaining):
            batch_num   = len(all_mp3_paths) + 1
            track_title = f"{series_name}_재개트랙{batch_num}"
            push_message(job_id, f"🎵 트랙 {batch_num}/{target_count} 생성 중...")
            jobs[job_id]["status"] = "running"

            track_paths = await generate_one_batch(job_id, series_dir, track_title, concept, batch_num,
                                                   instrumental=instrumental, lyrics=lyrics, language=language)
            if not track_paths:
                push_message(job_id, f"  ⚠️ 트랙 {batch_num} 생성 실패 — 스킵")
                continue

            while True:
                jobs[job_id]["sample_path"]  = track_paths[0]
                jobs[job_id]["sample_paths"] = track_paths
                jobs[job_id]["status"] = "sample_ready"
                jobs[job_id]["track_num"]    = batch_num
                jobs[job_id]["total_tracks"] = target_count
                push_message(job_id, f"👂 트랙 {batch_num}/{target_count} 준비됨 — A/B 선택해주세요")

                event = asyncio.Event()
                sample_events[job_id] = event
                await event.wait()

                if jobs[job_id].get("sample_approved"):
                    idx = jobs[job_id].get("selected_track_index", 0)
                    selected = track_paths[idx] if idx < len(track_paths) else track_paths[0]
                    for j, p in enumerate(track_paths):
                        if j != idx and os.path.exists(p):
                            os.remove(p)
                    selected = _finalize_selected(selected)
                    all_mp3_paths.append(selected)
                    _m = load_job_meta(series_dir) or {}
                    _m["selected_paths"] = all_mp3_paths
                    save_job_meta(series_dir, _m)
                    push_message(job_id, f"✅ 트랙 {batch_num} 승인")
                    break
                else:
                    push_message(job_id, f"🔄 트랙 {batch_num} 다시 생성 중...")
                    jobs[job_id]["status"] = "running"
                    track_paths = await generate_one_batch(job_id, series_dir, track_title, concept, batch_num,
                                                           instrumental=instrumental, lyrics=lyrics, language=language)
                    if not track_paths:
                        push_message(job_id, f"  ⚠️ 재생성 실패 — 스킵")
                        break

        if not all_mp3_paths:
            raise RuntimeError("재개할 MP3가 없습니다.")

        push_message(job_id, f"  → 총 {len(all_mp3_paths)}개 MP3 생성 완료")
        await run_post_generation(job_id, series_dir, title, concept, genre, image_path,
                                   selected_paths=all_mp3_paths)

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"]  = str(e)
        push_message(job_id, f"❌ 오류: {e}")


# ── 트랙 추가 생성 ─────────────────────────────────────────────────────────────
async def run_add_tracks(job_id: str, series_dir: Path, concept: str):
    batch_num    = len(glob.glob(str(series_dir / "*.mp3"))) // 2 + 1
    track_title  = f"{series_dir.name}_추가트랙{batch_num}"
    instrumental = jobs.get(job_id, {}).get("instrumental", True)
    lyrics       = jobs.get(job_id, {}).get("lyrics", "")
    language     = jobs.get(job_id, {}).get("language", "English")
    push_message(job_id, f"🎵 음악 추가 생성 중... (배치 {batch_num})")
    try:
        paths = await generate_one_batch(job_id, series_dir, track_title, concept, batch_num,
                                         instrumental=instrumental, lyrics=lyrics, language=language)
        if paths:
            new_tracks = [{"path": p, "name": Path(p).stem} for p in paths]
            jobs[job_id]["add_tracks_queue"].extend(new_tracks)
            push_message(job_id, f"  → {len(paths)}개 트랙 추가 완료")
        else:
            push_message(job_id, "  ⚠️ 추가 생성 실패")
    except Exception as e:
        push_message(job_id, f"  ❌ 추가 생성 오류: {e}")
    finally:
        jobs[job_id]["adding_tracks"] = False


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
    print(f"[GENERATE] instrumental={req.instrumental} lyrics_len={len(req.lyrics)} series={req.series_name}", flush=True)
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending", "messages": [], "youtube_url": None,
        "video_path": None, "sample_path": None, "preview": None,
        "error": None, "title": req.title, "series_name": req.series_name,
        "created_at": datetime.now().isoformat(),
        "add_tracks_queue": [], "adding_tracks": False,
    }
    background_tasks.add_task(run_pipeline, job_id, req)
    return {"job_id": job_id}


@app.post("/resume/{series_name}")
async def resume_job(series_name: str, background_tasks: BackgroundTasks):
    series_dir = MUSIC_FILE_ROOT / series_name
    if not series_dir.exists():
        raise HTTPException(404, f"시리즈 폴더 없음: {series_name}")

    meta = load_job_meta(series_dir)
    if not meta:
        # 메타데이터 없으면 시리즈명으로 자동 재구성
        auto = analyze_series(series_name)
        meta = {
            "series_name":  series_name,
            "concept":      auto["concept"],
            "title":        auto["title"],
            "genre":        auto["genre"],
            "extra_tracks": 9,
            "target_count": 20,
            "image_path":   None,
        }
        save_job_meta(series_dir, meta)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending", "messages": [], "youtube_url": None,
        "video_path": None, "sample_path": None, "preview": None,
        "error": None, "title": meta.get("title", series_name),
        "series_name": series_name,
        "created_at": datetime.now().isoformat(),
        "add_tracks_queue": [], "adding_tracks": False,
    }
    background_tasks.add_task(run_resume_pipeline, job_id, series_dir, meta)
    return {"job_id": job_id}


@app.get("/sample/{job_id}")
async def get_sample(job_id: str, index: int = 0):
    """샘플 오디오 파일 스트리밍 (index=0: A버전, index=1: B버전)"""
    if job_id not in jobs:
        raise HTTPException(404)
    paths = jobs[job_id].get("sample_paths") or []
    if not paths:
        p = jobs[job_id].get("sample_path")
        if p:
            paths = [p]
    if not paths or index >= len(paths) or not paths[index] or not os.path.exists(paths[index]):
        raise HTTPException(404, "샘플 파일 없음")
    return FileResponse(paths[index], media_type="audio/mpeg")


@app.post("/approve-sample/{job_id}")
async def approve_sample(job_id: str, req: ApproveRequest = ApproveRequest()):
    if job_id not in jobs:
        raise HTTPException(404)
    jobs[job_id]["sample_approved"] = True
    jobs[job_id]["selected_track_index"] = req.selected_index
    jobs[job_id]["next_lyrics"] = req.next_lyrics
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


@app.get("/track-audio/{job_id}/{filename}")
async def get_track_audio(job_id: str, filename: str):
    if job_id not in jobs:
        raise HTTPException(404)
    series_dir = jobs[job_id].get("series_dir")
    if not series_dir:
        raise HTTPException(404)
    path = Path(series_dir) / filename
    if not path.exists() or path.suffix.lower() != ".mp3":
        raise HTTPException(404, "파일 없음")
    return FileResponse(str(path), media_type="audio/mpeg")


@app.post("/add-tracks/{job_id}")
async def add_tracks(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(404)
    job = jobs[job_id]
    if job.get("adding_tracks"):
        return {"ok": False, "message": "이미 생성 중입니다"}
    series_dir = job.get("series_dir")
    concept    = job.get("concept", "")
    if not series_dir:
        raise HTTPException(400, "series_dir 없음")
    job["adding_tracks"] = True
    background_tasks.add_task(run_add_tracks, job_id, Path(series_dir), concept)
    return {"ok": True}


@app.post("/set-track-order/{job_id}")
async def set_track_order(job_id: str, req: TrackOrderRequest):
    if job_id not in jobs:
        raise HTTPException(404)
    jobs[job_id]["ordered_tracks"] = req.ordered_paths
    if job_id in order_events:
        order_events[job_id].set()
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


@app.post("/retry-upload/{job_id}")
async def retry_upload(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(404)
    if jobs[job_id].get("status") != "upload_failed":
        raise HTTPException(400, "업로드 실패 상태가 아닙니다")
    background_tasks.add_task(run_upload_retry, job_id)
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
                payload = json.dumps({
                    "type": "sample_ready",
                    "job_id": job_id,
                    "track_num": job.get("track_num", 1),
                    "total_tracks": job.get("total_tracks", 1),
                    "track_count": len(job.get("sample_paths") or [job.get("sample_path")]),
                }, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                while jobs.get(job_id, {}).get("status") == "sample_ready":
                    await asyncio.sleep(0.5)
                continue

            if status == "tracks_ready":
                tracks = job.get("tracks", [])
                payload = json.dumps({
                    "type": "tracks_ready",
                    "job_id": job_id,
                    "tracks": [{"path": p, "name": Path(p).stem} for p in tracks],
                }, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                add_sent = 0
                while jobs.get(job_id, {}).get("status") == "tracks_ready":
                    add_queue = jobs.get(job_id, {}).get("add_tracks_queue", [])
                    if add_sent < len(add_queue):
                        new_tracks = add_queue[add_sent:]
                        add_sent = len(add_queue)
                        payload2 = json.dumps({
                            "type": "tracks_added",
                            "tracks": new_tracks,
                        }, ensure_ascii=False)
                        yield f"data: {payload2}\n\n"
                    await asyncio.sleep(0.5)
                continue

            if status == "preview_ready":
                preview = job.get("preview", {})
                payload = json.dumps({"type": "preview", "job_id": job_id, **preview}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                while jobs.get(job_id, {}).get("status") == "preview_ready":
                    await asyncio.sleep(0.5)
                continue

            if status == "upload_failed":
                payload = json.dumps({"type": "upload_failed", "job_id": job_id}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                while jobs.get(job_id, {}).get("status") == "upload_failed":
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


# ── Suno 크레딧 확인 ──────────────────────────────────────────────────────────
@app.get("/suno-credits")
async def suno_credits():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
        api_key = os.getenv("SUNOAPI_KEY")
        if not api_key:
            return {"credits": None, "error": "API 키 없음"}
        resp = http_requests.get(
            "https://api.sunoapi.org/api/v1/generate/credit",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=8,
        )
        data = resp.json()
        if data.get("code") == 200:
            d = data.get("data")
            if isinstance(d, (int, float)):
                credits = int(d)
            elif isinstance(d, dict):
                v = d.get("credits", d.get("left", d.get("remaining")))
                credits = int(v) if isinstance(v, (int, float)) else "?"
            else:
                credits = "?"
        else:
            credits = "?"
        return {"credits": credits}
    except Exception as e:
        return {"credits": "?", "error": str(e)}


# ── YouTube 인증 상태 확인 ────────────────────────────────────────────────────
@app.get("/youtube-status")
async def youtube_status():
    try:
        from scripts.upload_youtube import TOKEN_FILE, CLIENT_SECRETS_FILE
    except Exception:
        try:
            from upload_youtube import TOKEN_FILE, CLIENT_SECRETS_FILE
        except Exception:
            return {"status": "error", "message": "모듈 로드 실패"}

    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"status": "no_secrets", "message": "client_secrets.json 없음"}
    if not os.path.exists(TOKEN_FILE):
        return {"status": "not_auth", "message": "인증 필요"}
    try:
        from google.auth.transport.requests import Request
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
        if creds and creds.valid:
            return {"status": "ok", "message": "연결됨"}
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
            return {"status": "ok", "message": "연결됨"}
        else:
            return {"status": "not_auth", "message": "재인증 필요"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── YouTube OAuth 인증 실행 ───────────────────────────────────────────────────
_yt_auth_state: dict = {"running": False, "error": None}

@app.post("/youtube-auth")
async def start_youtube_auth(background_tasks: BackgroundTasks):
    if _yt_auth_state["running"]:
        return {"ok": False, "message": "이미 인증 진행 중입니다"}

    def _run_auth():
        _yt_auth_state["running"] = True
        _yt_auth_state["error"] = None
        try:
            from scripts.upload_youtube import CLIENT_SECRETS_FILE, TOKEN_FILE, SCOPES
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, authorization_prompt_message="",
                                          extra_params={"prompt": "select_account consent"})
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        except Exception as e:
            _yt_auth_state["error"] = str(e)
        finally:
            _yt_auth_state["running"] = False

    background_tasks.add_task(_run_auth)
    return {"ok": True, "message": "브라우저에서 Google 계정 인증을 완료해주세요"}
