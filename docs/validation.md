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

## Revisão final de prontidão — 31/10/2026

O MVP v0.1.0-rc.1 recebeu aceite visual de Franklin, conforme instrução desta revisão. Isso substitui a pendência de aceite visual acima, sem autorizar produção. Revisão técnica completa em [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md): **NO-GO**.

Base inspecionada: `5819b7fce93c10cceabbe59fde5fac4f647b707c`; alterações de revisão em `review/production-readiness`. Arquitetura e implantação de homologação preservadas. Produção não criada/deployada, demais serviços e proxy preservados.

- API e agente: testes completos com race e vet passaram; integração em PostgreSQL descartável sem rede/portas. Casos novos verificam tokens/CSRF/sessão, alertas, leituras seguras, fila sem bearer e falha de heartbeat após erro de ingestão.
- Operação: 3 testes passaram (backup com transporte falhando preserva último sucesso; idade/checksum/serviço; rejeição de manifest não aprovado).
- Playwright: 4 testes passaram; zero violações axe A/AA nas sete páginas, larguras 390/768/1280, erro 503 de eventos visível e credencial sintética fora dos storages. `/me` 503 mostrando login permanece lacuna caracterizada. Traces desabilitados para evitar persistência de credenciais.
- Build web e OpenAPI passaram (24 paths). npm audit: 0; govulncheck: zero alcançáveis, um advisory de módulo x/crypto/openpgp não importado pela API.
- **Complemento obrigatório à tabela histórica de dependências:** Trivy das imagens exatas de homologação identificou web com 1 CRITICAL/46 HIGH e banco com 1 CRITICAL/25 HIGH, este último no gosu. API sem HIGH/CRITICAL. Instalação de pacote não prova caminho explorável. Inventário completo e SBOMs em [evidence](evidence/production-readiness-2026-10-31.json). Resultado anterior de npm/Go não abrangia esses componentes de imagem.
- Benchmark repetido: p95 364,53 / 303,83 / 280,71 ms, 7.500 eventos sintéticos novos, zero erros. Meta de 300 ms sem evidência consistente; 304 comandos SQL por lote de 100 eventos, índices presentes. Nenhuma otimização funcional aplicada.
- Backup criptografado recente, checksum válido; restore novamente passou em banco isolado: schema 1, organização 1, eventos 4, reconhecimentos 1. Monitor Kuma continua readiness, sem alerta de frescor/falha do backup. Probe somente leitura preparado e testado uma vez, não instalado/agendado.
- Release imutável: exemplos de Compose/manifest e validador preparados, incluindo banco. Renderização com digests sintéticos passou, sem builds/portas. Manifest de exemplo retorna NO-GO esperado; não publicou registry/atestação nem executou deploy.

Bloqueadores: imagens vulneráveis, API com superusuário PostgreSQL, heartbeat acoplado a Flush, alerta de backup/cópia independente da chave e promoção imutável/rollback ainda não ensaiados. Pendências menores e critérios de encerramento constam no relatório. Aguarda aprovação para correções; nenhuma aprovação de produção foi inferida.

Verificação final de segredos: Gitleaks passou no commit de revisão e nos 5 commits do histórico examinado, sem leaks versionados. A varredura inclui testes, documentação e SBOMs; arquivos locais ignorados com credenciais não foram publicados.

