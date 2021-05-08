@echo off
python bkpScr/backup.py
if errorlevel 1 (
	echo "Unexpected Exception: Errorcode: %errorlevel%"
	pause >NUL
)
exit