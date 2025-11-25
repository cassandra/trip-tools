NOW_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')

SCRIPTS = deploy/env-generate.py deploy/run_container.sh deploy/docker-compose-env-convert.py deploy/deploy-prod.sh

# Docker daemon check - fails fast if Docker is not running
.PHONY: check-docker
check-docker:
	@docker info > /dev/null 2>&1 || (echo "ERROR: Docker is not running. Please start Docker and try again." && exit 1)

.SECONDARY:

.DEFAULT_GOAL := fix-permissions

test:
	./src/manage.py test --keepdb custom tt

test-parallel:
	./src/manage.py test --keepdb custom tt --parallel 4

# SQLite tests (fast, good for rapid iteration)
test-sqlite:
	DJANGO_SETTINGS_MODULE=tt.settings.ci ./src/manage.py test custom tt

test-sqlite-parallel:
	DJANGO_SETTINGS_MODULE=tt.settings.ci ./src/manage.py test custom tt --parallel 4

lint:
	flake8 --config=src/.flake8-ci src/tt/ 2>/dev/null

lint-strict:
	flake8 --config=src/.flake8 src/tt/ 2>/dev/null

check:	lint test

docker-build:	check-docker Dockerfile
	@TT_VERSION=$$(cat TT_VERSION); \
	docker build \
		--label "name=tt" \
		--label "version=$$TT_VERSION" \
		--label "build-date=$(NOW_DATE)" \
		--tag tt:$$TT_VERSION \
		--tag tt:latest .

docker-run:	.private/env/local.dev Dockerfile fix-permissions
	./deploy/run_container.sh -bg

docker-run-fg:	.private/env/local.dev Dockerfile fix-permissions
	./deploy/run_container.sh

docker-stop:	
	docker stop tt

env-build:	.private/env/local.dev fix-permissions
	./deploy/env-generate.py --env-name local

env-build-dev:	.private/env/development.sh fix-permissions
	./deploy/env-generate.py --env-name development

.private/env/local.dev:

.private/env/development.sh:

.PHONY:	fix-permissions

fix-permissions:
	@echo "Setting execute permissions for $(SCRIPTS)"
	chmod +x $(SCRIPTS)

# Pattern rule: Convert bash env files to docker-compose .env format
.private/env/docker-compose.%.env:	.private/env/%.sh deploy/docker-compose-env-convert.py
	@echo "Converting $< to docker-compose format..."
	./deploy/docker-compose-env-convert.py $< $@

# Docker deployment targets
docker-push:
	@TT_VERSION=$$(cat TT_VERSION); \
	echo "Saving Docker image tt:$$TT_VERSION to tar.gz..."; \
	docker save tt:$$TT_VERSION | gzip > /tmp/tt-docker-image-$$TT_VERSION.tar.gz; \
	echo "Image saved: $$(du -h /tmp/tt-docker-image-$$TT_VERSION.tar.gz | cut -f1)"

deploy-prod:	check-docker .private/env/docker-compose.production.env fix-permissions
	./deploy/deploy-prod.sh


