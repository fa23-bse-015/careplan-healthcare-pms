@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SmartHealthcarePMS --add-data "schema.sql;." app.py
