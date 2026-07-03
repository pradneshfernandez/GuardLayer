.PHONY: setup run test demo logs down clean

setup:
	docker compose up -d --build
	docker compose exec guardlayer python -m storage.migrate

run:
	docker compose up guardlayer

test:
	pytest tests/ -v --cov

demo:
	docker compose exec guardlayer python -m demo.run_demo

logs:
	docker compose logs -f

down:
	docker compose down

clean:
	docker compose down -v
