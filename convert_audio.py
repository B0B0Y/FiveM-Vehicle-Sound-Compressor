"""
GTA V / FiveM Vehicle Audio Converter + OpenIV openFormats Workflow
Converts audio files to OpenIV/AWC compatible format and prepares openFormats structure.

Output specs:
- Format: WAV (PCM uncompressed)
- Bit depth: 16-bit
- Channels: Mono
- Sample rate: 32000 Hz (default) or 22050 Hz
- Little Endian

Workflow:
1. Convert audio files to GTA V compatible format
2. Validate all files against GTA V / FiveM rules
3. Generate OpenIV openFormats structure (.oac metadata)
4. Ready for direct AWC import - zero manual steps
"""

import subprocess
import sys
import os
import struct
import wave
import shutil
from pathlib import Path
from datetime import datetime

# Supported input formats
SUPPORTED_EXTENSIONS = {'.wav', '.mp3', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus', '.aiff', '.aif'}

# GTA V Audio Requirements
GTA_REQUIREMENTS = {
    'format': 'WAV',
    'codec': 'PCM',
    'bit_depth': 16,
    'channels': 1,
    'sample_rates': [24000, 32000, 22050],
    'byte_order': 'little_endian'
}

# Get script directory for local ffmpeg
SCRIPT_DIR = Path(__file__).parent
FFMPEG_LOCAL = SCRIPT_DIR / "ffmpeg.exe"

def get_ffmpeg_path():
    """Get path to ffmpeg executable (local or PATH)."""
    if FFMPEG_LOCAL.exists():
        return str(FFMPEG_LOCAL)
    return 'ffmpeg'

def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    ffmpeg = get_ffmpeg_path()
    try:
        subprocess.run([ffmpeg, '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_wav_info(file_path):
    """Get detailed WAV file information using Python's wave module."""
    try:
        with wave.open(str(file_path), 'rb') as wav:
            return {
                'channels': wav.getnchannels(),
                'sample_rate': wav.getframerate(),
                'bit_depth': wav.getsampwidth() * 8,
                'frames': wav.getnframes(),
                'duration': wav.getnframes() / wav.getframerate() if wav.getframerate() > 0 else 0,
                'codec': 'pcm_s16le' if wav.getsampwidth() == 2 else f'pcm_{wav.getsampwidth()*8}bit'
            }
    except Exception as e:
        return None

def get_audio_info_ffmpeg(file_path):
    """Get audio file information using ffmpeg."""
    ffmpeg = get_ffmpeg_path()
    try:
        result = subprocess.run([
            ffmpeg, '-i', str(file_path), '-hide_banner'
        ], capture_output=True, text=True)
        
        info_text = result.stderr
        info = {
            'sample_rate': 0,
            'channels': 0,
            'bit_depth': 'unknown',
            'codec': 'unknown'
        }
        
        for line in info_text.split('\n'):
            if 'Audio:' in line:
                parts = line.split(',')
                
                if 'Audio:' in parts[0]:
                    codec_part = parts[0].split('Audio:')[1].strip()
                    info['codec'] = codec_part.split()[0] if codec_part else 'unknown'
                
                for part in parts:
                    part = part.strip()
                    if 'Hz' in part:
                        try:
                            info['sample_rate'] = int(part.replace('Hz', '').strip())
                        except:
                            pass
                    elif part in ['mono', 'stereo']:
                        info['channels'] = 1 if part == 'mono' else 2
                    elif part.startswith('s') and part[1:].isdigit():
                        info['bit_depth'] = int(part[1:])
                    elif part.startswith('u') and part[1:].isdigit():
                        info['bit_depth'] = int(part[1:])
                break
        
        return info
    except:
        return None

def validate_wav_for_gta(file_path, target_sample_rate=32000):
    """
    Validate a WAV file against GTA V / FiveM requirements.
    Returns (is_valid, issues_list, info_dict)
    """
    issues = []
    info = get_wav_info(file_path)
    
    if info is None:
        return False, ["Could not read WAV file"], None
    
    # Check bit depth (MUST be 16-bit)
    if info['bit_depth'] != 16:
        issues.append(f"Bit depth is {info['bit_depth']}-bit (must be 16-bit)")
    
    # Check channels (MUST be mono)
    if info['channels'] != 1:
        issues.append(f"Channels: {info['channels']} (must be mono/1 channel)")
    
    # Check sample rate
    if info['sample_rate'] not in GTA_REQUIREMENTS['sample_rates']:
        issues.append(f"Sample rate is {info['sample_rate']}Hz (must be 32000Hz or 22050Hz)")
    elif info['sample_rate'] != target_sample_rate:
        # Warning, not error - both rates are valid
        pass
    
    is_valid = len(issues) == 0
    return is_valid, issues, info

def convert_audio(input_path, output_path, sample_rate=32000):
    """Convert audio file to GTA V/FiveM compatible format."""
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        '-y',                           # Overwrite output
        '-i', str(input_path),          # Input file
        '-acodec', 'pcm_s16le',         # 16-bit PCM Little Endian
        '-ac', '1',                     # Mono (1 channel)
        '-ar', str(sample_rate),        # Sample rate
        '-f', 'wav',                    # WAV format
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def format_size(size_bytes):
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

def format_duration(seconds):
    """Format duration in human readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"

def generate_oac_file(output_folder, wav_files, awc_name=None):
    """
    Generate OpenIV openFormats .oac metadata file.
    
    The .oac file tells OpenIV how to rebuild the AWC archive.
    Uses OpenIV's custom text format (NOT XML).
    """
    if awc_name is None:
        awc_name = output_folder.name
    
    # Build the .oac content in OpenIV's text format
    lines = []
    lines.append("Version 1 11")
    lines.append("{")
    lines.append("\tIsStream False")
    lines.append("\tDescriptorsInOrder False")
    lines.append("\tEntries")
    lines.append("\t{")
    
    for wav_file in sorted(wav_files):
        track_name = wav_file.stem
        # Relative path: awc_name\filename.wav
        wave_path = f"{awc_name}\\{wav_file.name}"
        
        lines.append(f"\t\tWaveTrack {track_name}")
        lines.append("\t\t{")
        lines.append("\t\t\tCompression PCM")
        lines.append("\t\t\tHeadroom -170")
        lines.append("\t\t\tLoopPoint -1")
        lines.append("\t\t\tLoopBegin 0")
        lines.append("\t\t\tLoopEnd 0")
        lines.append("\t\t\tPlayBegin 0")
        lines.append("\t\t\tPlayEnd 0")
        lines.append(f"\t\t\tWave {wave_path}")
        lines.append("\t\t\tAnimClip null")
        lines.append("\t\t\tEvents null")
        lines.append("\t\t\tUNKNOWN_23097A2B null")
        lines.append("\t\t\tUNKNOWN_E787895A null")
        lines.append("\t\t\tUNKNOWN_252C20D9 null")
        lines.append("\t\t}")
    
    lines.append("\t}")
    lines.append("}")
    
    # Write .oac file
    oac_path = output_folder / f"{awc_name}.oac"
    with open(oac_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(lines))
    
    return oac_path

def generate_validation_report(output_folder, results):
    """Generate a validation report file."""
    report_path = output_folder / "_VALIDATION_REPORT.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("GTA V / FiveM AUDIO VALIDATION REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total files: {len(results)}\n")
        
        valid_count = sum(1 for r in results if r['valid'])
        f.write(f"Valid: {valid_count}\n")
        f.write(f"Invalid: {len(results) - valid_count}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("REQUIRED FORMAT:\n")
        f.write("- Format: WAV (PCM uncompressed)\n")
        f.write("- Bit depth: 16-bit ONLY\n")
        f.write("- Channels: Mono (1 channel)\n")
        f.write("- Sample rate: 32000 Hz or 22050 Hz\n")
        f.write("- Byte order: Little Endian\n")
        f.write("\n" + "=" * 60 + "\n\n")
        
        # List all files
        for r in results:
            status = "OK" if r['valid'] else "FAIL"
            f.write(f"[{status}] {r['file']}\n")
            
            if r['info']:
                info = r['info']
                f.write(f"     Channels: {info['channels']} ({'mono' if info['channels']==1 else 'stereo'})\n")
                f.write(f"     Sample rate: {info['sample_rate']} Hz\n")
                f.write(f"     Bit depth: {info['bit_depth']}-bit\n")
                f.write(f"     Duration: {format_duration(info['duration'])}\n")
            
            if r['issues']:
                for issue in r['issues']:
                    f.write(f"     ! {issue}\n")
            f.write("\n")
        
        f.write("=" * 60 + "\n")
        if valid_count == len(results):
            f.write("ALL FILES VALID - Ready for OpenIV AWC import!\n")
        else:
            f.write(f"WARNING: {len(results) - valid_count} file(s) have issues!\n")
        f.write("=" * 60 + "\n")
    
    return report_path

def process_single_awc(input_path, output_path, awc_name, sample_rate=24000):
    """Process a single AWC: convert WAVs, copy .oac and .awc."""
    
    # Find matching subfolder with WAV files
    wav_folder = input_path / awc_name
    if not wav_folder.exists() or not wav_folder.is_dir():
        print(f"  [SKIP] No folder found for {awc_name}")
        return None
    
    # Find audio files in the subfolder
    files = [f for f in wav_folder.glob('*') if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        print(f"  [SKIP] No audio files in {awc_name}/")
        return None
    
    # Find .oac and .awc files
    oac_file = input_path / f"{awc_name}.oac"
    awc_file = input_path / f"{awc_name}.awc"
    
    # Create output subfolder
    wav_output_path = output_path / awc_name
    wav_output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n  [{awc_name}] Converting {len(files)} audio files...")
    
    # Stats for this AWC
    total_input_size = 0
    total_output_size = 0
    converted_files = []
    all_valid = True
    
    # Convert files
    for file in files:
        input_size = file.stat().st_size
        total_input_size += input_size
        
        out_file = wav_output_path / (file.stem + '.wav')
        
        if convert_audio(file, out_file, sample_rate):
            output_size = out_file.stat().st_size
            total_output_size += output_size
            converted_files.append(out_file)
        else:
            print(f"    [FAIL] {file.name}")
    
    # Validate converted files
    for wav_file in converted_files:
        is_valid, issues, info = validate_wav_for_gta(wav_file, sample_rate)
        if not is_valid:
            all_valid = False
    
    # Copy .oac file
    if oac_file.exists():
        dst_oac = output_path / oac_file.name
        shutil.copy2(oac_file, dst_oac)
    else:
        # Generate .oac if no original exists
        generate_oac_file(output_path, converted_files, awc_name)
    
    # Copy .awc file
    if awc_file.exists():
        dst_awc = output_path / awc_file.name
        shutil.copy2(awc_file, dst_awc)
    
    status = "OK" if all_valid else "WARN"
    print(f"  [{status}] {awc_name}: {len(converted_files)} files, "
          f"{format_size(total_input_size)} -> {format_size(total_output_size)}")
    
    return {
        'awc_name': awc_name,
        'files_converted': len(converted_files),
        'input_size': total_input_size,
        'output_size': total_output_size,
        'valid': all_valid
    }


def process_files(input_folder, output_folder, sample_rate=24000, recursive=False, 
                  generate_openformats=True, awc_name=None):
    """Process all audio files with full OpenIV workflow. Supports batch processing."""
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    if not input_path.exists():
        print(f"Error: Input folder '{input_folder}' does not exist!")
        return
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Auto-detect all .oac files (each represents one AWC to process)
    oac_files = list(input_path.glob('*.oac'))
    
    # Also detect subfolders that might contain audio (even without .oac)
    subfolders = [d for d in input_path.iterdir() if d.is_dir()]
    
    # Build list of AWC names to process
    awc_names = set()
    
    # Add AWC names from .oac files
    for oac in oac_files:
        awc_names.add(oac.stem)
    
    # Add AWC names from subfolders that have audio files
    for sf in subfolders:
        audio_files = [f for f in sf.glob('*') if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        if audio_files:
            awc_names.add(sf.name)
    
    # If specific awc_name provided, only process that one
    if awc_name is not None:
        awc_names = {awc_name}
    
    if not awc_names:
        print(f"No AWC packages found in '{input_folder}'")
        print("Expected structure: input/awcname.oac + input/awcname/*.wav")
        return
    
    # Sort for consistent ordering
    awc_names = sorted(awc_names)
    
    print(f"\n{'='*70}")
    print(f"  GTA V / FiveM Audio Converter + OpenIV Workflow")
    print(f"  BATCH MODE - Processing {len(awc_names)} AWC package(s)")
    print(f"{'='*70}")
    print(f"  Input folder:    {input_folder}")
    print(f"  Output folder:   {output_folder}")
    print(f"  Sample rate:     {sample_rate} Hz")
    print(f"  AWC packages:    {', '.join(awc_names)}")
    print(f"{'='*70}")
    
    # Process each AWC
    results = []
    for awc in awc_names:
        result = process_single_awc(input_path, output_path, awc, sample_rate)
        if result:
            results.append(result)
    
    # Generate combined validation report
    all_validation_results = []
    for awc in awc_names:
        wav_folder = output_path / awc
        if wav_folder.exists():
            for wav_file in wav_folder.glob('*.wav'):
                is_valid, issues, info = validate_wav_for_gta(wav_file, sample_rate)
                all_validation_results.append({
                    'file': f"{awc}/{wav_file.name}",
                    'valid': is_valid,
                    'issues': issues,
                    'info': info
                })
    
    report_path = generate_validation_report(output_path, all_validation_results)
    
    # Final Summary
    total_files = sum(r['files_converted'] for r in results)
    total_input = sum(r['input_size'] for r in results)
    total_output = sum(r['output_size'] for r in results)
    all_valid = all(r['valid'] for r in results)
    
    print(f"\n{'='*70}")
    print(f"  BATCH WORKFLOW COMPLETE")
    print(f"{'='*70}")
    print(f"  AWC packages:      {len(results)}")
    print(f"  Total files:       {total_files}")
    print(f"  Total input:       {format_size(total_input)}")
    print(f"  Total output:      {format_size(total_output)}")
    
    if total_input > 0:
        total_change = ((total_input - total_output) / total_input) * 100
        if total_change > 0:
            print(f"  Space saved:       {format_size(total_input - total_output)} (-{total_change:.1f}%)")
        else:
            print(f"  Size change:       +{format_size(total_output - total_input)} (+{abs(total_change):.1f}%)")
    
    print(f"{'='*70}")
    
    if all_valid:
        print(f"\n  [SUCCESS] All {len(results)} AWC packages converted!")
    else:
        print(f"\n  [WARNING] Some files have validation issues!")
        print(f"  Check {report_path.name} for details.")
    
    print(f"\n  OUTPUT STRUCTURE:")
    print(f"  {output_path.name}/")
    for awc in awc_names:
        print(f"    +-- {awc}.oac")
        print(f"    +-- {awc}.awc")
        print(f"    +-- {awc}/")
        print(f"    |     +-- *.wav")
    print(f"    +-- _VALIDATION_REPORT.txt")
    
    print(f"\n  IMPORT TO OPENIV:")
    print(f"  1. Open OpenIV in Edit Mode")
    print(f"  2. Navigate to: Edit -> New -> Import openFormats")
    print(f"  3. Select ANY .oac file from output folder")
    print(f"  4. Repeat for each AWC package")
    print(f"\n{'='*70}")

def main():
    if not check_ffmpeg():
        print("ERROR: FFmpeg not found!")
        print(f"Place ffmpeg.exe in: {SCRIPT_DIR}")
        print("Or install FFmpeg and add it to your PATH.")
        print("Download: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    if FFMPEG_LOCAL.exists():
        print(f"Using local FFmpeg: {FFMPEG_LOCAL}")
    
    # Default folders
    script_dir = Path(__file__).parent
    default_input = script_dir / "input"
    default_output = script_dir / "output"
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(
        description='Convert audio to GTA V/FiveM format + OpenIV workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_audio.py
  python convert_audio.py --rate 22050
  python convert_audio.py --awc-name myvehicle
  python convert_audio.py -i "C:\\sounds" -o "C:\\output" --awc-name customcar
        """
    )
    parser.add_argument('-i', '--input', default=str(default_input),
                        help='Input folder (default: ./input)')
    parser.add_argument('-o', '--output', default=str(default_output),
                        help='Output folder (default: ./output)')
    parser.add_argument('-r', '--rate', type=int, default=24000, choices=[24000, 32000, 22050],
                        help='Sample rate: 24000 (default), 32000, or 22050 for small effects')
    parser.add_argument('--recursive', action='store_true',
                        help='Process subfolders recursively')
    parser.add_argument('--awc-name', type=str, default=None,
                        help='Name for the AWC/OAC file (default: output folder name)')
    parser.add_argument('--no-openformats', action='store_true',
                        help='Skip generating openFormats .oac file')
    
    args = parser.parse_args()
    
    # Create input folder if it doesn't exist
    Path(args.input).mkdir(parents=True, exist_ok=True)
    
    process_files(
        args.input, 
        args.output, 
        args.rate, 
        args.recursive,
        generate_openformats=not args.no_openformats,
        awc_name=args.awc_name
    )

if __name__ == '__main__':
    main()
