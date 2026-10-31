# Modelo de ameaças

Fronteiras: host do agente, transporte HTTPS, sessão administrativa, tenant e PostgreSQL. O agente não recebe comandos. Root comprometido está fora da garantia de integridade. Hashes e aliases são metadados sensíveis.

Controles: openat2, tipo regular, hardlinks rejeitados, allowlist local e denylist, limite de leitura/fila/lote; tokens aleatórios com hash e revogação; Argon2id, CSRF, SameSite, Origin exata, RBAC por joins, payload JSON estrito; idempotência com comparação integral do evento e conflito de sequência; logs sem payload/credenciais; métricas privadas; backups e restore isolado.

Testes críticos: symlink final/intermediário, FIFO, hardlink, denylist e mudanças de estado; fila após reinício/saturação; replay divergente; escopo entre tenants; revogação; sessão/CSRF; fluxo fixture→evento→reconhecimento. Nunca usar arquivos reais do sistema em testes.
