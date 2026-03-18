"""
aisence — MP3 여러 개 + 이미지 1장 → MP4 자동 생성
사용법:
  python merge_video.py --image ../images/cover.png --audio ../audio/1.mp3 ../audio/2.mp3 ../audio/3.mp3
  python merge_video.py --image ../images/cover.png --audio_dir ../audio --resolution 4k
"""

import argparse
import os
import glob
from moviepy import AudioFileClip, ImageClip, concatenate_audioclips
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut


RESOLUTIONS = {
    "1080p": (1920, 1080),
    "4k":    (3840, 2160),
}


def merge_video(
    image_path: str,
    audio_paths: list,
    output_path: str = None,
    resolution: str = "1080p",
    fps: int = 30,
    fade_in: float = 2.0,
    fade_out: float = 3.0,
):
    """
    MP3 여러 개를 순서대로 이어붙이고 이미지를 배경으로 MP4 생성

    Args:
        image_path : 배경 이미지 경로 (.png / .jpg)
        audio_paths: MP3 파일 경로 리스트 (순서대로)
        output_path: 출력 경로 (없으면 output/ 폴더에 자동 저장)
        resolution : "1080p" 또는 "4k"
        fps        : 프레임레이트 (기본 30)
        fade_in    : 첫 곡 페이드인 시간 (초)
        fade_out   : 마지막 곡 페이드아웃 시간 (초)
    """
    if not audio_paths:
        raise ValueError("오디오 파일이 없어요.")

    width, height = RESOLUTIONS.get(resolution, RESOLUTIONS["1080p"])

    # 출력 경로 자동 설정
    if output_path is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(audio_paths[0])), "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "merged_final.mp4")

    # 1. 오디오 순서대로 이어붙이기
    print(f"[1/4] 오디오 {len(audio_paths)}개 이어붙이는 중...")
    clips = []
    for i, path in enumerate(audio_paths):
        print(f"      {i+1}. {os.path.basename(path)}")
        clips.append(AudioFileClip(path))

    # 첫 곡 페이드인, 마지막 곡 페이드아웃 적용
    clips[0] = clips[0].with_effects([AudioFadeIn(fade_in)])
    clips[-1] = clips[-1].with_effects([AudioFadeOut(fade_out)])

    combined_audio = concatenate_audioclips(clips)
    total_duration = combined_audio.duration
    print(f"      총 재생시간: {int(total_duration // 60)}분 {int(total_duration % 60)}초")

    # 2. 이미지를 배경으로 설정
    print(f"[2/4] 이미지 불러오는 중: {image_path}")
    video = (
        ImageClip(image_path)
        .resized((width, height))
        .with_duration(total_duration)
        .with_audio(combined_audio)
    )

    # 3. 렌더링
    print(f"[3/4] 영상 렌더링 중... ({resolution} / {fps}fps / 시간이 걸릴 수 있어요)")
    video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    print(f"[4/4] 완료! 저장 위치: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MP3 여러 개 + 이미지 → MP4 자동 생성")
    parser.add_argument("--image", required=True, help="배경 이미지 파일 경로")

    audio_group = parser.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--audio", nargs="+", help="MP3 파일 경로 (순서대로 나열)")
    audio_group.add_argument("--audio_dir", help="MP3 파일이 있는 폴더 (파일명 순으로 자동 정렬)")

    parser.add_argument("--output", default=None, help="출력 파일 경로 (선택)")
    parser.add_argument("--resolution", default="1080p", choices=["1080p", "4k"], help="해상도 (기본 1080p)")
    parser.add_argument("--fps", type=int, default=30, help="프레임레이트 (기본 30)")
    parser.add_argument("--fade_in", type=float, default=2.0, help="첫 곡 페이드인 시간 (초)")
    parser.add_argument("--fade_out", type=float, default=3.0, help="마지막 곡 페이드아웃 시간 (초)")
    args = parser.parse_args()

    if args.audio_dir:
        audio_files = sorted(glob.glob(os.path.join(args.audio_dir, "*.mp3")))
        if not audio_files:
            raise FileNotFoundError(f"{args.audio_dir} 폴더에 MP3 파일이 없어요.")
    else:
        audio_files = args.audio

    merge_video(
        image_path=args.image,
        audio_paths=audio_files,
        output_path=args.output,
        resolution=args.resolution,
        fps=args.fps,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
    )
