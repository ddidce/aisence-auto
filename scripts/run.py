"""
aisence — 통합 실행 스크립트
이미지 + 오디오 → 영상 생성 → 유튜브 업로드 한 번에 처리

사용법:
  python run.py --image ../images/xxx.png --audio ../audio/xxx.mp3 \
                --title "새벽 감성 lofi ~ 잠 못 이루는 밤에 🎵 aisence" \
                --genre dawn \
                --schedule "2026-03-21T18:00:00+09:00"
"""

import argparse
from make_video import make_video
from upload_youtube import upload_video


def run(image_path, audio_path, title, genre,
        description=None, schedule=None, thumbnail_path=None,
        fade_in=2.0, fade_out=3.0):

    print("=" * 50)
    print("  aisence 자동화 파이프라인 시작")
    print("=" * 50)

    # Step 1: 영상 생성
    print("\n▶ STEP 1: 영상 생성")
    output_path = make_video(image_path, audio_path,
                             fade_in=fade_in, fade_out=fade_out)

    # Step 2: 유튜브 업로드
    print("\n▶ STEP 2: 유튜브 업로드")
    video_id = upload_video(output_path, title, genre,
                            description, schedule, thumbnail_path)

    print("\n" + "=" * 50)
    print("  ✅ 모든 작업 완료!")
    print(f"  영상: {output_path}")
    print(f"  유튜브: https://www.youtube.com/watch?v={video_id}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="aisence 통합 실행")
    parser.add_argument("--image", required=True, help="이미지 파일 경로")
    parser.add_argument("--audio", required=True, help="오디오 파일 경로")
    parser.add_argument("--title", required=True, help="유튜브 영상 제목")
    parser.add_argument("--genre", default="lofi",
                        choices=["lofi", "heal", "bass", "dawn",
                                 "drive", "drive_summer", "drive_night",
                                 "drive_hype", "drive_chill", "drive_rain"],
                        help="장르 (기본: lofi)")
    parser.add_argument("--description", default=None, help="영상 설명 (선택)")
    parser.add_argument("--schedule", default=None,
                        help='예약 업로드 시간 (예: "2026-03-21T18:00:00+09:00")')
    parser.add_argument("--thumbnail", default=None, help="썸네일 이미지 경로 (선택)")
    parser.add_argument("--fade-in", type=float, default=2.0, help="페이드인 초 (기본 2)")
    parser.add_argument("--fade-out", type=float, default=3.0, help="페이드아웃 초 (기본 3)")
    args = parser.parse_args()

    run(args.image, args.audio, args.title, args.genre,
        args.description, args.schedule, args.thumbnail,
        args.fade_in, args.fade_out)
