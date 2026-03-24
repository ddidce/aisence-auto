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
order_events:   dict[str, asyncio.Event] = {}


# ── 요청 모델 ──────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    series_name: str
    concept: str
    title: str
    genre: str = "lofi"
    image_path: Optional[str] = None
    extra_tracks: int = 9  # 샘플 승인 후 추가 생성할 배치 수 (1배치=2트랙)


class SeriesRequest(BaseModel):
    series_name: str


class TitleRequest(BaseModel):
    concept: str
    genre: str = "lofi"


class TrackOrderRequest(BaseModel):
    ordered_paths: list[str]


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

        # ── 2.5 트랙 순서 지정 대기 ──────────────────────────────────────────────
        track_list = sorted(glob.glob(str(series_dir / "*.mp3")))
        jobs[job_id]["tracks"]  = track_list
        jobs[job_id]["status"]  = "tracks_ready"
        push_message(job_id, f"🎼 트랙 순서를 지정해주세요 ({len(track_list)}개)")

        order_event = asyncio.Event()
        order_events[job_id] = order_event
        await order_event.wait()

        ordered_tracks = jobs[job_id].get("ordered_tracks", track_list)
        push_message(job_id, f"✅ 트랙 순서 확정 — {len(ordered_tracks)}개")
        jobs[job_id]["status"] = "running"

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
                mp3s = ordered_tracks
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

            if status == "tracks_ready":
                tracks = job.get("tracks", [])
                payload = json.dumps({
                    "type": "tracks_ready",
                    "job_id": job_id,
                    "tracks": [{"path": p, "name": Path(p).stem} for p in tracks],
                }, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                while jobs.get(job_id, {}).get("status") == "tracks_ready":
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
