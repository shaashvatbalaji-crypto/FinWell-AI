import os
import sys
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio
import imageio_ffmpeg

# Set directories
BASE_DIR = r"C:\Users\shaas\OneDrive\Desktop\FinWell_AI\FinWell_AI"
ASSETS_DIR = os.path.join(BASE_DIR, "docs", "assets")
VIDEO_ASSETS_DIR = os.path.join(ASSETS_DIR, "video")
os.makedirs(VIDEO_ASSETS_DIR, exist_ok=True)

OUTPUT_MP4 = os.path.join(ASSETS_DIR, "finwell-ai-intro.mp4")
OUTPUT_GIF = os.path.join(ASSETS_DIR, "finwell-ai-intro.gif")
OUTPUT_WEBP = os.path.join(ASSETS_DIR, "finwell-ai-intro.webp")

W, H = 1920, 1080
FPS = 30

def get_font(name="segoeui.ttf", size=24, bold=False):
    font_file = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = os.path.join(r"C:\Windows\Fonts", font_file)
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

font_title = get_font(size=44, bold=True)
font_sub = get_font(size=26, bold=False)
font_badge = get_font(size=20, bold=True)

def load_and_cover(path, target_w=W, target_h=H):
    """Load image and crop/scale to exactly target_w x target_h preserving aspect ratio."""
    im = Image.open(path).convert("RGB")
    src_w, src_h = im.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return im.crop((left, top, left + target_w, top + target_h))

def apply_ken_burns(base_img, progress, zoom_start=1.0, zoom_end=1.05, pan_x=0.0, pan_y=0.0):
    """Applies smooth zoom and pan to base image."""
    current_zoom = zoom_start + (zoom_end - zoom_start) * progress
    crop_w = int(W / current_zoom)
    crop_h = int(H / current_zoom)
    
    # Calculate crop center with panning
    center_x = (W / 2) + (pan_x * W * (progress - 0.5))
    center_y = (H / 2) + (pan_y * H * (progress - 0.5))
    
    left = max(0, min(W - crop_w, int(center_x - crop_w / 2)))
    top = max(0, min(H - crop_h, int(center_y - crop_h / 2)))
    
    cropped = base_img.crop((left, top, left + crop_w, top + crop_h))
    return cropped.resize((W, H), Image.Resampling.BILINEAR)

