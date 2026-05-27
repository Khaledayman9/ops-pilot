dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down:
	docker compose down

migrate:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend alembic upgrade head

revision:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm \
		-v $(PWD)/alembic:/app/alembic \
		backend alembic revision --autogenerate -m "$(m)"