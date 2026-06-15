@echo off
rmdir /s /q build
rmdir /s /q dist

pyinstaller ^
  --noconfirm ^
  --windowed ^
  --onedir ^
  --name HardwareMockRecorder ^
  --add-data "config\default_config.json;config" ^
  --add-data "app\db\schema.sql;app\db" ^
  --add-data "app\assets\app_icon.svg;app\assets" ^
  main.py

pause
