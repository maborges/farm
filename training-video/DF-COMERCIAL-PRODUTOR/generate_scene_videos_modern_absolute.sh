#!/usr/bin/env bash
# generate_scene_videos_modern_absolute.sh
# -------------------------------------------------
# Generates one MP4 per scene using the modern‑producer images that were
# created as artifacts. No audio or subtitles are added – you can overlay later.

# Absolute paths to the artifact images (generated earlier)
IMG_01="/home/borgus/.gemini/antgravity-ide/brain/e772626c-be6c-4759-a948-882475571203/scene_01_modern_1791854911159.jpg"
IMG_02="/home/borgus/.gemini/antgravity-ide/brain/e772626c-be6c-4759-a948-882475571203/scene_02_modern_1791854928502.jpg"
IMG_03="/home/borgus/.gemini/antgravity-ide/brain/e772626c-be6c-4759-a948-882475571203/scene_03_modern_1791854946648.jpg"
IMG_04="/home/borgus/.gemini/antgravity-ide/brain/e772626c-be6c-4759-a948-882475571203/scene_04_modern_1791854964162.jpg"
IMG_05="/home/borgus/.gemini/antgravity-ide/brain/e772626c-be6c-4759-a948-882475571203/scene_05_modern_1791854980225.jpg"
IMG_06="/home/borgus/.gemini/antgravity-ide/brain/e772626c-be6c-4759-a948-882475571203/scene_06_modern_1791854994077.jpg"

OUT_DIR="./scene-videos-modern"
mkdir -p "$OUT_DIR"

make_scene_video() {
    local idx=$1
    local img_var="IMG_${idx}"
    local img_path="${!img_var}"
    local out="${OUT_DIR}/Cena_${idx}.mp4"

    if [[ ! -f "$img_path" ]]; then
        echo "⚠️  Image not found: $img_path"
        return 1
    fi

    # Fixed duration – you may adapt per scene later
    local duration=5
    ffmpeg -y -loglevel error -loop 1 -i "$img_path" -c:v libx264 -t $duration -pix_fmt yuv420p -vf "scale=1920:1080,format=yuv420p" -r 30 "$out"
    echo "✅  Cena $idx → $out"
}

for i in $(seq 1 6); do
    make_scene_video "$i"
done

echo "🎉  All modern scene videos generated in: $OUT_DIR"
