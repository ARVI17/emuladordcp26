.PHONY: up down restart logs test seed reset backup restore emulator-status emulator-connect

up:
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

test:
	docker compose run --rm --no-deps backend pytest -q
	docker compose run --rm frontend-test
	docker compose run --rm frontend-e2e

seed:
	docker compose exec backend python -m app.db.seed

reset:
	docker compose down -v
	docker compose up --build -d

backup:
	powershell -ExecutionPolicy Bypass -File scripts/backup.ps1

restore:
	powershell -ExecutionPolicy Bypass -File scripts/restore.ps1 -BackupFile "$(FILE)"

emulator-status:
	powershell -ExecutionPolicy Bypass -File scripts/check-emulator.ps1

emulator-connect:
	powershell -ExecutionPolicy Bypass -File scripts/check-emulator.ps1 -Connect -Address "$(ADDRESS)"
