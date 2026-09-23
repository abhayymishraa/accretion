.PHONY: backend frontend template-build

backend:
	uv run --env-file .env python -m db.migrate
	uv run --env-file .env python -m agent.storage.init_storage
	uv run --env-file .env uvicorn main:app --reload --port 8000

frontend:
	npm --prefix frontend run dev -- --port 3000

# Authenticate the E2B CLI or export E2B_API_KEY before building.
# Use a fresh release name, e.g. webbuilder-react-design-20260917-1.
template-build:
	$(if $(TEMPLATE_NAME),,$(error Set TEMPLATE_NAME to a new template release name))
	npx --yes @e2b/cli@2.19.0 template create "$(TEMPLATE_NAME)" \
		--path sandbox --dockerfile e2b.Dockerfile \
		--cpu-count 1 --memory-mb 1024 --min-free-disk-mb 2048 \
		--cmd 'cd /home/user/react-app && exec node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173 --strictPort' \
		--ready-cmd 'test "$$(curl --silent --connect-timeout 2 --max-time 5 --output /dev/null --write-out "%{http_code}" http://127.0.0.1:5173/)" = 200'
