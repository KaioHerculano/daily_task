MIN_COVERAGE = 100

.PHONY: help
help:
	@echo "-----------------------------------------------------"
	@echo " Makefile projeto Api-Shipay "
	@echo "-----------------------------------------------------"
	@echo " Comandos: "
	@echo "    make install         - Instala as dependancias e incia o ambiente virtual"
	@echo "    make migrate         - Aplica as migrations"
	@echo "    make migrations      - Gera novas migrations"
	@echo "    make test     - Roda os testes"
	@echo "    make test-coverage   - Roda os testes e gera um relatorio de cobertura"
	@echo "    make format   - Formata o codigo com Flake8, Black e Isort"
	@echo "    make db_population   - Popula o banco com os roles, claims e usuarios"

.PHONY: install
install:
	@python -m pip show poetry >nul 2>&1 || python -m pip install poetry
	@python -m poetry install

.PHONY: migrate
migrate:
	@poetry run python manage.py migrate

.PHONY: migrations
migrations:
	@poetry run python manage.py makemigrations

.PHONY: run
run:
	@poetry run python manage.py runserver

.PHONY: test
test:
	@poetry run python manage.py test

.PHONY: test-coverage
test-coverage:
	@echo "Running tests and generating coverage reports - minimum $(MIN_COVERAGE)%%"
	@poetry run coverage run manage.py test
	@poetry run coverage report -m --fail-under=$(MIN_COVERAGE)

.PHONY: format
format:
	@poetry run flake8
	@poetry run black .
	@poetry run isort .

.PHONY:db_population
db_population:
	@poetry run python manage.py seed_roles
	@poetry run python manage.py seed_claims
	@poetry run python manage.py seed_users
