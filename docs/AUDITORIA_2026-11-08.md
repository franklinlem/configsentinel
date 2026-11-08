# Relatório de Auditoria e Resolução — ConfigSentinel

**Data da Auditoria:** 08/11/2026  
**Ambientes Auditados:**
- **Produção:** [https://configsentinel.franklem.uk](https://configsentinel.franklem.uk) (VPS Contabo)
- **Homologação:** [https://configsentinel-dev.franklem.uk](https://configsentinel-dev.franklem.uk) (VPS Contabo)
- **Host de Observabilidade e Backups:** `frank-note2`
- **Workstation de Desenvolvimento:** `frank-note1` (`/mnt/HD-NOTE1/apps-skills/configsentinel`)

**Branch de Trabalho:** `ops/homologation-rc2-window` (sincronizada com `main`)  
**Commit Inicial da Sessão:** `44bc612` $\rightarrow$ **Commit Final:** `70ab48d`  
**Status Geral dos Ambientes:** **ATIVOS, HEALTHY E MONITORADOS (GO)**

---

## 1. Levantamento e Estado dos Ambientes

### 1.1 Central de Produção (`https://configsentinel.franklem.uk`)
- **Aplicação Coolify:** `configsentinel-producao` (ID: `12`, UUID: `rtk5g5dxkq498fiw9k23marq`, ambiente `production` ID: `11`).
- **Commit em Execução:** `44bc612a4df7ee61a6b65ee2a2b02a275fdf8b1a` (branch `main`).
- **Docker Compose:** `deploy/compose.production.yml`.
- **Containers Ativos no Host Contabo:**
  - `web-rtk5g5dxkq498fiw9k23marq-...`: `Up (healthy)`, porta interna `8080`, Traefik TLS Let's Encrypt ativo.
  - `api-rtk5g5dxkq498fiw9k23marq-...`: `Up (healthy)`, portas internas `8081` (REST) e `9090` (Métricas).
  - `migrate-rtk5g5dxkq498fiw9k23marq-...`: `Exited (0)` (one-shot bootstrap de migrações).
  - `db-rtk5g5dxkq498fiw9k23marq-...`: `Up (healthy)`, porta interna `5432`, volume dedicado `configsentinel_prod_postgres_data`.
- **Endpoints Validados:**
  - `GET /api/health/ready` $\rightarrow$ `HTTP/2 200 {"status":"ready"}`
  - `GET /` $\rightarrow$ `HTTP/2 200` (SPA React carregada com suporte ao tema Claro/Escuro e badge dinâmico `PRODUÇÃO`)
  - `POST /api/v1/auth/login` $\rightarrow$ `HTTP/2 200` (Cookie seguro `cs_session` HttpOnly + token CSRF)
- **Base de Dados:** Schema versão 2 aplicado; roles segregadas (`owner`, `migrator`, `runtime`); dados administrativos iniciais íntegros (1 usuário, 2 organizações, 2 projetos, 2 ambientes, 1 servidor, 3 agentes provisionados, 9 logs de auditoria).

### 1.2 Central de Homologação (`https://configsentinel-dev.franklem.uk`)
- **Aplicação Coolify:** `configsentinel-homologacao` (ID: `11`, UUID: `oi6lvzwzomwtbbgzf5uzofuh`).
- **Commit em Execução:** `36baf66f4656f86d157cd070202323db9465c5f4` (branch `plan/active-homologation-rc2`).
- **Containers Ativos no Host Contabo:**
  - `oi6lvzwzomwtbbgzf5uzofuh-web-1`: `Up (healthy)`.
  - `oi6lvzwzomwtbbgzf5uzofuh-api-1`: `Up (healthy)`.
  - `oi6lvzwzomwtbbgzf5uzofuh-migrate-1`: `Exited (0)`.
  - `oi6lvzwzomwtbbgzf5uzofuh-db-1`: `Up (healthy)`, volume `oi6lvzwzomwtbbgzf5uzofuh_postgres_data`.
- **Endpoints Validados:**
  - `GET /api/health/ready` $\rightarrow$ `HTTP/2 200 {"status":"ready"}`
- **Base de Dados:** Schema versão 2 aplicado; dados preservados (2 usuários, 4 eventos, 3 reconhecimentos, 8 agentes, 15 logs de auditoria).

---

## 2. Auditoria e Resolução do Backup de Produção

### 2.1 Análise das Rotinas e do Backup Genérico da Contabo
- **Lacuna Crítica Identificada (P0):** A rotina existente em `frank-note2` (`configsentinel-backup.service`) executava exclusivamente o export do container `oi6lvzwzomwtbbgzf5uzofuh-db-1` (Homologação). **Não havia rotina de backup nem agendamento para o banco de produção.**
- **Auditoria do Backup Genérico da Contabo:** O script `/usr/local/sbin/backup-contabo` no `frank-note2` e os pacotes `.tar.gz` diários em `/srv/storage/backups/contabo/daily/` cobrem **exclusivamente os metadados do Coolify** (`coolify-db.dump` e `/data/coolify`). **O backup genérico NÃO executa pg_dump nem inclui cópias consistentes dos bancos de dados das aplicações hospedadas.**

### 2.2 Pipeline de Produção Implementado
A solução foi arquitetada espelhando o padrão de segurança e privilégios mínimos do projeto:
1. **Export Seguro na VPS Contabo:**
   - Criado `/home/franklin/.local/bin/configsentinel-prod-backup-export` (`0755`).
   - Localiza dinamicamente o container ativo do banco de produção pelas labels Docker Compose (`com.docker.compose.project=rtk5g5dxkq498fiw9k23marq` e `service=db`), garantindo resiliência mesmo após novos deploys no Coolify.
   - Executa `pg_dump -U configsentinel -d configsentinel -Fc` transmitindo diretamente pelo stdout.
2. **Segregação Estrita de Chaves SSH:**
   - Gerado par de chaves SSH dedicado no `frank-note2`: `~/.config/configsentinel-prod-backup/id_ed25519` (`0600`).
   - Adicionada a chave pública em `~/.ssh/authorized_keys` da Contabo com restrição total de execução:  
     `restrict,command="/home/franklin/.local/bin/configsentinel-prod-backup-export" ssh-ed25519 ... configsentinel-prod-backup-only`.
3. **Criptografia Simétrica AES256 e Armazenamento Offsite (`frank-note2`):**
   - Gerada chave simétrica AES256 em `~/.config/configsentinel-prod-backup/encryption.key` (`0600`) com cópia de contingência em `contingency/`.
   - Armazenamento em `~/.local/share/configsentinel-prod-backups/daily` e `weekly` (`0700`), preservando todas as cópias com checksums SHA-256 e fsync atômico.
4. **Agendamento e Monitoramento Automático:**
   - Timer de usuário `configsentinel-prod-backup.timer` habilitado (execução diária às 03:45 America/Sao_Paulo, com jitter e `Persistent=true`).
   - Criado o monitor push no Uptime Kuma **ID 24**: `ConfigSentinel · Produção · Backup criptografado`, com intervalo de 600s e vinculado ao canal `HermesFranklem`.
   - Timer `configsentinel-prod-backup-monitor.timer` executando a cada 5 minutos com teste de decriptação, verificação de idade e validação de checksum antes de notificar o Kuma.

### 2.3 Ensaio de Restore Isolado (RPO e RTO Comprovados)
Realizado teste de restauração em container PostgreSQL descartável com rede desativada (`--network none`) e dados em RAM (`--tmpfs`), **sem montar nem sobrepor o volume ativo de produção**:
- **Checksum SHA-256:** `0e18d1f75d03f750e754c0796cc3d907743a1aa11d9443c50e8f24065d04b230` $\rightarrow$ **VALIDADO**.
- **Schema e Tabelas Restauradas:** Schema 2 integral; 100% das entidades relacionais coincidem com a base ativa de produção:
  - 1 usuário, 2 organizações, 2 projetos, 2 ambientes, 1 servidor, 3 agentes provisionados, 9 logs de auditoria, 0 eventos pendentes.
- **Tempo de Decriptação e Streaming (`pg_restore`):** **395 ms**.
- **Tempo Total da Operação (incluindo bootstrap do container em tmpfs):** **2.762 ms** (~2,7 segundos).
- **RTO (Recovery Time Objective):** $\approx \mathbf{2,8\text{ s}}$ para restore completo do banco.
- **RPO (Recovery Point Objective):** $\le \mathbf{24\text{ horas}}$ (agendamento diário com auditoria contínua a cada 5 min).
- *Escopo do Teste:* Validou integridade criptográfica, DDL, constraints, relacionamentos, roles e grants. Não inclui binários de agentes ou arquivos de configuração do host externo.

---

## 3. Auditoria de Monitores e Recursos Operacionais

### 3.1 Status dos Monitores Uptime Kuma (`frank-note2`)

| ID | Nome | Tipo | Alvo / Configuração | Intervalo | Último Status | Amostra Recente | Canal de Alerta |
|:---:|---|:---:|---|:---:|:---:|:---:|---|
| **20** | `ConfigSentinel · Homologação` | HTTP | `https://configsentinel-dev.franklem.uk/api/health/ready` | 60s | **1 (UP)** / 200 OK (678 ms) | 19:48:08 UTC | *Nenhum (silenciado)* |
| **21** | `ConfigSentinel · Backup criptografado` | Push | Token de Homologação | 600s | **1 (UP)** / `backup verified` | 19:48:25 UTC | `HermesFranklem` (ID 1) |
| **22** | `ConfigSentinel · Agente sintético` | Push | Token de Alertas do Agente Lab | 600s | **1 (UP)** / `agents_healthy` | 19:47:29 UTC | `HermesFranklem` (ID 1) |
| **23** | `ConfigSentinel · Produção` | HTTP | `https://configsentinel.franklem.uk/api/health/ready` | 60s | **1 (UP)** / 200 OK (673 ms) | 19:48:10 UTC | `HermesFranklem` (ID 1) |
| **24** | `ConfigSentinel · Produção · Backup criptografado` | Push | Token de Produção | 600s | **1 (UP)** / `backup verified` | 19:53:55 UTC | `HermesFranklem` (ID 1) |

### 3.2 Auditoria do Agente no Host `frank-note2`
- **Classificação:** **SINTÉTICO DE LABORATÓRIO** (`configsentinel-agent-lab`), executando em container Docker.
- **Destino:** Central de homologação (`https://configsentinel-dev.franklem.uk/api/v1`), Agent ID `30f73ffc-182d-4e06-95c8-3b00b6750d75`.
- **Versão:** `0.1.0`.
- **Métricas:** Heartbeat ativo a cada 5s, `queue_depth: 0`, `clock_skew_warning: false`.
- **Privilégios:** Roda sob UID não-root `10001:10001`; mounts `/config` e `/fixtures` em modo Read-Only; banco de estado `/state/events.sqlite` com permissão restrita `0600`.

### 3.3 Inventário de Containers Antigos de Ensaios na Contabo (Proposta de Limpeza)

| Container | Imagem / Propósito | Estado Atual | Idade | Risco da Remoção |
|---|---|:---:|:---:|---|
| `configsentinel-j5-phase1-b5a30125ea-php` | PHP CLI diagnóstico J5 | `Up (unhealthy)` | 4 dias | **Nenhum risco.** Consome memória sem tráfego; ensaio concluído. |
| `configsentinel-j5-phase1-b5a30125ea-db` | Postgres 15 isolado | `Up` | 4 dias | **Nenhum risco.** Banco descartável do diagnóstico J5. |
| `configsentinel-j3-only-75b83f38d188-db` | Postgres 17 isolado | `Up` | 7 horas | **Nenhum risco.** Container de teste do restore de 08/11. |
| `configsentinel-j3-only-f606d879c7e7-db` | Postgres 17 isolado | `Up` | 3 dias | **Nenhum risco.** Ensaio isolado J3. |
| `configsentinel-j3-only-389d5e04d4d5-db` | Postgres 17 isolado | `Up` | 3 dias | **Nenhum risco.** Ensaio isolado J3. |
| `configsentinel-j3-only-f357d5b00e58-db` | Postgres 17 isolado | `Up` | 3 dias | **Nenhum risco.** Ensaio isolado J3. |
| `configsentinel-j3-only-6f5b6c1fc382-db` | Postgres 17 isolado | `Up` | 4 dias | **Nenhum risco.** Ensaio isolado J3. |
| `configsentinel-j3-only-c1b3ef1426f3-db` | Postgres 17 isolado | `Up` | 4 dias | **Nenhum risco.** Ensaio isolado J3. |
| `configsentinel-readiness-agent-stage-*` (2 cont.) | Agentes de ensaio | `Created` | 4-5 dias | **Nenhum risco.** Inativos. |
| `configsentinel-capacity-rehearsal-*` (5 cont.) | Rehearsal API/DB | `Exited` | 4 dias | **Nenhum risco.** Inativos. |
| `configsentinel-schema2-fallback-*` (3 cont.) | Fallback teste | `Exited` | 4 dias | **Nenhum risco.** Inativos. |
| `configsentinel-review-rollback-*` (3 cont.) | Rollback teste | `Exited` | 4 dias | **Nenhum risco.** Inativos. |
| `configsentinel-prechecks-*` (8 cont.) | Prechecks antigos | `Exited` | 7 dias | **Nenhum risco.** Inativos. |
| `configsentinel-rehearsal-9e8f62fc71-*` (9 cont.) | Rehearsal antigo | `Exited` | 7 dias | **Nenhum risco.** Inativos. |

*Nenhum container foi removido sem a prévia autorização expressa do operador.*

---

## 4. Testes de Segurança e Qualidade de Software

1. **Testes Unitários do Agente (`apps/agent`):**
   - 17 testes executados $\rightarrow$ **100% PASS** (recusa de FIFOs com `O_NONBLOCK`, desacoplamento de heartbeat sob travamento de coleta, persistência transacional em SQLite e bloqueio de symlinks em chaves).
2. **Testes da API REST (`apps/api`):**
   - Testes unitários (Argon2id, serialização estrita de JSON, validação de schemas) $\rightarrow$ **100% PASS**.
   - Testes de integração PostgreSQL com banco isolado:
     - `TestPostgresAuthorizationAndIngestion`: **PASS** (garante negação de DDL ao runtime e isolamento tenant).
     - `TestRetentionInIsolatedPostgres`: **PASS** (garante retenção e integridade de auditoria).
     - `TestReadinessTokenAndSessionBoundaries`: **PASS** (validação de tokens de uso único, hash de credenciais, CSRF e expiração).
     - `TestReadinessAlertCharacterization`: **PASS** (detecção precisa de offline, atraso e fila).
     - `TestHeartbeatClockSampleSeparatesStaleCollection`: **PASS** (diferenciação de relógio incorreto vs coleta atrasada).
     - `TestReadinessIngestionQueryCost`: **PASS** (custo de queries e batching).
3. **Frontend Web (`apps/web`):**
   - Compilação com TypeScript 7 e Vite 8.3.5 $\rightarrow$ **0 erros**.
   - `npm audit --audit-level=high` $\rightarrow$ **0 vulnerabilidades encontradas**.
   - Resolução dinâmica de ambiente via hostname em execução (evita exibição indevida de homologação em produção).

---

## 5. Histórico de Alterações de Código

```text
 M docs/AUDITORIA_2026-11-08.md     (este relatório completo de auditoria)
 M docs/PRODUCTION_TODO.md          (atualização de status de prontidão e backup)
 M docs/runbooks/backup.md          (procedimento operacional do backup de produção)
 M scripts/check-backup-health.py   (parâmetro --service-name para múltiplos timers)
 M scripts/monitor-backups.py       (repassa --service-name ao script de verificação)
 M scripts/restore-test.sh          (provisiona roles automaticamente no restore de teste)
```

**Commits Relevantes:**
- `44bc612`: *fix(web): dynamically render environment badge (PRODUÇÃO vs HOMOLOGAÇÃO) based on hostname*
- `70ab48d`: *feat(backup): implement encrypted offsite backup, monitoring and isolated restore for production*
