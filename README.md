# GTA V / FiveM Vehicle Audio Converter

ONE-CLICK workflow: Original Audio → GTA-safe WAV → Ready for AWC

**Batch Mode** - Convert multiple AWC packages at once!

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
   - Copy **all** exported folders into `input/`
   - You can add multiple AWC packages at once!

2. **Double-click `CONVERT.bat`**

3. **Script automatically:**
   - Detects ALL AWC packages in input folder
   - Converts WAV files to GTA V format (24,000 Hz, 16-bit, Mono)
   - Validates all files
   - Copies original `.oac` and `.awc` to output

4. **Import to OpenIV:**
   - Open OpenIV in Edit Mode
   - Go to: Edit → New → Import openFormats
   - Select `.oac` file from output folder
   - Repeat for each AWC package

## Input Folder Structure (Batch Mode)

Put multiple AWC packages in the input folder:

```
input/
  ├── baller3.oac        ← Original .oac
  ├── baller3.awc        ← Original .awc
  ├── baller3/           ← WAV files
  │     └── *.wav
  ├── mamba.oac
  ├── mamba.awc
  ├── mamba/
  │     └── *.wav
  ├── schafter3.oac
  ├── schafter3.awc
  ├── schafter3/
  │     └── *.wav
  └── ...
```

## Output Folder Structure

```
output/
  ├── baller3.oac              ← Copied from input
  ├── baller3.awc              ← Copied from input
  ├── baller3/                 ← Converted WAV files
  │     └── *.wav
  ├── mamba.oac
  ├── mamba.awc
  ├── mamba/
  │     └── *.wav
  ├── schafter3.oac
  ├── schafter3.awc
  ├── schafter3/
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

## Notes

- Original `.oac` is **COPIED**, not generated - preserves all metadata (Headroom, UNKNOWN fields, etc.)
- File size may INCREASE if original was lower quality - this is REQUIRED for GTA V compatibility
- This tool outputs **24,000 Hz** by default (GTA V native sample rate)
- If you *really* need it, you can override sample rate via CLI: `--rate 32000` or `--rate 22050`

## License

Open Source - Free to use and modify
