# ConfigSentinel

Observabilidade self-hosted de integridade de configurações. Agente Linux Go, API Go/Chi, PostgreSQL e painel React/TypeScript. Hash-only: arquivos e paths permanecem no host. Não há conteúdo, diff ou comandos remotos.

## Desenvolvimento

Requisitos: Go 1.27.3, Node 24, Docker Compose. Copie `.env.example` para `.env` e substitua os segredos por valores aleatórios (senha admin de pelo menos 16 caracteres). Execute:

```sh
npm ci --prefix apps/web
make test build check
docker compose --env-file .env -f deploy/compose.dev.yml up --build -d
```

Acesse http://localhost:8080. O bootstrap cria owner, organização, projeto Infraestrutura e ambiente Homologação apenas em banco vazio. A senha não é sobrescrita nos próximos boots. Banco sem porta publicada. Métricas disponíveis apenas na rede Docker em `api:9090/metrics`.

## Fluxo

1. Entre como owner. Em Projetos e ambientes, crie seu servidor lógico.
2. Em Credenciais, provisione uma instalação; guarde o token exibido uma vez.
3. Revise `apps/agent/agent.example.yaml` no host autorizado, sempre com arquivos individuais e `hash_only: true`.
4. Rode o agente como usuário dedicado sem privilégios. Primeira coleta cria baseline; alterações posteriores geram eventos.
5. Investigue o histórico; reconhecimentos preservam evento, ator, comentário e data.

## Verificação

```sh
TEST_DATABASE_URL='postgresql://postgres:...@localhost:5432/testdb?sslmode=disable' make test
```

Integração cria um schema temporário isolado e o remove ao terminar. Sem TEST_DATABASE_URL o teste PostgreSQL é marcado como skipped; não equivale a integração validada. Testes de filesystem usam fixtures temporárias. HTTP do agente somente com IP loopback e opt-in explícito para laboratório.

## Documentação

- [Plano mestre](ConfigSentinel_Plano_Completo_Engenharia_Software.md)
- [Backlog de implementação](docs/implementation-plan.md)
- [Arquitetura](docs/adr/0001-architecture.md)
- [Proteção do filesystem](docs/adr/0002-agent-filesystem.md)
- [Modelo de ameaças](docs/threat-model.md)
- [Contrato OpenAPI](api/openapi.yaml)
- [Implantação](deploy/coolify.md)
- [Evidências e limitações](docs/validation.md)
- [Runbooks](docs/runbooks/installation.md)

MVP em desenvolvimento/homologação. Produção depende de aceite explícito. Metas de disponibilidade, RPO/RTO e resistência contra root comprometido não são garantias. Licença MIT.
