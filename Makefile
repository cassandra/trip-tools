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

TEST_JS_PORT := 8765

test-js:
	@echo "Starting test server on http://localhost:$(TEST_JS_PORT)/tests/test-all.html"
	@echo "Press Ctrl+C to stop the server when done."
	@sleep 1 && ( \
		if command -v xdg-open > /dev/null; then \
			xdg-open http://localhost:$(TEST_JS_PORT)/tests/test-all.html; \
		elif command -v open > /dev/null; then \
			open http://localhost:$(TEST_JS_PORT)/tests/test-all.html; \
		fi \
	) &
	@python -m http.server $(TEST_JS_PORT) --directory src/tt/static

# E2E Testing (Playwright)
# Uses nvm if available, otherwise falls back to system node
NVM_SH := $(shell [ -f ~/.nvm/nvm.sh ] && echo ". ~/.nvm/nvm.sh && nvm use &&" || echo "")

test-e2e:
	cd testing/e2e && $(NVM_SH) npm test

test-e2e-webapp-extension-none:
	cd testing/e2e && $(NVM_SH) npm run test:webapp-extension-none

test-e2e-webapp-extension-sim:
	cd testing/e2e && $(NVM_SH) npm run test:webapp-extension-sim

test-e2e-extension-isolated:
	cd testing/e2e && $(NVM_SH) npm run test:extension-isolated

test-e2e-webapp-extension-real:
	cd testing/e2e && $(NVM_SH) npm run test:webapp-extension-real

test-e2e-install:
	cd testing/e2e && $(NVM_SH) npm install && npx playwright install chromium

test-e2e-seed:
	./src/manage.py seed_e2e_data

test-all:	test test-js test-e2e

check:	lint test

docker-build:	check-docker Dockerfile
	@TT_VERSION=$$(cat TT_VERSION); \
	docker build \
		--platform linux/amd64 \
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


