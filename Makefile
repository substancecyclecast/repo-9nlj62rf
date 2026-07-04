.PHONY: help dev prod test lint check-all offline-demo bench backup restore clean

help:  ## Показать это меню
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*##"}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

dev:  ## Запустить dev-окружение (Docker)
	docker compose up -d --build
	@echo "✓ API: http://localhost:8000/docs"
	@echo "✓ Streamlit: http://localhost:8501"
	@echo "✓ MailHog: http://localhost:8025"

prod:  ## Запустить production
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
	@echo "✓ Production started. Domain: $${DOMAIN:-demo.snabagent.ru}"

stop:  ## Остановить все контейнеры
	docker compose down

test:  ## Запустить тесты
	pytest -q --cov=src/snabagent --cov-report=term

lint:  ## Линтинг (ruff)
	ruff check src tests

typecheck:  ## Type-check (mypy strict)
	mypy src/snabagent --strict

security:  ## Аудит безопасности
	bandit -r src -q
	pip-audit --skip-editable

check-all: lint typecheck test security  ## Полная проверка (CI-эквивалент)
	@echo "✓ All checks passed"

offline-demo:  ## Оффлайн-демо (FakeLLM, без Docker)
	APP_ENV=dev LLM_PRIMARY=fake EMBEDDING_BACKEND=fake DATABASE_URL=sqlite+aiosqlite:///./demo.db \
		python scripts/run_offline_demo.py

bench:  ## Бенчмарк точности (>=70%)
	APP_ENV=dev LLM_PRIMARY=fake EMBEDDING_BACKEND=fake DATABASE_URL=sqlite+aiosqlite:///./bench.db \
		python scripts/benchmark.py --min-accuracy 0.70

migrate:  ## Применить миграции
	alembic upgrade head

migrate-new:  ## Создать новую миграцию
	@read -p "Message: " msg && alembic revision --autogenerate -m "$$msg"

backup:  ## Создать бэкап
	bash scripts/backup.sh

restore:  ## Восстановить из бэкапа
	@read -p "Backup dir: " dir && bash scripts/restore.sh "$$dir"

clean:  ## Очистить временные файлы
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .mypy_cache *.db

logs:  ## Логи всех сервисов
	docker compose logs -f --tail=50

shell:  ## Shell в API-контейнере
	docker compose exec api bash

bot-webhook:  ## Зарегистрировать Telegram webhook
	curl -s -X POST http://localhost:8000/api/v1/webhooks/telegram/set-webhook | python -m json.tool
