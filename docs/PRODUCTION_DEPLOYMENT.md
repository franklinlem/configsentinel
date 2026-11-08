# Relatório de Implantação em Produção — ConfigSentinel

**Data:** 08/11/2026  
**Domínio de Produção:** [https://configsentinel.franklem.uk](https://configsentinel.franklem.uk)  
**Ambiente Coolify:** `production` (Environment ID: 11)  
**Aplicação Coolify:** `configsentinel-producao` (ID: 12, UUID: `rtk5g5dxkq498fiw9k23marq`)  
**Status Operacional:** **PRODUÇÃO ATIVA E SAUDÁVEL (GO)**  

---

## 1. Resumo Executivo

A stack de produção do **ConfigSentinel** foi provisionada e implantada com sucesso no servidor Contabo via Coolify, operando de forma 100% isolada da stack de homologação (`configsentinel-dev.franklem.uk`).

Todos os componentes da arquitetura foram validados:
- Banco de dados PostgreSQL 17 endurecido com segregação estrita de roles (`owner`, `migrator` e `runtime`), sem concessão de superusuário à API.
- Execução automatizada e isolada de migrações (`--migrate`) no bootstrap inicial via container descartável.
- API RESTful em Go com restrição de privilégios e validação de runtime ativa.
- Interface Web moderna em React/Vite com suporte a tema escuro/claro, feedback visual em ações e proteção CSRF.
- Roteamento e terminação TLS automática via Traefik.
- Monitoramento ativo de disponibilidade no Uptime Kuma (Monitor ID 23) integrado ao canal de alertas `HermesFranklem`.

---

## 2. Infraestrutura e Configuração

### 2.1 Especificação Docker Compose (`deploy/compose.production.yml`)
- **`db`:** Build local a partir de `deploy/postgres/Dockerfile` com inicialização de roles de privilégio mínimo em volume dedicado `configsentinel_prod_postgres_data`.
- **`migrate`:** Container one-shot executando `/app/server --migrate` com identidade `configsentinel_migrator` e elevação transitória a `configsentinel_owner`.
- **`api`:** Serviço principal executando `/app/server` com identidade não privilegiada `configsentinel_runtime`. Depende da finalização com sucesso de `migrate`.
- **`web`:** Nginx unprivileged servindo os assets estáticos compilados da SPA e efetuando proxy reverso interno para a API.

### 2.2 Isolamento e Segurança
- **Segregação de Volumes:** O volume de dados de produção `configsentinel_prod_postgres_data` é independente do volume de homologação.
- **Redes Isoladas:** Redes internas `database` e `app` impedem comunicação não autorizada; apenas o container `web` se conecta à rede pública `coolify` (Traefik).
- **Proteção de Credenciais:** As senhas do PostgreSQL, Migrador, Runtime e Administrador foram geradas criptograficamente e armazenadas com permissão restrita (0600) em `.local/prod.env` (ignorado pelo Git).

---

## 3. Histórico do Deploy no Coolify

- **Commit de Produção:** `94ed78491969012ac31457f92a7de82787cf1682` (branch `main`).
- **Deployment UUID:** `d98c7a30-baf4-4cc4-b1a2-560d15f251ea`.
- **Resultado:** `status: finished`.
- **Containers Ativos:**
  - `db-rtk5g5dxkq498fiw9k23marq-20261108T151520`: `Up (healthy)`
  - `migrate-rtk5g5dxkq498fiw9k23marq-20261108T151520`: `Exited (0)`
  - `api-rtk5g5dxkq498fiw9k23marq-20261108T151520`: `Up (healthy)`
  - `web-rtk5g5dxkq498fiw9k23marq-20261108T151520`: `Up (healthy)`

---

## 4. Validação e Testes Ponta a Ponta

| Teste | Endpoint | Resultado Esperado | Resultado Obtido | Status |
|---|---|---|---|:---:|
| **Central Readiness** | `GET /api/health/ready` | HTTP 200 `{"status":"ready"}` | HTTP 200 `{"status":"ready"}` | **PASS** |
| **Página Inicial (Web)** | `GET /` | HTTP 200 (HTML da SPA) | HTTP 200 (HTML SPA carregado) | **PASS** |
| **Autenticação Admin** | `POST /api/v1/auth/login` | HTTP 200, Cookie `cs_session`, CSRF | HTTP 200, Cookie Strict, CSRF token | **PASS** |
| **Dados do Usuário** | `GET /api/v1/me` | HTTP 200, Email e ID do Admin | `{"email":"franklinlem@yahoo.com",...}` | **PASS** |
| **Listagem de Servidores**| `GET /api/v1/servers` | HTTP 200 `{"items":[]}` | HTTP 200 `{"items":[]}` | **PASS** |

---

## 5. Observabilidade e Monitoramento

- **Uptime Kuma (Host `frank-note2`):**
  - **Monitor ID:** `23`
  - **Nome:** `ConfigSentinel · Produção`
  - **Tipo:** `http` (GET readiness)
  - **URL:** `https://configsentinel.franklem.uk/api/health/ready`
  - **Intervalo:** 60 segundos (Retry: 30s / 2 tentativas)
  - **Canal de Notificação:** `HermesFranklem` (`notification_id: 1`)
  - **Status Inicial:** **1 (UP)** — Latência de resposta com TLS: ~674 ms.
