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

def process_files(input_folder, output_folder, sample_rate=24000, recursive=False, 
                  generate_openformats=True, awc_name=None):
    """Process all audio files with full OpenIV workflow."""
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    if not input_path.exists():
        print(f"Error: Input folder '{input_folder}' does not exist!")
        return
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Auto-detect structure from input folder
    # Look for .oac and .awc files
    oac_files = list(input_path.glob('*.oac'))
    awc_files = list(input_path.glob('*.awc'))
    
    # Look for subfolders containing WAV files
    subfolders = [d for d in input_path.iterdir() if d.is_dir()]
    
    # Determine AWC name from .oac file or subfolder
    if awc_name is None:
        if oac_files:
            awc_name = oac_files[0].stem
        elif subfolders:
            # Use first subfolder that contains audio files
            for sf in subfolders:
                audio_in_sf = list(sf.glob('*.wav')) + list(sf.glob('*.mp3'))
                if audio_in_sf:
                    awc_name = sf.name
                    break
        if awc_name is None:
            awc_name = output_path.name
    
    # Find WAV files - first check subfolders, then root
    files = []
    wav_source_folder = None
    
    # Check if there's a subfolder matching awc_name with audio files
    awc_subfolder = input_path / awc_name
    if awc_subfolder.exists() and awc_subfolder.is_dir():
        files = [f for f in awc_subfolder.glob('*') if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        wav_source_folder = awc_subfolder
    
    # If no files found in subfolder, check all subfolders
    if not files:
        for sf in subfolders:
            sf_files = [f for f in sf.glob('*') if f.suffix.lower() in SUPPORTED_EXTENSIONS]
            if sf_files:
                files = sf_files
                wav_source_folder = sf
                if awc_name is None:
                    awc_name = sf.name
                break
    
    # If still no files, check root folder
    if not files:
        files = [f for f in input_path.glob('*') if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        wav_source_folder = input_path
    
    if not files:
        print(f"No audio files found in '{input_folder}'")
        print(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        return
    
    # Create output subfolder for WAV files
    wav_output_path = output_path / awc_name
    wav_output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"  GTA V / FiveM Audio Converter + OpenIV Workflow")
    print(f"{'='*70}")
    print(f"  Input folder:    {input_folder}")
    print(f"  Output folder:   {output_folder}")
    print(f"  AWC name:        {awc_name}")
    print(f"  WAV source:      {wav_source_folder}")
    print(f"  WAV output:      {wav_output_path}")
    print(f"  Sample rate:     {sample_rate} Hz")
    if oac_files:
        print(f"  Original .oac:   {oac_files[0].name} (will copy)")
    if awc_files:
        print(f"  Original .awc:   {awc_files[0].name} (will copy)")
    print(f"  Files found:     {len(files)}")
    print(f"{'='*70}\n")
    
    # Stats
    total_input_size = 0
    total_output_size = 0
    converted_files = []
    validation_results = []
    
    print("STEP 1: Converting audio files...")
    print("-" * 70)
    
    for i, file in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {file.name}")
        
        input_size = file.stat().st_size
        total_input_size += input_size
        
        # Output path - same filename in output subfolder
        out_file = wav_output_path / (file.stem + '.wav')
        
        # Convert
        if convert_audio(file, out_file, sample_rate):
            output_size = out_file.stat().st_size
            total_output_size += output_size
            
            reduction = ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
            sign = "-" if reduction > 0 else "+"
            
            print(f"    Converted: {format_size(input_size)} -> {format_size(output_size)} ({sign}{abs(reduction):.1f}%)")
            converted_files.append(out_file)
        else:
            print(f"    FAILED to convert!")
    
    print()
    print("STEP 2: Validating converted files...")
    print("-" * 70)
    
    all_valid = True
    for wav_file in converted_files:
        is_valid, issues, info = validate_wav_for_gta(wav_file, sample_rate)
        
        validation_results.append({
            'file': wav_file.name,
            'valid': is_valid,
            'issues': issues,
            'info': info
        })
        
        if is_valid:
            print(f"[OK]   {wav_file.name}")
            if info:
                print(f"       {info['sample_rate']}Hz, {'mono' if info['channels']==1 else 'stereo'}, "
                      f"{info['bit_depth']}bit, {format_duration(info['duration'])}")
        else:
            all_valid = False
            print(f"[FAIL] {wav_file.name}")
            for issue in issues:
                print(f"       ! {issue}")
    
    # Generate validation report
    report_path = generate_validation_report(output_path, validation_results)
    print(f"\nValidation report: {report_path.name}")
    
    # Step 3: Copy original .oac and .awc files (instead of generating new ones)
    print()
    print("STEP 3: Copying original .oac and .awc files...")
    print("-" * 70)
    
    copied_files = []
    
    # Copy .oac file if exists
    if oac_files:
        src_oac = oac_files[0]
        dst_oac = output_path / src_oac.name
        shutil.copy2(src_oac, dst_oac)
        print(f"[OK] Copied: {src_oac.name} ({format_size(src_oac.stat().st_size)})")
        copied_files.append(dst_oac)
    else:
        # Generate .oac if no original exists
        if generate_openformats and converted_files:
            oac_path = generate_oac_file(output_path, converted_files, awc_name)
            print(f"[OK] Generated: {oac_path.name} (no original found)")
            copied_files.append(oac_path)
    
    # Copy .awc file if exists
    if awc_files:
        src_awc = awc_files[0]
        dst_awc = output_path / src_awc.name
        shutil.copy2(src_awc, dst_awc)
        print(f"[OK] Copied: {src_awc.name} ({format_size(src_awc.stat().st_size)})")
        copied_files.append(dst_awc)
    
    if not oac_files and not awc_files:
        print("[INFO] No .oac or .awc files found in input folder")
    
    # Final Summary
    print()
    print("=" * 70)
    print("  WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"  Files converted:   {len(converted_files)}")
    print(f"  Files validated:   {sum(1 for r in validation_results if r['valid'])}/{len(validation_results)}")
    print(f"  Total input:       {format_size(total_input_size)}")
    print(f"  Total output:      {format_size(total_output_size)}")
    
    if total_input_size > 0:
        total_change = ((total_input_size - total_output_size) / total_input_size) * 100
        if total_change > 0:
            print(f"  Space saved:       {format_size(total_input_size - total_output_size)} (-{total_change:.1f}%)")
        else:
            print(f"  Size change:       +{format_size(total_output_size - total_input_size)} (+{abs(total_change):.1f}%)")
    
    print("=" * 70)
    
    if all_valid:
        print()
        print("  [SUCCESS] All files are GTA V / FiveM compatible!")
        print()
        print("  OUTPUT STRUCTURE:")
        print(f"  {output_path.name}/")
        if oac_files:
            print(f"    +-- {awc_name}.oac           <- Copied from input")
        if awc_files:
            print(f"    +-- {awc_name}.awc           <- Copied from input")
        print(f"    +-- {awc_name}/              <- Converted WAV files")
        print(f"    |     +-- *.wav")
        print(f"    +-- _VALIDATION_REPORT.txt")
        print()
        print("  IMPORT TO OPENIV:")
        print("  1. Open OpenIV in Edit Mode")
        print("  2. Navigate to: Edit -> New -> Import openFormats")
        print(f"  3. Select the '{awc_name}.oac' file from output folder")
        print("  4. Done! AWC file will be created automatically")
        print()
    else:
        print()
        print("  [WARNING] Some files have validation issues!")
        print(f"  Check {report_path.name} for details.")
        print()
    
    print("=" * 70)

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