def draw_overlay(img, title, subtitle, badge_text=None, alert=False):
    """Renders sleek fintech glassmorphism lower-third banner."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    banner_w = 1200
    banner_h = 150 if badge_text else 130
    x0 = (W - banner_w) // 2
    y0 = H - banner_h - 60
    x1 = x0 + banner_w
    y1 = y0 + banner_h

    # Glass background with subtle border
    bg_color = (15, 23, 42, 220) if not alert else (50, 10, 15, 225)
    border_color = (52, 211, 153, 200) if not alert else (239, 68, 68, 220)
    
    # Outer glow
    draw.rounded_rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], radius=16, fill=(0, 0, 0, 100))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=bg_color, outline=border_color, width=2)
    
    # Left accent vertical pill
    draw.rounded_rectangle([x0 + 16, y0 + 18, x0 + 24, y1 - 18], radius=4, fill=border_color)

    # Texts
    tx = x0 + 44
    ty = y0 + 20

    if badge_text:
        badge_bg = (6, 78, 59, 255) if not alert else (153, 27, 27, 255)
        badge_txt_color = (52, 211, 153) if not alert else (254, 202, 202)
        draw.rounded_rectangle([tx, ty, tx + 180, ty + 28], radius=6, fill=badge_bg)
        draw.text((tx + 12, ty + 4), badge_text, fill=badge_txt_color, font=font_badge)
        ty += 34

    draw.text((tx, ty), title, fill=(255, 255, 255), font=font_title)
    draw.text((tx, ty + 50), subtitle, fill=(203, 213, 225), font=font_sub)

    # Composite overlay onto img
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

# Shot definitions
shots_config = [
    {
        "name": "shot1_coffee",
        "file": "scene1_coffee_upi.jpg",
        "frames": 75,
        "zoom": (1.0, 1.06),
        "pan": (0.02, 0.0),
        "title": "EVERY DAY, MONEY MOVES.",
        "subtitle": "A morning coffee. A quick UPI scan. Invisible transactions begin.",
        "badge": "01 • DAILY TRANSACTIONS"
    },
    {
        "name": "shot2_grocery",
        "file": "scene1b_grocery_nfc.jpg",
        "frames": 75,
        "zoom": (1.0, 1.05),
        "pan": (-0.02, 0.01),
        "title": "PAYMENTS HAPPEN IN SECONDS.",
        "subtitle": "Supermarket checkout • Contactless taps • Silent expenses accumulate.",
        "badge": "02 • CONTACTLESS SPEED"
    },
    {
        "name": "shot3_sofa_bills",
        "file": "scene2_sofa_bills.jpg",
        "frames": 75,
        "zoom": (1.0, 1.05),
        "pan": (0.01, -0.01),
        "title": "PAYMENTS. TRANSFERS. SUBSCRIPTIONS.",
        "subtitle": "Rent debits, OTT renewals, food orders — without conscious tracking.",
        "badge": "03 • INVISIBLE ACCUMULATION"
    },
    {
        "name": "shot4_sofa_track",
        "file": "scene2_sofa_bills.jpg",
        "frames": 55,
        "zoom": (1.05, 1.08),
        "pan": (0.0, 0.0),
        "title": "ARE YOU KEEPING TRACK?",
        "subtitle": "Dozens of transactions every week. Do you know where it all went?",
        "badge": "04 • THE DILEMMA",
        "alert": True
    },
    {
        "name": "shot5_night_stress",
        "file": "scene3_night_frustration.jpg",
        "frames": 75,
        "zoom": (1.0, 1.06),
        "pan": (0.0, 0.02),
        "title": "ONE MONTH. HUNDREDS OF TRANSACTIONS.",
        "subtitle": "Late-night financial fatigue trying to decipher dense bank statements.",
        "badge": "05 • THE MONTH-END REALITY",
        "alert": True
    },
    {
        "name": "shot6_confusing_stmt",
        "file": "scene3b_confusing_statement.png",
        "frames": 75,
        "zoom": (1.0, 1.03),
        "pan": (0.0, 0.01),
        "title": "WHERE DID YOUR MONEY GO?",
        "subtitle": "Cryptic descriptions • Unmatched transfers • Ambiguous balances.",
        "badge": "06 • UNSTRUCTURED DATA",
        "alert": True
    },
    {
        "name": "shot7_tech_ingest",
        "file": "scene4a_ingestion_extraction.png",
        "frames": 90,
        "zoom": (1.0, 1.04),
        "pan": (0.02, 0.0),
        "title": "INTRODUCING FINWELL AI",
        "subtitle": "Automated PDF Stream Extraction • ChromaDB Semantic Categorization.",
        "badge": "STAGE 1 • AI INGESTION"
    },
    {
        "name": "shot8_tech_recon",
        "file": "scene4b_reconciliation_matrix.png",
        "frames": 90,
        "zoom": (1.0, 1.03),
        "pan": (0.0, 0.02),
        "title": "TRI-ENGINE RECONCILIATION MATRIX",
        "subtitle": "Transfer Pairing • Refund Matching • Sliding-Window Duplicate Elimination.",
        "badge": "STAGE 2 • FULL RECONCILIATION"
    },
    {
        "name": "shot9_clarity",
        "file": "scene5_peace_clarity.jpg",
        "frames": 65,
        "zoom": (1.06, 1.0),
        "pan": (-0.01, 0.0),
        "title": "YOUR MONEY MOVES EVERY DAY.",
        "subtitle": "FinWell AI helps you understand every transaction with total clarity.",
        "badge": "THE RESULT • PEACE OF MIND"
    },
    {
        "name": "shot10_title_card",
        "file": "scene5b_title_card.png",
        "frames": 65,
        "zoom": (1.0, 1.02),
        "pan": (0.0, 0.0),
        "title": "EXTRACT. UNDERSTAND. RECONCILE.",
        "subtitle": "Take control of your personal finances with FinWell AI.",
        "badge": "FINWELL AI"
    }
]

def render_video():
    print("Pre-loading all scene master images...")
    loaded_images = {}
    for shot in shots_config:
        f = shot["file"]
        if f not in loaded_images:
            full_path = os.path.join(VIDEO_ASSETS_DIR, f)
            print(f"Loading {full_path}...")
            loaded_images[f] = load_and_cover(full_path)

    total_frames = sum(s["frames"] for s in shots_config)
    print(f"Total shots: {len(shots_config)}, Total target frames: {total_frames} (~{total_frames/FPS:.1f}s)")

    print(f"Writing master MP4 to: {OUTPUT_MP4} ...")
    writer = imageio.get_writer(
        OUTPUT_MP4,
        fps=FPS,
        codec="libx264",
        quality=9,
        pixelformat="yuv420p"
    )

    CROSSFADE_FRAMES = 12
    all_raw_frames = []

    for idx, shot in enumerate(shots_config):
        print(f"Rendering shot {idx+1}/{len(shots_config)}: {shot['name']} ({shot['frames']} frames)...")
        base_img = loaded_images[shot["file"]]
        shot_frames = []
        n_frames = shot["frames"]

        for i in range(n_frames):
            prog = i / max(1, n_frames - 1)
            frame_img = apply_ken_burns(
                base_img,
                progress=prog,
                zoom_start=shot["zoom"][0],
                zoom_end=shot["zoom"][1],
                pan_x=shot["pan"][0],
                pan_y=shot["pan"][1]
            )

            # Draw overlay banner
            frame_with_overlay = draw_overlay(
                frame_img,
                title=shot["title"],
                subtitle=shot["subtitle"],
                badge_text=shot.get("badge"),
                alert=shot.get("alert", False)
            )
            shot_frames.append(frame_with_overlay)

        # Crossfade with previous shot if applicable
        if not all_raw_frames:
            all_raw_frames.extend(shot_frames)
        else:
            # Alpha blend last CROSSFADE_FRAMES
            tail_start = len(all_raw_frames) - CROSSFADE_FRAMES
            for k in range(CROSSFADE_FRAMES):
                alpha = (k + 1) / (CROSSFADE_FRAMES + 1)
                prev_f = all_raw_frames[tail_start + k]
                next_f = shot_frames[k]
                blended = Image.blend(prev_f, next_f, alpha)
                all_raw_frames[tail_start + k] = blended
            all_raw_frames.extend(shot_frames[CROSSFADE_FRAMES:])

    print(f"Generated {len(all_raw_frames)} composited frames. Encoding to MP4...")
    for f in all_raw_frames:
        writer.append_data(np.array(f))
    writer.close()
    print(f"MP4 generated successfully! File size: {os.path.getsize(OUTPUT_MP4) / (1024*1024):.2f} MB")

    # Generate Optimized GIF via ffmpeg 2-pass palettegen
    print("Generating optimized animated GIF via ffmpeg...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # 800px width at 15fps provides pristine readability while keeping file size GitHub-friendly (~10MB)
    gif_filter = (
        "fps=15,scale=800:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=128:reserve_transparent=0[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=3"
    )
    cmd_gif = [
        ffmpeg_exe, "-y",
        "-i", OUTPUT_MP4,
        "-vf", gif_filter,
        OUTPUT_GIF
    ]
    subprocess.check_call(cmd_gif)
    print(f"GIF generated successfully! File size: {os.path.getsize(OUTPUT_GIF) / (1024*1024):.2f} MB")

    # Generate Animated WebP
    print("Generating animated WebP...")
    cmd_webp = [
        ffmpeg_exe, "-y",
        "-i", OUTPUT_MP4,
        "-vcodec", "libwebp",
        "-filter:v", "fps=18,scale=960:-1:flags=lanczos",
        "-lossless", "0",
        "-compression_level", "4",
        "-q:v", "70",
        "-loop", "0",
        OUTPUT_WEBP
    ]
    subprocess.check_call(cmd_webp)
    print(f"WebP generated successfully! File size: {os.path.getsize(OUTPUT_WEBP) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    render_video()
    print("All deliverables generated successfully!")
