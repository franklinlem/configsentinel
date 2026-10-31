# Evidências de homologação — 31/10/2026

## Entrega

- Repositório privado: https://github.com/franklinlem/configsentinel.
- Homologação: https://configsentinel-dev.franklem.uk.
- Coolify: projeto ConfigSentinel `e7effkibiwnrgnsw079rxplp`, ambiente homologacao `klbnshornbwxbbxydohd7ayt`, aplicação `oi6lvzwzomwtbbgzf5uzofuh`.
- Primeiro deploy `ppnbtbejfptkajfvgfdwpvdq`, revisão `5d5f723`, terminou com web/api/db saudáveis. Revisão final da entrega está registrada no histórico Git e nos deployments Coolify.
- Deploy manual; API pública do Coolify permaneceu desativada. Controllers autenticados foram usados via SSH com credencial temporária, sem alterar o switch global.
- Produção não foi publicada: o plano condiciona promoção a aceite da homologação.

## Verificação executada

| Verificação | Resultado |
|---|---|
| Go 1.27.3 oficial | Download Linux amd64 com SHA-256 verificado |
| API: go test -race + PostgreSQL 17 real | Passou; schema temporário isolado removido no final |
| Autorização | Sem sessão 401; CSRF inválido 403; organização alheia 404; viewer não emite token; admin restrito ao projeto não vê outro projeto da mesma organização |
| Replay | Mesmo UUID/seq/payload retorna duplicates; payload divergente 409 e auditoria; só 2 eventos únicos no cenário isolado |
| Sessão/token | Logout revoga sessão; token revogado recebe 401; tokens em banco apenas com hash |
| Reconhecimento/retensão | Comentário e ator persistidos; retenção >90 dias remove eventos/acks e preserva auditoria administrativa |
| Agente: go test -race | Passou; symlink final/intermediário, troca por symlink, hardlink, FIFO, diretório, limites e denylist |
| Fila SQLite | Evento persistido após reabertura; seq contínua; identidade divergente rejeitada; fila cheia não avança snapshot |
| Máquina de estados | 95% de cobertura de statements em Transition; core total 74% |
| Autorização API | access 81%, middleware admin 100%; package server 57,8% (não declarar cobertura total 80%) |
| Fluxo local real do agente | baseline → modified → deleted → restored → reconhecimento confirmado |
| Navegador local e HTTPS de homologação | Login, navegação, detalhes/reconhecimento, desktop/mobile, sem erros JS; verificações axe WCAG A/AA executadas sem violações no overview |
| Segurança de dependências | npm audit: 0 vulnerabilidades; govulncheck: 0 vulnerabilidades alcançáveis em API/agente; 1 achado em módulo requerido pela API não chamado pelo código |
| Segredos | Gitleaks sem leaks após classificar exatamente o placeholder não secreto do primeiro commit em .gitleaksignore |
| Contrato | OpenAPI 3.1.2: 24 paths validados pelo swagger-parser |
| CI | Duas primeiras execuções completas verdes, incluindo módulos Go, builds amd64/arm64 e imagens; pipeline final adiciona navegador/axe e secret scan |

Fixtures contêm apenas texto sintético. Testes não leem configurações reais do sistema. A inspeção de capturas desktop e mobile foi realizada pelo assistente; aceite visual e funcional de Franklin continua separado.

## Rede e TLS

- TLS validado sem ignorar certificados. Let's Encrypt, issuer YR2; validade observada 31/10/2026 a 29/01/2027.
- `/`: 200; `/api/health/live`: 200; `/api/health/ready`: 200.
- `/api/v1/events` sem sessão: 401; `/metrics` público: 404.
- Sem portas do host nos três serviços. Somente web está em `coolify`; api em redes app/database; db somente database, internal=true. API UID/GID 10001, web UID 101.
- Volumes, secrets e redes exclusivos. Outros projetos não foram alterados.

## Piloto frank-note2

