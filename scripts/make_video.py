"""
aisence — 이미지 + 오디오 → MP4 자동 생성
사용법: python make_video.py --image ../images/xxx.png --audio ../audio/xxx.mp3
"""

import argparse
import os
from moviepy import AudioFileClip, ImageClip


def make_video(image_path: str, audio_path: str, output_path: str = None,
               fade_in: float = 2.0, fade_out: float = 3.0):
    """
    이미지 + 오디오 → MP4 영상 생성

    Args:
        image_path: 이미지 파일 경로 (.png / .jpg)
        audio_path: 오디오 파일 경로 (.mp3 / .wav)
        output_path: 출력 파일 경로 (없으면 output/ 폴더에 자동 저장)
        fade_in: 페이드인 시간 (초)
        fade_out: 페이드아웃 시간 (초)
    """
    # 출력 경로 자동 설정
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = os.path.join(os.path.dirname(os.path.dirname(audio_path)), "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base_name}_final.mp4")

    print(f"[1/4] 오디오 불러오는 중: {audio_path}")
    audio = AudioFileClip(audio_path)

    # 페이드인/아웃 적용
    audio = audio.with_effects([
        __import__('moviepy.audio.fx', fromlist=['AudioFadeIn']).AudioFadeIn(fade_in),
        __import__('moviepy.audio.fx', fromlist=['AudioFadeOut']).AudioFadeOut(fade_out),
    ])

    print(f"[2/4] 이미지 불러오는 중: {image_path}")
    video = (
        ImageClip(image_path)
        .with_duration(audio.duration)
        .with_audio(audio)
    )

    print(f"[3/4] 영상 렌더링 중... (시간이 걸릴 수 있어요)")
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    print(f"[4/4] 완료! 저장 위치: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="aisence 영상 자동 생성")
    parser.add_argument("--image", required=True, help="이미지 파일 경로")
    parser.add_argument("--audio", required=True, help="오디오 파일 경로")
    parser.add_argument("--output", default=None, help="출력 파일 경로 (선택)")
    parser.add_argument("--fade-in", type=float, default=2.0, help="페이드인 시간 (초, 기본 2)")
    parser.add_argument("--fade-out", type=float, default=3.0, help="페이드아웃 시간 (초, 기본 3)")
    args = parser.parse_args()

    make_video(args.image, args.audio, args.output, args.fade_in, args.fade_out)
