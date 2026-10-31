# Changelog

## 0.1.0-rc.1 — 2026-10-31

Primeira homologação funcional: API Go com tenancy/RBAC, sessões Argon2id e CSRF; agente Linux hash-only com openat2 e fila SQLite transacional; painel React em português com investigação, reconhecimento e credenciais de exibição única.

Inclui monorepo privado, OpenAPI 3.1.2, Compose, CI Go/React, binários Linux amd64/arm64, testes de isolamento/replay/filesystem/offline, monitor Uptime Kuma e backup criptografado diário fora da VPS com restore ensaiado. Laboratório frank-note2 usa somente fixture sintética.

Produção aguarda aceite e gates descritos em docs/validation.md. Não há conteúdo/diffs/comandos remotos. Benchmark local com 25 agentes / lotes de 100 / 5 lotes concorrentes teve p95 de 349,86 ms: acima da meta indicativa de 300 ms, sem erros. Isso exige calibrar a meta/otimizar antes de assumir SLO.
