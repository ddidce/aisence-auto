"""
aisence — 유튜브 자동 업로드
사용법: python upload_youtube.py --video ../output/xxx_final.mp4 --title "제목" --genre lofi
"""

import argparse
import os
import pickle
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube API 권한 범위
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secrets.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.pickle")

# 장르별 기본 태그
GENRE_TAGS = {
    "lofi":         ["aisence", "lofi", "lofi hip hop", "chill music", "study music", "AI음악", "감성음악", "힐링음악"],
    "heal":         ["aisence", "힐링음악", "healing music", "잔잔한음악", "감성음악", "ambient music", "AI음악"],
    "bass":         ["aisence", "bass music", "deep bass", "베이스음악", "dark music", "electronic music", "AI음악"],
    "dawn":         ["aisence", "새벽음악", "새벽감성", "밤음악", "late night music", "midnight vibes", "AI음악"],
    "drive":        ["aisence", "드라이브음악", "drive music", "야간드라이브", "night drive", "road trip", "AI음악"],
    "drive_summer": ["aisence", "여름드라이브", "summer drive", "드라이브음악", "summer vibes", "road trip", "AI음악", "여름음악"],
    "drive_night":  ["aisence", "야간드라이브", "night drive", "새벽드라이브", "드라이브음악", "midnight drive", "AI음악", "새벽감성"],
    "drive_hype":   ["aisence", "신나는드라이브", "hype drive", "드라이브음악", "energetic music", "업템포", "AI음악", "신나는음악"],
    "drive_chill":  ["aisence", "여유로운드라이브", "chill drive", "드라이브음악", "chill music", "relaxing drive", "AI음악", "힐링드라이브"],
    "drive_rain":   ["aisence", "비오는날드라이브", "rainy drive", "드라이브음악", "rain music", "빗소리", "AI음악", "감성드라이브"],
}

# 장르별 설명 템플릿
COPYRIGHT_NOTICE = "\n\n---\n해당 영상에 사용된 모든 음악, 가사는 @AIsense가 직접 제작한 콘텐츠입니다.\n무단 사용 및 재 업로드는 금지되어 있습니다."

GENRE_DESC = {
    "lofi":         "🎵 따뜻한 로파이 비트, 오늘도 수고했어요.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #lofi #lofimusic #AI음악",
    "heal":         "🌿 지친 하루 끝에 듣는 힐링 음악.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #힐링음악 #healingmusic #AI음악",
    "bass":         "🌑 무거운 베이스, 혼자만의 시간.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #bassmusic #베이스음악 #AI음악",
    "dawn":         "🌙 아무도 없는 새벽, 혼자만의 감성.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #새벽감성 #새벽음악 #AI음악",
    "drive":        "🚗 야간 드라이브, 아무 생각 없이 달릴 때.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #드라이브음악 #nightdrive #AI음악",
    "drive_summer": "☀️ 창문 활짝 열고, 여름 햇살 맞으며 달릴 때.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #여름드라이브 #summerdrive #AI음악",
    "drive_night":  "🌃 불빛 가득한 도시, 아무 생각 없이 달리는 새벽.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #야간드라이브 #nightdrive #AI음악",
    "drive_hype":   "🔥 액셀 밟고 싶어지는 그 느낌, 신나는 드라이브.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #신나는드라이브 #hypedrive #AI음악",
    "drive_chill":  "🛣️ 한적한 도로, 여유롭게 흘러가는 시간.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #여유로운드라이브 #chilldrive #AI음악",
    "drive_rain":   "🌧️ 빗소리와 함께, 감성이 차오르는 드라이브.\n\nAI로 만든 감성 음악 채널, aisence\n매주 새로운 트랙을 업로드합니다.\n\n구독 & 좋아요는 큰 힘이 됩니다 🙏\n\n#aisence #비오는날드라이브 #rainydrive #AI음악",
}


def get_authenticated_service():
    """YouTube API 인증"""
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print("\n❌ client_secrets.json 파일이 없습니다.")
                print("   Google Cloud Console에서 OAuth 클라이언트 ID를 다운로드하고")
                print(f"   {CLIENT_SECRETS_FILE} 경로에 저장해주세요.\n")
                raise FileNotFoundError("client_secrets.json 없음")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, authorization_prompt_message="",
                                          extra_params={"prompt": "select_account consent"})

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: str, title: str, genre: str = "lofi",
                 description: str = None, scheduled_time: str = None,
                 thumbnail_path: str = None):
    """
    유튜브 영상 업로드

    Args:
        video_path: 업로드할 영상 파일 경로
        title: 영상 제목
        genre: 장르 코드 (lofi / heal / bass / dawn / drive)
        description: 설명 (없으면 장르별 기본값 사용)
        scheduled_time: 예약 업로드 시간 (ISO 형식: "2026-03-21T18:00:00+09:00")
        thumbnail_path: 썸네일 이미지 경로 (선택)
    """
    genre = genre.lower()
    tags = GENRE_TAGS.get(genre, GENRE_TAGS["lofi"])
    desc = (description or GENRE_DESC.get(genre, GENRE_DESC["lofi"])) + COPYRIGHT_NOTICE

    # 공개 상태 설정
    if scheduled_time:
        privacy_status = "private"
        publish_at = scheduled_time
    else:
        privacy_status = "public"
        publish_at = None

    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "10",  # 10 = Music
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if publish_at:
        body["status"]["publishAt"] = publish_at

    print(f"[1/3] YouTube 인증 중...")
    youtube = get_authenticated_service()

    print(f"[2/3] 영상 업로드 중: {os.path.basename(video_path)}")
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  업로드 진행률: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"[3/3] 업로드 완료! https://www.youtube.com/watch?v={video_id}")

    # 썸네일 업로드 (선택)
    if thumbnail_path and os.path.exists(thumbnail_path):
        print("  썸네일 업로드 중...")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print("  썸네일 업로드 완료!")

    return video_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="aisence 유튜브 자동 업로드")
    parser.add_argument("--video", required=True, help="업로드할 영상 파일 경로")
    parser.add_argument("--title", required=True, help="영상 제목")
    parser.add_argument("--genre", default="lofi",
                        choices=["lofi", "heal", "bass", "dawn",
                                 "drive", "drive_summer", "drive_night",
                                 "drive_hype", "drive_chill", "drive_rain"],
                        help="장르 (기본: lofi)")
    parser.add_argument("--description", default=None, help="영상 설명 (선택)")
    parser.add_argument("--schedule", default=None,
                        help='예약 업로드 시간 (예: "2026-03-21T18:00:00+09:00")')
    parser.add_argument("--thumbnail", default=None, help="썸네일 이미지 경로 (선택)")
    args = parser.parse_args()

    upload_video(args.video, args.title, args.genre,
                 args.description, args.schedule, args.thumbnail)
