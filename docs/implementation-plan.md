# Plano de implementação — ConfigSentinel

Referência: documento mestre na raiz, v1.0 (31/10/2026). Execução autorizada por Franklin em 31/10/2026, incluindo GitHub, SSH, Coolify e Uptime Kuma.

## Sequência e aceite

1. Fundação: monorepo, ADRs, PostgreSQL privado, API Go/Chi, React/TS, contrato OpenAPI e Compose.
2. Identidade: Argon2id, sessões revogáveis, CSRF, organização/projeto/ambiente, RBAC e testes entre tenants (RF-001–005, 013, 017).
3. Agente: Linux openat2 sem symlinks, arquivos regulares controlados, hash-only, máquina de estados, SQLite transacional e limites (RF-006–012).
4. Fluxo: ingestão autenticada, UUID/seq idempotentes, conflito explícito, heartbeat e reconhecimento auditado (RF-009–017).
5. Painel: login, visão geral, servidores, arquivos por alias, filtros, credenciais uma vez, auditoria e alertas (RF-014–017).
6. Operação: CI, binários amd64/arm64, métricas privadas, retenção e runbooks (RF-018).
7. Homologação isolada na Contabo: DNS existente, TLS, banco e secrets exclusivos, agente apenas sobre fixture sintética, backup/restore isolado.
8. Produção: depende de aceite da homologação. Não promover automaticamente.

## Decisões

- Tenancy desde a primeira migration; admin de projeto restrito ao projeto atribuído; Owner organiza membros.
- Go estável verificado no feed oficial; Node 24 LTS; PostgreSQL 17; módulos Go independentes.
- Cookie de sessão opaco, token e CSRF aleatórios; somente hashes persistidos. Login usa limite de tentativas.
- Allowlist local imutável pela central; aliases únicos; sem conteúdo, diffs ou comandos remotos.
- Limite de fila: bloquear avanço de snapshot quando cheia, sinalizando erro; nunca descartar eventos já persistidos.
- Somente laboratório sintético em frank-note2. Não ler configurações reais sem lista revisada.
- GitHub inicialmente privado; licença MIT. Deploy manual.
- Backups: comprovar restore antes de promoção; distinguir ensaio de agendamento recorrente.

## Evidências

Resultados e limites reais serão registrados em docs/validation.md. Não considerar cenários executados até haver evidência.
