#!/usr/bin/env python3
"""
Video to Sprite Sheet Converter

Converts MP4 animations to sprite sheets for efficient avatar animations.
Uses ffmpeg to extract frames and ImageMagick to create sprite sheets.
"""

import argparse
import os
import glob
import subprocess
import shutil
import sys
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description='Convert video animations to sprite sheets')
    parser.add_argument('input_dir', help='Directory containing MP4 animation files')
    parser.add_argument('--output-dir', '-o', default='sprite_sheets', 
                        help='Output directory for sprite sheets')
    parser.add_argument('--temp-dir', '-t', default='temp_frames',
                        help='Temporary directory for extracted frames')
    parser.add_argument('--fps', default=12, type=int,
                        help='Frames per second to extract (default: 12)')
    parser.add_argument('--cols', default=4, type=int,
                        help='Number of columns in sprite sheet (default: 4)')
    parser.add_argument('--frame-size', default='128x128',
                        help='Size of each frame in sprite sheet (default: 128x128)')
    parser.add_argument('--prefix', default='animation_',
                        help='Prefix for sprite sheet filenames')
    parser.add_argument('--clean', action='store_true',
                        help='Clean up temporary files after processing')
    return parser.parse_args()

def check_dependencies():
    """Check if ffmpeg and ImageMagick are installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: ffmpeg not found. Please install ffmpeg.")
        return False
    
    try:
        # Try montage command (Linux/macOS)
        subprocess.run(['montage', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        try:
            # Try magick montage (Windows)
            subprocess.run(['magick', 'montage', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Error: ImageMagick not found. Please install ImageMagick.")
            return False
    
    return True

def extract_frames(video_path, output_dir, fps):
    """Extract frames from video using ffmpeg"""
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    frames_dir = os.path.join(output_dir, video_name)
    os.makedirs(frames_dir, exist_ok=True)
    
    # Create frame extraction command
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps={fps}',
        os.path.join(frames_dir, f'frame_%03d.png')
    ]
    
    print(f"Extracting frames from {video_path}...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        frame_count = len(glob.glob(os.path.join(frames_dir, 'frame_*.png')))
        print(f"  Extracted {frame_count} frames to {frames_dir}")
        return frames_dir, frame_count
    except subprocess.CalledProcessError as e:
        print(f"Error extracting frames: {e}")
        print(f"ffmpeg error: {e.stderr.decode()}")
        return None, 0

def create_sprite_sheet(frames_dir, output_path, cols, frame_size, frame_count):
    """Create sprite sheet using ImageMagick"""
    # Calculate rows needed
    rows = (frame_count + cols - 1) // cols  # Ceiling division
    
    # Try to determine if we're on Windows or Unix-like
    is_windows = sys.platform.startswith('win')
    
    if is_windows:
        cmd = [
            'magick', 'montage',
            os.path.join(frames_dir, 'frame_*.png'),
            '-tile', f'{cols}x{rows}',
            '-geometry', f'{frame_size}+0+0',
            '-background', 'none',
            output_path
        ]
    else:
        cmd = [
            'montage',
            os.path.join(frames_dir, 'frame_*.png'),
            '-tile', f'{cols}x{rows}',
            '-geometry', f'{frame_size}+0+0',
            '-background', 'none',
            output_path
        ]
    
    print(f"Creating sprite sheet: {output_path}...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"  Created sprite sheet with {frame_count} frames ({cols}x{rows})")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating sprite sheet: {e}")
        if hasattr(e, 'stderr'):
            print(f"ImageMagick error: {e.stderr.decode()}")
        return False

def generate_animation_info(animations):
    """Generate a Python dictionary with animation data"""
    info = {}
    for anim_name, anim_data in animations.items():
        frame_count, cols, rows = anim_data
        info[anim_name] = {
            "sheet": f"{anim_name}_sheet.png",
            "frames": frame_count,
            "cols": cols,
            "rows": rows,
            "frame_size": args.frame_size.split('x'),
            "fps": args.fps,
            "loop": True  # Default to looping animations
        }
    
    return info

def write_animation_data(animations, output_dir):
    """Write animation data to a Python file"""
    output_path = os.path.join(output_dir, "animation_data.py")
    with open(output_path, 'w') as f:
        f.write("# Auto-generated animation data\n")
        f.write("ANIMATIONS = {\n")
        for anim_name, anim_data in animations.items():
            frame_count, cols, rows = anim_data
            f.write(f"    '{anim_name}': {{\n")
            f.write(f"        'sheet': '{anim_name}_sheet.png',\n")
            f.write(f"        'frames': {frame_count},\n")
            f.write(f"        'cols': {cols},\n")
            f.write(f"        'rows': {rows},\n")
            f.write(f"        'frame_size': ({args.frame_size.split('x')[0]}, {args.frame_size.split('x')[1]}),\n")
            f.write(f"        'fps': {args.fps},\n")
            f.write("        'loop': True,\n")
            f.write("    },\n")
        f.write("}\n")
    print(f"Wrote animation data to {output_path}")

def main(args):
    # Create directories
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.temp_dir, exist_ok=True)
    
    # Find all MP4 files in input directory
    videos = glob.glob(os.path.join(args.input_dir, '*.mp4'))
    if not videos:
        print(f"No MP4 files found in {args.input_dir}")
        return 1
    
    print(f"Found {len(videos)} video files")
    
    # Process each video
    animations = {}
    for video in videos:
        video_name = os.path.splitext(os.path.basename(video))[0]
        frames_dir, frame_count = extract_frames(video, args.temp_dir, args.fps)
        
        if frames_dir and frame_count > 0:
            # Create output filename
            output_path = os.path.join(args.output_dir, f"{args.prefix}{video_name}_sheet.png")
            
            # Calculate rows
            rows = (frame_count + args.cols - 1) // args.cols
            
            # Create sprite sheet
            success = create_sprite_sheet(frames_dir, output_path, args.cols, args.frame_size, frame_count)
            
            if success:
                animations[video_name] = (frame_count, args.cols, rows)
    
    # Generate animation data file
    if animations:
        write_animation_data(animations, args.output_dir)
    
    # Clean up temporary files if requested
    if args.clean and os.path.exists(args.temp_dir):
        print("Cleaning up temporary files...")
        shutil.rmtree(args.temp_dir)
    
    print("Done!")
    return 0

if __name__ == "__main__":
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
        
    # Parse arguments
    args = parse_args()
    
    # Run main function
    sys.exit(main(args))
