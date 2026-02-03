# GTA V / FiveM Vehicle Audio Converter

ONE-CLICK workflow: Original Audio → GTA-safe WAV → Ready for AWC

Preserves original `.oac` metadata by copying from input!

## Output Format (100% GTA V / FiveM / OpenIV Compatible)

| Property | Value |
|----------|-------|
| Format | WAV (PCM uncompressed) |
| Bit depth | 16-bit ONLY |
| Channels | Mono (1 channel) |
| Sample rate | 24,000 Hz (default) |
| Byte order | Little Endian |
| Codec | pcm_s16le |

## Requirements

1. **Python 3.x** - https://www.python.org/downloads/
2. **FFmpeg** - INCLUDED (`ffmpeg.exe` in this folder)

## How to Use

1. **Export from OpenIV:**
   - Right-click AWC → Export to openFormats folder
   - Copy the entire exported folder into `input/`

2. **Double-click `CONVERT.bat`**

3. **Script automatically:**
   - Detects AWC name from `.oac` file
   - Converts WAV files to GTA V format (24,000 Hz, 16-bit, Mono)
   - Validates all files
   - Copies original `.oac` and `.awc` to output

4. **Import to OpenIV:**
   - Open OpenIV in Edit Mode
   - Go to: Edit → New → Import openFormats
   - Select the `.oac` file from output folder
   - Done!

## Input Folder Structure

```
input/
  ├── awcname.oac        ← Original .oac (exported from OpenIV)
  ├── awcname.awc        ← Original .awc (optional)
  └── awcname/           ← Subfolder with WAV files
        ├── ENGINE_ACCEL.wav
        ├── ENGINE_DECEL.wav
        └── ...
```

## Output Folder Structure

```
output/
  ├── awcname.oac              ← Copied from input (original metadata)
  ├── awcname.awc              ← Copied from input
  ├── awcname/                 ← Converted WAV files
  │     └── *.wav
  └── _VALIDATION_REPORT.txt
```

## Command Line Options

```bash
# Basic (24,000 Hz default)
python convert_audio.py

# Custom sample rate
python convert_audio.py --rate 32000
python convert_audio.py --rate 22050

# Custom AWC name
python convert_audio.py --awc-name sultan

# Custom folders
python convert_audio.py -i "C:\sounds" -o "C:\converted"
```

## Supported Input Formats

WAV, MP3, OGG, FLAC, AAC, M4A, WMA, OPUS, AIFF

## Notes

- Original `.oac` is **COPIED**, not generated - preserves all metadata (Headroom, UNKNOWN fields, etc.)
- File size may INCREASE if original was lower quality - this is REQUIRED for GTA V compatibility
- **24,000 Hz** - Default, GTA V native sample rate
- **32,000 Hz** - Higher quality if needed
- **22,050 Hz** - For small effects (clicks, beeps)

## License

Open Source - Free to use and modify
