from pathlib import Path

import cv2
from ultralytics import YOLO
import subprocess
from .analytics import TrafficAnalytics
from .api_client import save_vehicle


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

CONFIDENCE = 0.25
MIN_TRACK_FRAMES = 15


# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

print("Loading trained YOLO model...")

model = YOLO(str(MODEL_PATH))

print("Model loaded successfully.")
print("Classes:", model.names)

# --------------------------------------------------
# CONVERT VIDEO FOR BROWSER PLAYBACK
# --------------------------------------------------

def convert_to_browser_mp4(
    input_video: str | Path,
    output_video: str | Path
):
    ffmpeg_path = (
        r"C:\Users\MOHAN AKASH\AppData\Local\Microsoft\WinGet\Packages"
        r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
    )

    command = [
        ffmpeg_path,
        "-y",
        "-i", str(input_video),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(output_video),
    ]

    print("\nConverting video for browser playback...")

    subprocess.run(
        command,
        check=True
    )

    print("Browser-compatible video created.")
# --------------------------------------------------
# PROCESS VIDEO
# --------------------------------------------------

def process_video(
    video_path: str | Path,
    output_video: str | Path | None = None,
    progress_callback=None
):
    """
    Process any uploaded traffic video using
    YOLO + ByteTrack + TrafficAnalytics.

    progress_callback:
        Optional function receiving:
            progress, current_frame, total_frames

    Returns:
        processed video path
        vehicle analytics
        video information
    """

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    # --------------------------------------------------
    # OUTPUT PATH
    # --------------------------------------------------

    if output_video is None:
        output_video = (
            OUTPUT_DIR /
            f"{video_path.stem}_processed.mp4"
        )
    else:
        output_video = Path(output_video)

    output_video.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # ANALYTICS
    # --------------------------------------------------

    analytics = TrafficAnalytics(
        min_track_frames=MIN_TRACK_FRAMES
    )

    # --------------------------------------------------
    # VIDEO
    # --------------------------------------------------

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {video_path}"
        )

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 30.0

    width = int(
        cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    print("\n----------------------------------------")
    print("Starting traffic video processing")
    print("----------------------------------------")

    print(f"Input: {video_path}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Total frames: {total_frames}")

    # --------------------------------------------------
    # INITIAL PROGRESS
    # --------------------------------------------------

    if progress_callback:
        progress_callback(
            0,
            0,
            total_frames
        )

    # --------------------------------------------------
    # OUTPUT VIDEO
    # --------------------------------------------------

    temp_output = output_video.with_name(
        output_video.stem + "_temp.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    writer = cv2.VideoWriter(
        str(temp_output),
        fourcc,
        fps,
        (width, height)
    )
    # --------------------------------------------------
    # TRACKING
    # --------------------------------------------------

    frame_count = 0

    last_progress = -1

    while True:

        success, frame = cap.read()

        if not success:
            break

        frame_count += 1

        # --------------------------------------------------
        # YOLO + BYTE TRACK
        # --------------------------------------------------

        results = model.track(
            frame,
            tracker="bytetrack.yaml",
            persist=True,
            conf=CONFIDENCE,
            verbose=False
        )

        result = results[0]

        # --------------------------------------------------
        # TRACKED VEHICLES
        # --------------------------------------------------

        if (
            result.boxes is not None
            and result.boxes.id is not None
        ):

            boxes = (
                result.boxes.xyxy
                .cpu()
                .numpy()
            )

            track_ids = (
                result.boxes.id
                .int()
                .cpu()
                .tolist()
            )

            classes = (
                result.boxes.cls
                .int()
                .cpu()
                .tolist()
            )

            for box, track_id, cls_id in zip(
                boxes,
                track_ids,
                classes
            ):

                x1, y1, x2, y2 = box

                center_x = (
                    x1 + x2
                ) / 2

                center_y = (
                    y1 + y2
                ) / 2

                vehicle_type = model.names[
                    cls_id
                ]

                analytics.update(
                    track_id=track_id,
                    vehicle_type=vehicle_type,
                    center_x=center_x,
                    center_y=center_y
                )

        # --------------------------------------------------
        # DRAW TRACKING RESULTS
        # --------------------------------------------------

        annotated_frame = result.plot()

        writer.write(
            annotated_frame
        )

        # --------------------------------------------------
        # REAL PROGRESS
        # --------------------------------------------------

        if total_frames > 0:

            progress = int(
                (frame_count / total_frames) * 100
            )

            # Send update whenever percentage changes
            if progress != last_progress:

                last_progress = progress

                if progress_callback:
                    progress_callback(
                        progress,
                        frame_count,
                        total_frames
                    )

            # Terminal logging every 10%
            if progress % 10 == 0:
                print(
                    f"Processed "
                    f"{frame_count}/"
                    f"{total_frames} "
                    f"({progress}%)"
                )

    # --------------------------------------------------
    # CLEANUP
    # --------------------------------------------------

    cap.release()
    writer.release()

    # Convert temporary MP4 to browser-compatible H.264 MP4
    convert_to_browser_mp4(
        temp_output,
        output_video
    )

    # Remove temporary video
    temp_output.unlink(
        missing_ok=True
    )

    # --------------------------------------------------
    # FINAL PROGRESS
    # --------------------------------------------------

    if progress_callback:
        progress_callback(
            100,
            frame_count,
            total_frames
        )

    # --------------------------------------------------
    # FINAL ANALYTICS
    # --------------------------------------------------

    vehicle_results = (
        analytics.get_results()
    )

    print("\n----------------------------------------")
    print("Tracking completed")
    print("----------------------------------------")

    print(
        f"Frames processed: {frame_count}"
    )

    print(
        f"Reliable vehicles: "
        f"{len(vehicle_results)}"
    )

    # --------------------------------------------------
    # SAVE VEHICLES TO DATABASE
    # --------------------------------------------------

    for vehicle in vehicle_results:

        print(vehicle)

        saved = save_vehicle(
            vehicle
        )

        if saved:

            print(
                f"Saved vehicle "
                f"{vehicle['vehicle_id']} "
                f"to database"
            )

    print(
        "\nOutput video:"
    )

    print(output_video)

    # --------------------------------------------------
    # RETURN RESULTS
    # --------------------------------------------------

    return {
        "output_video": str(
            output_video
        ),
        "frame_count": frame_count,
        "fps": fps,
        "width": width,
        "height": height,
        "vehicle_count": len(
            vehicle_results
        ),
        "vehicles": vehicle_results
    }


# --------------------------------------------------
# DIRECT TEST
# --------------------------------------------------

if __name__ == "__main__":

    test_video = (
        PROJECT_ROOT /
        "videos" /
        "traffic.mp4"
    )

    result = process_video(
        test_video
    )

    print("\nFinal result:")
    print(result)