dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build

migrate:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend alembic upgrade head

migrate-version-up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend alembic upgrade "$(m)"

migrate-version-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend alembic downgrade "$(m)"

revision:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm \
		-v $(PWD)/alembic:/app/alembic \
		backend alembic revision --autogenerate -m "$(m)"
	sudo chown -R $(USER):$(USER) $(PWD)/alembic/versions

seed-neo4j:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m app.db.neo4j_seed

prune:
	docker system prune -a
	docker system prune -a --volumes