"""
카페재즈시리즈 — 전체 합본 플레이리스트 영상 생성
PNG 배경 + 전체 MP3 이어붙이기 → MP4 1개 출력
"""

import os
import glob
from moviepy import AudioFileClip, ImageClip, concatenate_audioclips
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut

FOLDER = r"D:\claude_proj\music_ai_proj\music_file\카페재즈시리즈"
OUTPUT_NAME = "카페재즈시리즈_플레이리스트.mp4"

def main():
    # PNG 배경 찾기
    png_files = glob.glob(os.path.join(FOLDER, "*.png"))
    if not png_files:
        print("[오류] PNG 파일을 찾을 수 없어요.")
        return
    image_path = png_files[0]
    print(f"[배경 이미지] {os.path.basename(image_path)}")

    # MP3 파일 정렬해서 불러오기
    mp3_files = sorted(glob.glob(os.path.join(FOLDER, "*.mp3")))
    if not mp3_files:
        print("[오류] MP3 파일을 찾을 수 없어요.")
        return

    print(f"\n[트랙 목록] 총 {len(mp3_files)}개")
    for i, f in enumerate(mp3_files, 1):
        print(f"  {i:02d}. {os.path.basename(f)}")

    # 오디오 이어붙이기
    print("\n[1/4] 오디오 병합 중...")
    clips = [AudioFileClip(f) for f in mp3_files]
    combined_audio = concatenate_audioclips(clips)

    # 페이드인/아웃
    combined_audio = combined_audio.with_effects([
        AudioFadeIn(2.0),
        AudioFadeOut(4.0),
    ])

    total_min = int(combined_audio.duration // 60)
    total_sec = int(combined_audio.duration % 60)
    print(f"    총 재생시간: {total_min}분 {total_sec}초")

    # 이미지 + 오디오 합치기
    print("[2/4] 이미지 불러오는 중...")
    video = (
        ImageClip(image_path)
        .with_duration(combined_audio.duration)
        .with_audio(combined_audio)
    )

    # 출력 경로 (같은 폴더)
    output_path = os.path.join(FOLDER, OUTPUT_NAME)

    print("[3/4] 영상 렌더링 중... (시간이 걸릴 수 있어요)")
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    print(f"\n[4/4] 완료! 저장 위치:\n  {output_path}")

    # 클립 해제
    for c in clips:
        c.close()

if __name__ == "__main__":
    main()
