#!/usr/bin/env bash
# generate_scene_videos_modern.sh
# -------------------------------------------------
# Generates one MP4 per scene using the modern‑producer images.
# No audio or subtitles are added – you can edit/overlay later.

# Directories (relative to this script)
IMG_DIR="./images"
SCENE_DIR="./scene-videos-modern"
mkdir -p "$SCENE_DIR"

make_scene_video() {
    local idx=$1
    local pad_idx=$(printf "%02d" "$idx")
    local img="${IMG_DIR}/Cena_${pad_idx}_modern.jpg"
    local out="${SCENE_DIR}/Cena_${pad_idx}.mp4"

    if [[ ! -f "$img" ]]; then
        echo "⚠️  Image not found: $img"
        return 1
    fi

    # Fixed duration (seconds) – adjust if needed.
    local duration=5
    ffmpeg -y -loglevel error -loop 1 -i "$img" -c:v libx264 -t $duration -pix_fmt yuv420p -vf "scale=1920:1080,format=yuv420p" -r 30 "$out"
    echo "✅  Cena $idx → $out"
}

for i in $(seq 1 6); do
    make_scene_video "$i"
 done

echo "🎉  All modern scene videos generated in: $SCENE_DIR"
