.PHONY: up down status test backup restore emulator-status emulator-connect

up:
	powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Inicio

down:
	powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Parada

status:
	powershell -ExecutionPolicy Bypass -File scripts/fc27.ps1 Estado

test:
	python scripts/verify_docker.py --scope full

backup:
	powershell -ExecutionPolicy Bypass -File scripts/backup.ps1

restore:
	powershell -ExecutionPolicy Bypass -File scripts/restore.ps1 -BackupFile "$(FILE)"

emulator-status:
	powershell -ExecutionPolicy Bypass -File scripts/check-emulator.ps1

emulator-connect:
	powershell -ExecutionPolicy Bypass -File scripts/check-emulator.ps1 -Connect -Address "$(ADDRESS)"
