#!/usr/bin/env bash
set -euo pipefail

LESSON_ID="DF-COMERCIAL-PRODUTOR"
BASE_DIR="/opt/lampp/htdocs/farm/training-video/${LESSON_ID}"
SCENE_DIR="${BASE_DIR}/scene-videos"
WAV_DIR="${BASE_DIR}"
SRT_DIR="${BASE_DIR}"

mkdir -p "${SCENE_DIR}"

make_scene_video() {
    local idx=$1
    # Sempre usar zero‑padding (01,02,...)
    local pad_idx=$(printf "%02d" ${idx})
    local wav="${WAV_DIR}/Cena_${pad_idx}.wav"
    local srt="${SRT_DIR}/Cena_${pad_idx}.srt"
    local out="${SCENE_DIR}/Cena_${pad_idx}.mp4"
    if [[ ! -f "${wav}" ]]; then
        echo "⚠️  Audio not found: ${wav}" >&2
        return 1
    fi
    local duration_ms=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${wav}" | awk '{printf "%.0f", $1 * 1000}')
    ffmpeg -y -f lavfi -i color=size=1920x1080:rate=30:color=0x000000 -t $(awk "BEGIN{printf \"%.3f\", ${duration_ms}/1000}") -c:v libx264 -pix_fmt yuv420p -r 30 -metadata title="Cena ${idx} – ${LESSON_ID}" "${SCENE_DIR}/tmp_${idx}.mp4" > /dev/null 2>&1
    if [[ -f "${srt}" ]]; then
        ffmpeg -y -i "${SCENE_DIR}/tmp_${idx}.mp4" -i "${wav}" -vf "subtitles='${srt}':force_style='Fontsize=28,PrimaryColour=&HFFFFFF&'" -c:v libx264 -c:a aac -b:a 128k -shortest "${out}" > /dev/null 2>&1
    else
        ffmpeg -y -i "${SCENE_DIR}/tmp_${idx}.mp4" -i "${wav}" -c:v libx264 -c:a aac -b:a 128k -shortest "${out}" > /dev/null 2>&1
    fi
    rm -f "${SCENE_DIR}/tmp_${idx}.mp4"
    echo "✅  Cena ${idx} → ${out}"
}

for i in $(seq 1 6); do
    make_scene_video "$i"
 done

echo "🎉  All scene videos generated in: ${SCENE_DIR}"
