GO ?= go
.PHONY: test build dev check
check:
	cd apps/api && $(GO) vet ./...
	cd apps/agent && $(GO) vet ./...
	test -z "$$(gofmt -l apps/api apps/agent)"
	node scripts/validate-openapi.mjs
test:
	cd apps/api && $(GO) test -race ./...
	cd apps/agent && $(GO) test -race ./...
build:
	mkdir -p bin
	cd apps/api && CGO_ENABLED=0 $(GO) build -trimpath -o ../../bin/configsentinel-api ./cmd/server
	cd apps/agent && CGO_ENABLED=0 $(GO) build -trimpath -o ../../bin/configsentinel-agent ./cmd/configsentinel-agent
	npm --prefix apps/web run build
dev:
	docker compose --env-file .env -f deploy/compose.dev.yml up --build -d