- Container `configsentinel-agent-lab`, UID/GID 10001, filesystem read-only, cap_drop=ALL, no-new-privileges, sem portas ou Docker socket.
- Somente `/fixtures/demo.conf` é monitorado. Config/token ro e fila em volume próprio. Sudo do host exige senha; nenhuma instalação systemd/usuário/permissão de arquivo real foi realizada. Ver ADR 0003.
- Desconexão controlada alterando URL apenas no config do laboratório, sem mudar firewall ou roteador.
- Resultado: 108 segundos de ensaio, 3 eventos persistidos, UUIDs preservados após reinício e fila 0 após retorno. Eventos modified/deleted/restored recebidos na central.
- Intervalo do laboratório: 5 segundos, diferente do padrão de 60 segundos. Escopo não habilita monitoramento de arquivos reais.

## Backup e monitoramento

- Uptime Kuma: monitor ID 20, `ConfigSentinel · Homologação`, GET readiness, 60 s, TLS verificado, 2 retries. Sem acoplar canais de notificação existentes.
- Timer de usuário no frank-note2 habilitado e com linger: diário 03:35 America/Sao_Paulo + até 120 s de jitter; Persistent=true.
- Pull por chave SSH exclusiva com forced command/restrict na Contabo; exporta apenas pg_dump do banco ConfigSentinel. Sem capacidade de shell pelo novo credential.
- Criptografia GPG AES256; checksum SHA-256; 7 diários e 4 semanais; primeiro snapshot da semana preservado.
- Destino fora da VPS: `~/.local/share/configsentinel-backups` no frank-note2. Chave de criptografia 0600 separada em `~/.config/configsentinel-backup/encryption.key`.
- Execução manual do mesmo serviço agendado: Result=success, ExecMainStatus=0. Agendamento é verificável com `systemctl --user list-timers configsentinel-backup.timer`.
- Restore comprovado com pg_restore --exit-on-error em PostgreSQL descartável, rede none e dados tmpfs. Schema versão 1 e registros conferidos; container de restore removido ao final.
- Backup não inclui arquivos, token/config/fila do agente nem credenciais Coolify. Ainda é necessário o operador guardar cópia da chave de criptografia em local protegido separado do frank-note2. Monitor HTTP não verifica idade do backup.

## Limites e gates para produção

- Não há SSO/MFA, recuperação por e-mail, diff, comandos remotos, notificações externas de eventos ou agentes Windows. São pós-MVP; recuperação administrativa disponível via CLI reset-password.
- Não há atestação contra root comprometido, garantia de capturar mudanças entre polls, entrega ilimitada ou RPO/RTO contratado. Saturação preserva a fila existente, mas pode perder mudanças intermediárias não enfileiradas.
- Leituras são limitadas por bytes e estabilidade de stat; utilizar filesystem local. Não foi validado timeout de I/O em filesystem de rede/bloqueado.
- Testes não constituem auditoria externa, fuzzing prolongado ou certificação WCAG. A verificação axe cobriu a jornada e o overview, não todos os estados/perfis possíveis.
- Antes de produção: aceite humano, revisar allowlists reais por servidor, cópia externa da chave de backup, alertas para backup atrasado, imagens da aplicação em registry com SBOM/scanner e promoção por digest. Hoje o Coolify fixa commit e registra imagens locais; não é promoção de imagem de registry.
- Metas de p95/uptime/RPO/RTO não são garantias. Resultados do benchmark limitado são anexados abaixo.

## Benchmark limitado

```json
{
  "environment": "local Docker; five concurrent batches",
  "agents": 25,
  "events": 2500,
  "batch_size": 100,
  "duration_seconds": 1.277,
  "p50_batch_ms": 217.73,
  "p95_batch_ms": 349.86,
  "max_batch_ms": 365.54,
  "errors": 0
}
```

Medição local específica desta máquina; não extrapolar para SLO de produção.
