@echo off
title GTA V / FiveM Audio Converter + OpenIV Workflow
echo.
echo ======================================================================
echo   GTA V / FiveM Vehicle Audio Converter + OpenIV Workflow
echo ======================================================================
echo   Output: WAV, 16-bit, Mono, 24000 Hz, PCM Little Endian
echo.
echo   Workflow:
echo   1. Convert all audio files to GTA V format
echo   2. Validate against GTA V / FiveM rules
echo   3. Generate OpenIV openFormats structure (.oac)
echo   4. Ready for AWC import - ZERO manual steps!
echo ======================================================================
echo.
echo   Put your audio files in the "input" folder, then press any key...
echo.
pause

python convert_audio.py

echo.
pause