CI remoto final: [execução 41230354166](https://github.com/franklinlem/configsentinel/actions/runs/41230354166), commit `74d41fb695899f542282267fcd2fd32767dd9013`, todos os jobs concluídos com sucesso: API, agente, web/E2E/axe/operação e segredos. A execução anterior `41230318920` também passou. Este registro posterior altera somente documentação. Nova inspeção remota confirmou os mesmos IDs de imagem e os três containers saudáveis, sem redeploy. O banco temporário exclusivo dos testes foi parado ao concluir.

## Correções aprovadas de P0/P1 — candidato para revisão (31/10/2026)

Branch `fix/production-blockers`, baseada em `0524bee`; imagens finais construídas do commit `ea868efaa3e3b364d012981e597c8faf6bc30651`. RC1 ativo e piloto preservados. [Relatório atual](PRODUCTION_READINESS.md), [histórico do RC1](evidence/production-readiness-rc1.md), [manifest real do candidato](../deploy/release-manifest.candidate.json).

- Web reduzida/atualizada e PostgreSQL 17.11 sem gosu: **0 HIGH/CRITICAL**, também zero MEDIUM/LOW/UNKNOWN. Agente zero; API somente GO-2026-5932 UNKNOWN de módulo openpgp não chamado. Sem supressões. Quatro SBOMs runtime e provas de assinatura em `docs/evidence/remediation/`.
- Roles owner NOLOGIN, migrator NOINHERIT e runtime restrito; API recusa administrador e não migra no startup. DDL/elevação/mutação de auditoria negadas; operações da jornada permitidas. Seis testes de operação/roles passaram sem skips com PostgreSQL selecionado.
- Flush em worker independente, heartbeat em 409/422/503 e ingestão bloqueada, fila cheia/reinício, replay com UUID preservado e recuperação testados com race. Fila/piloto existentes não foram atualizados ou descartados.
- Backup corrigido instalado: lock, timeout 300 s, chave obrigatória, metadata atômica e pontos do mesmo dia preservados. Monitor independente a cada 5 min e Kuma **21**, canal HermesFranklem; atraso de 27 h e corrupção de checksum geraram DOWN/UP com fixtures. Provedor Telegram aceitou teste; recepção humana não confirmada. Endpoint loopback existente utilizado sem alterar proxy ou firewall. Cópia de recuperação da chave conferida fora do repositório e do host de backup, 0600.
- Backup anterior e mais recente preservados, SHA-256 válidos. Restore final via GPG/SSH em streaming para volume novo: schema 1, **4 eventos e 2 reconhecimentos**; snapshot anterior da revisão tinha 1 reconhecimento. Nunca restaurou por cima do banco ativo.
- Ensaio remoto isolado por digest: candidato → rollback API/web → rollback PostgreSQL → retorno ao candidato. PostgreSQL 17.11/schema 1, contagens iguais nas quatro etapas, readiness 200 e sem sessão 401. Roles runtime mantidas no rollback. Volume de teste preservado, todos os seus containers parados. [Evidência](evidence/remediation/homologation-rollback.json).
- Repetidos: Go race com `-count=1`, vet, integração PostgreSQL, Playwright (4), axe (0 violações nas sete páginas), build web/OpenAPI (24 paths), govulncheck e npm audit (0). Benchmark anterior continua 280,71–364,53 ms p95, sem nova promessa de desempenho.
- [CI 41253986449](https://github.com/franklinlem/configsentinel/actions/runs/41253986449) completo verde. [Imagens 41253986413](https://github.com/franklinlem/configsentinel/actions/runs/41253986413): quatro builds/scans/SBOMs/assinaturas verdes, registry verificado privado e pull por digest para cache da VPS, sem deploy. Cosign com chave pública fixada e política privada sem Rekor; payloads SBOM assinados conferem com os arquivos e checksums.
- Manifest indica ensaio isolado aprovado, homologação ativa não promovida e aprovações humanas/produção falsas. O validador retorna NO-GO por ausência de autorização de produção. Ele valida declarações; assinatura/autenticidade têm evidência separada.

**Decisão atual: NO-GO para produção; candidato pronto para revisão.** Próxima etapa exige revisão de Franklin antes de promover qualquer candidato. Coolify ativo ainda é RC1; configurar pull somente leitura e procedimento de roles no recurso somente na promoção aprovada. Nenhum serviço de outro projeto, Traefik, DNS, firewall ou porta pública alterado. Produção não foi criada ou implantada.

Repetição final local sem cache: API race passou em 12,121 s; agente/core em 1,412 s, além do runner. Playwright final isolado: 4 testes em 21,1 s, axe sem violações, mantendo limite de 30 s e mesmas asserções. Uma execução concorrente aos checks de compilação atingiu esse limite no axe; não houve relaxamento de timeout ou de regras para a repetição.

Gitleaks final no histórico versionado, incluindo SBOMs/provas de assinatura e documentação: **zero vazamentos**. Arquivos ignorados de credenciais não foram publicados. Inspeção final confirmou os mesmos IDs de imagem do RC1 e todos os containers ativos saudáveis; evidência em `evidence/remediation/active-homologation-final-check.json`.

## Plano da homologação ativa — 31/10/2026, 21:54 -03

Preparado [ACTIVE_HOMOLOGATION_PROMOTION.md](ACTIVE_HOMOLOGATION_PROMOTION.md) e Compose específico com volume/redes existentes externos e pull_policy=never. Validação local com placeholders: quatro serviços, sem builds/portas, roles separadas, API/migrate sem ADMIN_PASSWORD, labels Traefik idênticas às ativas. Parser Coolify com secrets reais permanece gate pré-deploy.

Verificações desta etapa: quatro imagens exatas exportadas do cache e reescaneadas (zero HIGH/CRITICAL); oito assinaturas DSSE de SBOM/provenance revalidadas com a chave pública, commit/digests/checksums correspondentes; archives RC1 0600 com SHA conferido. Assinatura direta online será repetida após pull somente leitura. Backup recente passou em checksum/decriptação; timers saudáveis e quatro pushes de monitor recentes aceitos. Badge Kuma 21 N/A não comprova estado; recebimento humano continua pendente. Somente metadados de variáveis deste UUID foram consultados; nenhuma credencial global de Kuma/Docker acessada. [Novas evidências](evidence/promotion/artifact-recheck.json).

Não repetida suite funcional completa para alteração documental/Compose sem deploy. Testes pós-deploy estão definidos; nenhum smoke mutante foi executado no ativo. Recuperação com web/DB RC1 vulneráveis está vedada; fallback limpo por digest é gate adicional. Central, piloto, fila e backups existentes preservados; nenhuma promoção ou aprovação inferida.

## Confirmação humana dos alertas de backup

Franklin respondeu “Recebi o alerta do ConfigSentinel” e anexou captura do HermesFranklem mostrando os testes DOWN/UP de atraso (16:04) e checksum inválido (16:12), além da mensagem de teste (20:47). A pendência de recebimento humano indicada nos registros anteriores está encerrada para esses testes. [Registro sanitizado](evidence/promotion/alert-receipt-confirmation.json); captura original não versionada por conter conversas e serviços alheios. Horários transcritos da imagem, sem consulta ao provedor.

Continuam pendentes o ensaio de ausência de push e a conferência da configuração atual do monitor 21. Esta confirmação não autoriza promoção; nenhum serviço, token, fila, backup ou configuração foi alterado.

## Prechecks isolados autorizados — 01/11/2026

G1–G6 concluídos no escopo isolado/leitura conforme [checklist](evidence/promotion/precheck-gates.json); G0 continua PENDENTE. Fallback limpo assinado e workflow `packages: read` publicados/testados. API de migração permanece RC2 durante rollback da API HTTP para o fallback RC1 compatível.

Ensaio remoto novo sem portas/Traefik/volumes ativos: restore de backup criptografado, adoção transacional das roles preservando 14 contagens, runtime autenticado por TCP, dez negações 42501 e RC2 → fallback → RC2. Cada estágio passou login/RBAC/CSRF/tenant, ingestão/replay sem duplicação, heartbeat 202, auditoria e invalidação de sessão. Quatro eventos e dois reconhecimentos originais idênticos por ID/conteúdo; snapshots/filas/volumes preservados. Fixtures HTTP usaram IP privado do web com Origin configurado; não constituem smoke TLS pela URL ativa. [Resultados](evidence/promotion/isolated-promotion-rehearsal.json).

Probe no Coolify 4.5.3 executou métodos instalados em clone somente em memória/transação read-only, com SSH e persistência de logs interceptados; validou raw Compose, custom commands e skip do pull. O comando gerado foi executado no projeto isolado. Serialização protegida preservou senha existente e DSNs novos sem exposição. `>/dev/null` não é aceito no comando customizado; `--format '{{.Id}}'` passou. Nenhum job completo de deploy foi disparado.

Monitor 21 consultado somente por ID em transação read-only, sem ler credenciais/configuração global. Recebimento humano confirmado e lógica instalada de timeout/recovery exercitada com relógio isolado, sem alterar timers reais. Ausência real de push por 10 min com entrega end-to-end continua fora do ensaio executado. Backup regular de hoje íntegro; dump adicional de preparação restaurado em isolamento. Snapshot exclusivo de configuração AES256/0600 validado com cópia offsite. Backup final de escritores drenados pertence à futura janela.

Suites Go/Playwright anteriores não foram repetidas por mudanças de documentação/workflows/helpers sem alteração de aplicação. Verificação pertinente nesta etapa: scans/assinaturas online, integração e smoke reais no clone, probes dos métodos instalados, JSON/links/Compose e barreiras de escopo. Erros iniciais do harness foram corrigidos: readiness TCP evita o servidor temporário do initdb e heartbeat espera 202 conforme contrato; não houve correção nem regressão funcional da aplicação nessa etapa.

[Preservação final](evidence/promotion/active-preservation-final.json): RC1 permanece healthy, mesmos containers/imagens e starts desde 31/10, 4 eventos/2 reconhecimentos/1 usuário, três roles novas ausentes. Nenhum serviço ativo, piloto, proxy, DNS, firewall ou produção foi alterado. Procedimento definitivo em [ACTIVE_HOMOLOGATION_PROMOTION.md](ACTIVE_HOMOLOGATION_PROMOTION.md); aguarda autorização específica da janela.
