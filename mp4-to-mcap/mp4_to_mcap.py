import argparse
from datetime import datetime
import os
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import av
from foxglove_schemas_protobuf.CompressedVideo_pb2 import CompressedVideo
from google.protobuf.timestamp_pb2 import Timestamp
from mcap.writer import Writer
from tqdm import tqdm

from writers import ProtobufWriter


def count_frames_by_demux(input_file: Path) -> Optional[int]:
    with av.open(input_file) as container:
        print("Counting frames by demuxing...")
        video_stream = container.streams.video[0]
        total_frames = sum(1 for _ in container.demux(video=0))
        print(f"  Video codec: {video_stream.codec_context.name}")
        print(f"  Using frame rate: {video_stream.average_rate} fps")
        print(f"  Total frames: {total_frames}")
        return total_frames


def protobuf_timestamp(ts: int):
    timestamp = Timestamp()
    timestamp.FromNanoseconds(ts)
    return timestamp


def load_mp4_frames(
    input_mp4: Path,
    frame_id: str = "",
    frame_rate: float = 30.0,
    global_start_time_ns: Optional[int] = None,
) -> Generator[Tuple[CompressedVideo, int], None, None]:
    """Load MP4 file and yield CompressedVideo messages.

    Args:
        input_mp4: Path to input MP4 file
        frame_id: Frame ID for the video stream
        frame_rate: Default frame rate if not available from video
        global_start_time_ns: Optional external start time in nanoseconds

    Yields:
        Tuple[CompressedVideo, int]: CompressedVideo message and its timestamp in nanoseconds
    """
    with av.open(input_mp4) as container:
        # Get video info
        video_stream = container.streams.video[0]
        frame_rate = float(video_stream.average_rate or frame_rate)

        # Determine the start time: external > video_stream > now()
        if global_start_time_ns:
            start_time_ns = global_start_time_ns
        elif video_stream.start_time is not None:
            start_time_ns = video_stream.start_time * 1e9
        else:
            start_time_ns = datetime.now().timestamp() * 1e9
        frame_duration_ns = int(1e9 / frame_rate)  # Duration of one frame in nanosecs

        for frame_count, packet in enumerate(container.demux(video=0)):
            # Skip invalid packets
            if not packet.buffer_ptr or packet.buffer_size <= 0:
                continue

            # Use packet timestamp if it exists, otherwise calculate based on frame count
            frame_time_ns = int(
                packet.pts * 1e9
                if packet.pts
                else start_time_ns + frame_count * frame_duration_ns
            )

            compressed_frame = CompressedVideo(
                timestamp=protobuf_timestamp(frame_time_ns),
                frame_id=frame_id,
                data=bytes(packet),
                format="h264",
            )

            yield frame_time_ns, compressed_frame


def process_mp4_h264_stream(input_mp4: Path, output_mcap: Path, topic: str):
    """Process MP4 file and write to MCAP file with progress bar.

    Args:
        input_mp4: Path to input MP4 file
        output_mcap: Path to output MCAP file
        topic: Topic name for video stream
    """
    process_start_time = datetime.now()
    print(f"Processing MP4 file: {input_mp4}")
    total_frames = count_frames_by_demux(input_mp4)

    # Setup progress bar
    pbar = tqdm(
        total=total_frames,
        desc="Converting frames",
        unit="",  # Empty string to avoid unit in rate
        unit_scale=True,
        unit_divisor=1000,  # Show thousands as k
        miniters=1,  # Update at least every frame
        dynamic_ncols=True,  # Automatically adjust to terminal width
        bar_format=(
            "{desc}: {percentage:3.0f}%|{bar}| {n:d}/{total:d} frames "
            "[{elapsed}<{remaining}, {rate_fmt} fps]"
            if total_frames
            else "{l_bar}{bar}| {n:d} frames [{elapsed}, {rate_fmt} fps]"
        ),
    )

    # Process frames
    with open(output_mcap, "wb") as outfile:
        writer = Writer(outfile)
        protobuf_writer = ProtobufWriter(writer)
        writer.start()

        # Write frames with progress bar
        for timestamp, message in load_mp4_frames(input_mp4):
            protobuf_writer.write_message(
                topic=topic,
                message=message,
                log_time=timestamp,
                publish_time=timestamp,
            )
            pbar.update(1)

        writer.finish()
        pbar.close()

    print(f"Total frames processed: {pbar.n}")
    print(f"Processing time: {datetime.now() - process_start_time}")
    print(f"Output MCAP file: {output_mcap}")


def process_input_files(input_paths: List[Path], output_dir: Path, topic: str) -> None:
    """Process all MP4 files from input paths and convert them to MCAP files.

    Args:
        input_paths: List of input files or directories
        output_dir: Output directory for MCAP files
        topic: Topic name for video streams
    """

    # Collect all MP4 files from input paths
    mp4_files = []
    for path in input_paths:
        if path.is_dir():
            mp4_files.extend(path.glob("**/*.mp4"))
        elif path.suffix.lower() == ".mp4":
            mp4_files.append(path)

    if not mp4_files:
        raise FileNotFoundError(f"No MP4 files found in {input_paths}")

    # Process each MP4 file
    for mp4_file in mp4_files:
        output_file = output_dir / f"{mp4_file.stem}.mcap"
        print(f"\nProcessing {mp4_file.name} -> {output_file.name}")
        process_mp4_h264_stream(
            input_mp4=mp4_file, output_mcap=output_file, topic=topic
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-paths",
        nargs="+",
        type=lambda x: Path(x).expanduser(),
        help="Input MP4 file or directory containing MP4 files (required)",
    )
    parser.add_argument(
        "--output-dir",
        type=lambda x: Path(x).expanduser() if x else None,
        help="Output directory for MCAP files (required)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=os.environ.get("TOPIC", "/video/h264"),
        help="Topic for video streams",
    )
    args = parser.parse_args()

    if not args.input_paths and os.environ.get("INPUT_PATHS"):
        args.input_paths = [
            Path(x).expanduser() for x in os.environ.get("INPUT_PATHS").split(":")
        ]
    if not args.output_dir and os.environ.get("OUTPUT_DIR"):
        args.output_dir = Path(os.environ.get("OUTPUT_DIR")).expanduser()

    process_input_files(args.input_paths, args.output_dir, args.topic)


if __name__ == "__main__":
    main()
