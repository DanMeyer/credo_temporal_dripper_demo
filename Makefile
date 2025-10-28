.PHONY: dev up up-dripper load

dev:
	python app/run_worker.py --queue general,status,convert --max-activities 2

up:
	docker compose up --build

up-dripper:
	docker compose up --build

load:
	python tools/loader.py --n 25 --rate 2
