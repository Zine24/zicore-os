@echo off
title ZICORE System - Ollama Server
echo ============================================
echo   ZICORE System - Ollama Server
echo   ZineMotion Foundation
echo ============================================
echo.
set OLLAMA_MODELS=C:\Users\zinem\Documents\zicore-system\data\ollama\models
set OLLAMA_HOST=127.0.0.1:11434
set OLLAMA_KEEP_ALIVE=5m
echo [ZICORE] Starting Ollama server...
echo [ZICORE] Models: %OLLAMA_MODELS%
echo [ZICORE] Host: %OLLAMA_HOST%
echo.
.\ollama.exe serve
