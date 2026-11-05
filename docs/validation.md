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

Não houve repetição manual das suites Go/Playwright nesta preparação; o CI remoto posterior as executou novamente, conforme complemento abaixo. Verificação pertinente nesta etapa: scans/assinaturas online, integração e smoke reais no clone, probes dos métodos instalados, JSON/links/Compose e barreiras de escopo. Erros iniciais do harness foram corrigidos: readiness TCP evita o servidor temporário do initdb e heartbeat espera 202 conforme contrato; não houve correção nem regressão funcional da aplicação nessa etapa.

[Preservação final](evidence/promotion/active-preservation-final.json): RC1 permanece healthy, mesmos containers/imagens e starts desde 31/10, 4 eventos/2 reconhecimentos/1 usuário, três roles novas ausentes. Nenhum serviço ativo, piloto, proxy, DNS, firewall ou produção foi alterado. Procedimento definitivo em [ACTIVE_HOMOLOGATION_PROMOTION.md](ACTIVE_HOMOLOGATION_PROMOTION.md); aguarda autorização específica da janela.

Complemento final: [CI 41305147386](https://github.com/franklinlem/configsentinel/actions/runs/41305147386), commit `836d297`, passou em todos os jobs: API/agente com race/vet/govulncheck, web/build/OpenAPI/npm audit, testes de operação/roles em PostgreSQL, Playwright/axe e segredos. A repetição manual do workflow read-only [41305428149](https://github.com/franklinlem/configsentinel/actions/runs/41305428149) passou em assinaturas/scans dos cinco digests e cache, validando também workflow_dispatch nesta branch.

O fallback não estava mais no cache ao retomar. A tentativa automática `41305147376` falhou no segundo lote; sua causa exata não foi estabelecida. Após execução manual bem-sucedida, inspeção confirmou os quatro digests centrais disponíveis. Somente o helper de precache recebeu diagnóstico por etapa/categoria; backup de seu código anterior preservado, sem mudança de SSH/auth/serviços ativos. Quatro testes novos verificam não exposição de credenciais em erros, rejeição de repo alheio e isolamento/remoção do Docker config temporário. Gitleaks local passou no diff e seis commits anteriores. [Resumo](evidence/promotion/verification-summary.json). A janela exige nova inspeção de cache, sem assumir durabilidade e sem relaxar nenhum gate.


## Janela ativa autorizada —01/11/2026: interrompida em J3

**NO-GO para aceite da homologação; produção não autorizada.** Recurso exclusivo `oi6lvzwzomwtbbgzf5uzofuh`, preparação fixada em `36baf66f4656f86d157cd070202323db9465c5f4`, código das imagens `ea868efaa3e3b364d012981e597c8faf6bc30651`. Branch de execução separada, sem mover a preparação aprovada.

J0/J1: [workflow 41307377319](https://github.com/franklinlem/configsentinel/actions/runs/41307377319) PASS, headSha autorizado; cinco assinaturas/provenance/SBOMs e scans novos (zero HIGH/CRITICAL, somente UNKNOWN openpgp já documentado em API/fallback), pull read-only, cache dos quatro digests centrais e capacidade conferidos. Coolify 4.5.3/Compose 5.6.1 e caminho instalado reconfirmados; serializers/Compose preservam credenciais, volume/redes externos, ausência de build/portas e separação migrator/runtime. Nenhuma credencial Docker compartilhada alterada.

J2: snapshot novo AES256/0600, roundtrip e cópia criptografada no frank-note2. API/web paradas às 09:41:52 -03, DB preservado e healthy. Baseline 14 tabelas, schema 1, quatro eventos/dois reconhecimentos; nenhuma transação de cliente ativa na conferência. Nenhuma alteração do agente.

J3: backup final adicional em destino exclusivo novo; checksum, GPG e catálogo pg_restore 17.11 legível. O destino isolado falhou no bootstrap antes de pg_restore: harness criou diretório `empty-init` modo 0700 (umask 077), inacessível ao UID 70. **Não houve restore efetivo deste backup.** Falha pertence ao harness operacional; não é demonstração de corrupção do arquivo ou defeito da imagem. A janela foi interrompida e não foi repetida; correção mínima de modo 0755 preparada apenas localmente. Container/volume/arquivos isolados e backups preservados.

J4/J5/J6/J7 não executados: zero roles novas/envs/deploys, nenhum smoke pós-deploy ou aceite por 10 min. Read-only final: 14 contagens iguais à baseline, eventos/ACKs iguais por conteúdo, volume e IDs originais, configuração Coolify ainda RC1/main/Compose antigo, auto-deploy desligado e fila de deploy vazia. API/web continuam paradas por determinação do procedimento seguro; não reiniciadas imagens vulneráveis. Kuma 20 DOWN/503, Kuma 21 UP/backup verified; configuração dos monitores inalterada. Entrega humana anterior não equivale a confirmação de novo alerta desta janela.

Não repetidas suites Go/Playwright/axe de aplicação: não houve mudança de código ou deploy; o CI anterior continua evidência histórica, não smoke desta janela. As verificações novas estão em [active-rc2-window](evidence/active-rc2-window/execution-summary.json), com hashes de artefatos, estado operacional, falha e limitações. O manifest conserva active_homologation_promoted=false e production_approved=false. [Plano de retomada](ACTIVE_HOMOLOGATION_PROMOTION.md#11-execução-autorizada-e-decisão-operacional--01112026) aguarda revisão e nova autorização; não iniciar automaticamente.


## Repetição limitada de J3 — interrompida

Confirmação em leitura do banco ativo e dos containers antes/depois: 14 contagens, schema 1, quatro eventos e dois reconhecimentos preservados; API/web paradas, DB saudável. Causa anterior confirmada no diretório vazio modo 0700 e log de permissão negada. SHA-256 e sidecar do backup final conferidos.

O harness desta repetição falhou com SyntaxError antes da criação do destino: substituição de marcador incidiu em `POSTGRES_PASSWORD`. Não houve decriptação, pg_restore ou novo teste de acesso UID 70. O código local foi corrigido e compilado com valores fictícios, sem repetir o restore após a interrupção. [Logs sanitizados](evidence/active-rc2-window/j3-retest/sanitized-log.json); [resultado](evidence/active-rc2-window/j3-retest/summary.json). J3 continua pendente; J4–J8 e deploy não executados.


## J3 — restore isolado efetivo aprovado

Checksum do backup final e sidecar conferidos. Em recursos novos com rede interna, sem portas e sem volume ativo, PostgreSQL endurecido iniciou e passou `pg_isready`. `empty-init` modo 0755 e pais visíveis acessíveis ao UID 70; credencial em arquivo 0600, diretório 0700. Descriptografia por pipe e `pg_restore --exit-on-error` retornaram 0 em 3,479 s; sem dump plaintext persistido. Schema 1, 14 contagens e registros originais de quatro eventos/dois reconhecimentos coincidem. Banco ativo verificado antes e depois em leitura; containers ativos sem mudanças. [Recursos e logs sanitizados](evidence/active-rc2-window/j3-authorized-restore/result.json). Container, rede e volume isolados preservados.

J3 PASS para o backup ensaiado; J4–J8 e deploy não executados. Homologação continua parada; produção não autorizada. Antes de promoção futura, reconferir estado e frescor e obter autorização específica.


## Nova janela J4–J8 — interrompida em J5

Prechecks passaram: restore J3 corresponde à baseline atual, 14 contagens e registros originais conferidos, backup/snapshot/chave acessíveis, cache/rede/volume/capacidade OK. [Verificação 41309355528](https://github.com/franklinlem/configsentinel/actions/runs/41309355528) passou em assinaturas, SBOM, provenance, scans e pull de cinco digests no SHA aprovado.

J4 aplicou roles/grants transacionalmente; runtime TCP e dez negativas 42501 passaram, sem alteração das 14 contagens e eventos/ACKs. J5 parou ao receber resposta não interpretável como JSON. A causa ainda não está estabelecida; a saída original não foi preservada e o teste de sintaxe com dados fictícios não reproduziu a falha. Consulta read-only confirmou Coolify no commit/Compose RC1 e variáveis originais, sem deploy concorrente ou solicitado. Banco healthy, API/web paradas; roles J4 persistem. J6/J7, smokes e backup pós-RC2 não executados. Kuma 20 DOWN/503 e 21 UP. [Resumo](evidence/active-rc2-resume/summary.json). Produção NO-GO.


## Diagnóstico isolado de J5

Protocolo novo: oito testes cobrindo JSON válido, vazio/truncado, texto adicional, UTF-8 inválido, limite, timeout, saída de erro, SSH 255 ambíguo, stderr inesperado, confidencialidade do stdin/diagnósticos e recusa de campos extras. Suite operacional: 18 testes, 16 PASS e dois PostgreSQL pulados por ausência de container de integração.

Modelos instalados do Coolify com SQLite em memória e valores fictícios: persistência criptografada das sete variáveis, rollback integral após falha, idempotência, digest errado rejeitado e serializer/Compose conferidos. Valor sintético com cifrão foi conferido também dentro de container isolado sem rede. Commit/Compose/digests/redes/volume fixados verificados. Estado ativo consultado somente em leitura: roles J4, dados e containers preservados. [Resultados](evidence/j5-isolated/probe.json).

Causa de fundo da resposta não JSON anterior permanece desconhecida: saída não foi retida. O helper corrigido é aprovado para tentativa controlada com nova autorização; transporte, banco real de metadados e deploy completo não foram exercitados como alteração ativa.


## Tentativa única de J5 — FAIL

Gates novos passaram: SHA/hash dos helpers, metadata/roles/grants, 14 contagens e eventos/ACKs, backup/restore/snapshot, rede/volume/capacidade e Compose privado. [Verificação 41311042013](https://github.com/franklinlem/configsentinel/actions/runs/41311042013) passou em assinaturas, SBOM, provenance, scans e cache.

A única chamada ao helper retornou `internal_error` (código 2, stdout 68 bytes, stderr 0); não houve retry e a causa específica não é conhecida. Comparação independente com snapshot: metadados e envs originais, nenhuma persistência parcial observada; banco inalterado, API/web paradas e deploys em fila zero. As sete variáveis não foram persistidas e não há renderização pós-persistência. J6/J7/deploy não executados. [Evidências](evidence/j5-active-attempt/summary.json).


## Diagnóstico J5: buffer e erros mascarados

Medição do processo PHP instalado: buffer inexistente inicialmente, nível 1/tamanho 0 após abertura e após bootstrap. Clone isolado com mesma imagem Coolify e PostgreSQL 15 sintético: entrypoint anterior passou e foi idempotente. Com ruído injetado, `internal_error` e rollback integral foram reproduzidos; warning e exceção SQL sintética também podiam ser mascarados como `internal_error`. Isso não prova a origem do evento ativo; o esquema sintético cobre apenas tabelas e colunas necessárias.

Protocolo v2 registra fase/tipo por allowlist, código e tamanhos, sem conteúdo sensível; categorias de buffer, warning e banco verificadas em isolamento. Entry point v2, idempotência e falha de banco sintética passaram em PostgreSQL; serializer/SQLite e Compose passaram. Suite operacional: 21 testes, 19 PASS e 2 ignorados por ausência de container J4. Protocolos rejeitam saídas inválidas e o envelope v1. Recurso, envs, dados, roles e serviços ativos conferidos em leitura e preservados. [Evidências](evidence/j5-diagnostic/diagnostic.json). Nova tentativa ativa NO-GO até revisão da causa e dos limites; não houve J5 ativo/deploy.

## J5 — Fase 1 sintética, 02/11/2026

[Relatório](J5_SYNTHETIC_PHASE1.md) e [resultado sanitizado](evidence/j5-synthetic-phase1/result.json): **14/14 cenários PostgreSQL PASS**, **11/11 testes de protocolo PASS** e oracle SQLite original aprovado. Exercitados sucesso/idempotência, rollback após escrita, PK, lock timeout com segunda conexão, fila, drift, warning, buffers e resposta truncada simulada após commit. Nenhuma repetição automática do helper; nenhuma operação ativa. A matriz PostgreSQL chama o helper diretamente, o protocolo tem testes locais próprios e o oracle roda separado; isso não equivale a deploy nem a execução completa do job Coolify.

Isolamento anterior às fixtures: 228 tentativas negativas ao host/serviços sem rota, banco sintético alcançável, DNS externo bloqueado, nenhuma porta ou volume ativo, rootfs read-only e ausência de rota padrão nos dois containers. Imagens Coolify 4.5.3 e PostgreSQL 15 aprovadas, PHP 8.4.27, PostgreSQL 15.19 e Laravel 12.70.1. Helpers operacionais intactos. Quatro tentativas do harness preservadas, sendo as três primeiras falhas corrigidas na transferência e no bootstrap do clone; a quarta passou. Recursos isolados permanecem em execução; limpeza não autorizada.

A causa do J5 ativo não foi identificada. Schema e valores são sintéticos; nenhum banco ativo, env real ou credencial real foi consultado. Homologação ativa não revalidada. Fase 2 depende de autorização específica e produção continua NO-GO.

## Recuperação da homologação — 03/11/2026

**PASS funcional:** site/readiness 200; login 200; eventos e organizações autenticados 200; eventos anônimos 401; logout 200 e sessão invalidada. API e web RC2 e PostgreSQL original healthy; mesmo container e volume do banco; schema 1 e registros originais de quatro eventos e dois reconhecimentos preservados. Backup periódico recente com checksum íntegro. [Evidências](evidence/recovery-20261103/smoke.json).

**J5 corrigido:** SQLSTATE 22001 reproduzido com rollback devido a comando de 482 caracteres em `varchar(255)`. Comando de 255 caracteres usando três IDs SHA-256 completos passou em transação revertida, aplicação e verificação independente; sete variáveis, commit e Compose confirmados. Oracle SQLite sintético: sete verificações PASS. [Detalhes](RECOVERY_2026-11-03.md). O deploy de recuperação foi manual por Compose, sem recriar o banco; job Coolify e fallback ausente permanecem pendentes para futura janela. Produção continua NO-GO.

## PostgreSQL RC2 e fallback — 03/11/2026

PASS: cinco digests assinados/verificados e cacheados; backup criptografado e restore isolado correspondentes à baseline; PostgreSQL 17.11 endurecido no volume original; API/web preservadas; 14 contagens, eventos e reconhecimentos íntegros; site, readiness, login, eventos e logout; backup criptografado posterior com checksum. Kuma 20 e 21 UP na última consulta, com amostra de 20 posterior à troca. [Evidências](HOMOLOGATION_RC2_COMPLETION.md). O deploy pelo Coolify não foi executado porque seu job conectaria o proxy à rede dedicada, ação anteriormente proibida. Produção permanece NO-GO.

## Job Coolify e caminhos relativos — 03/11/2026

O único job manual autorizado terminou FAIL ao procurar `.env` do host dentro do container de deploy. Serviço permaneceu saudável e registros originais preservados. Foi preparada correção com `--env-file .env` e `-f ./deploy/compose.active-homologation.yml`: validador e injetor instalados e render Compose sintético PASS; PostgreSQL sintético 16/16, SQLite 8/8 e protocolo 11/11 PASS. O comando corrigido ainda não foi aplicado ao ativo e nenhum segundo job foi solicitado. [Relatório](HOMOLOGATION_RC2_COMPLETION.md). Produção continua NO-GO.

## Atualização operacional — 03/11/2026: deploy manual RC2 concluído

A correção do caminho relativo do Compose foi aplicada ao recurso de homologação autorizado e verificada por leitura independente, incluindo sete variáveis protegidas, imagens, redes e volume. Uma única tentativa manual do Coolify (`d872aded-991c-4568-a2da-a13335d6282e`) terminou em `finished`, sem rebuild nem repetição automática. API, web e PostgreSQL ficaram saudáveis; a migração terminou com código zero. A preparação usa o commit `36baf66f4656f86d157cd070202323db9465c5f4` e as imagens RC2 correspondem ao código `ea868efaa3e3b364d012981e597c8faf6bc30651`.

Antes da mudança, um backup criptografado novo teve checksum conferido e restore isolado com `pg_restore --exit-on-error` em 3,647 s; schema 1 e as 14 contagens corresponderam à baseline. Após o deploy, site e readiness retornaram 200; login, eventos autenticados, organizações e logout passaram, com 401 antes do login e após o logout. Os quatro eventos e dois reconhecimentos originais foram preservados. Evidências sanitizadas: [backup](evidence/rc2-retry-20261103/backup.json), [restore](evidence/rc2-retry-20261103/restore.json), [configuração](evidence/rc2-retry-20261103/independent.json), [job](evidence/rc2-retry-20261103/deployment-result.json) e [smoke](evidence/rc2-retry-20261103/smoke.json).

A homologação está operacional. Este smoke não substitui a revisão completa de RBAC, CSRF, heartbeat, auditoria, alertas Kuma e observação prolongada; nem foi realizado novo ensaio de rollback após este deploy. O agente não foi atualizado. Produção permanece **NO-GO**, sem autorização de implantação. Os recursos do restore isolado foram preservados.

## Revisão de 04/11/2026 UTC

Integração PostgreSQL sintética com race, Playwright/axe na homologação, npm audit e build web passaram; monitores 20/21 UP em histórico recente. Correção local para indisponibilidade inicial da sessão testada; imagem nova construída localmente e ainda não implantada. Detalhes e limites em [revisão](REVIEW_2026-11-04.md). Produção NO-GO.

## Atualização web e alertas — 04/11/2026 UTC

Web corrigida implantada em homologação e validada; correção da API para alertas simultâneos testada em PostgreSQL isolado e ainda pendente de promoção. Detalhes e evidências em [revisão](REVIEW_2026-11-04.md). Produção permanece NO-GO.

## API de alertas — 04/11/2026 UTC

API corrigida promovida à homologação por digest; smoke repetido passou após primeira tentativa com asserção HTTP não identificada. Backup/restore e integridade dos dados passaram. Detalhes em [revisão](REVIEW_2026-11-04.md). Produção NO-GO.

## Capacidade e migration — 04/11/2026

Central, interface e agente sintético promovidos com schema 2; heartbeat informa capacidade e alerta usa 80%. Backup posterior restaurado e testes relevantes passaram. Monitor externo de agente preparado, porém ainda não ativado. Ver [detalhes](CAPACITY_AND_ALERT_DELIVERY.md). Produção NO-GO.

## Ingestão e promoção em homologação — 04/11/2026

A API otimizada foi implantada por digest no recurso de homologação, sem alteração de schema ou volume. O job terminou `finished`, os três serviços ficaram saudáveis e o smoke passou. Backup criptografado foi restaurado em banco isolado; as 14 contagens e identidades dos quatro eventos e dois reconhecimentos conferiram. A reversão da configuração para a API anterior foi testada somente em fixtures sintéticas. Em três medições alternadas locais a mediana dos p95 caiu de 260,48 para 158,72 ms; esse resultado não comprova o desempenho em produção. [Detalhes e evidências](INGESTION_OPTIMIZATION.md).

O monitor externo de alertas de agente está implementado e testado com destino simulado, porém ainda não foi ativado no Kuma; a entrega real de alertas de agente permanece pendente. Produção continua **NO-GO**.

## Monitor de agentes — 05/11/2026

Monitor Kuma 22 e timer no frank-note2 ativados para o agente sintético selecionado, com conta viewer dedicada. Teste controlado de DOWN/UP registrado e entrega de ambos os avisos confirmada por Franklin; o teste de transição foi enviado ao monitor, sem simular falhas reais no agente. Ver [supervisão](CAPACITY_AND_ALERT_DELIVERY.md) e [evidências](evidence/agent-monitor-20261105/). Produção continua NO-GO.

## Preparação de produção — 05/11/2026

[Lista atual de pendências](PRODUCTION_TODO.md). Correções locais: a manutenção volta a tentar após falha e preserva eventos e reconhecimentos até definição de política; sessões vencidas continuam sendo removidas. O agente abre o token sem links e valida diretório, arquivo de fila e lock antes de usá-los. A exigência de diretório previamente provisionado corresponde ao `StateDirectory` do serviço e ao diretório do piloto; ela restringe implantações personalizadas que usavam criação automática. A proteção não trata comprometimento do próprio UID ou ACLs que concedam escrita adicional.

Testes Go com detector de corridas passaram nos dois módulos; a API foi exercitada com PostgreSQL sintético, incluindo preservação de eventos antigos e limpeza de sessões. As correções ainda não estão implantadas. A versão ativa mantém a exclusão de eventos após 90 dias, com exclusão em cascata dos reconhecimentos. Produção permanece NO-GO.

## Preservação de eventos e agente — 05/11/2026

A API do commit `13a8c18dfab0fab81d149727d3081f64c1b5659e` foi promovida por digest ao recurso de homologação pelo job `10cb583e-a2c4-4988-b4cc-0c9e1781ca25`; mantém eventos e reconhecimentos e retoma a manutenção após falhas. O agente sintético recebeu o binário assinado, com fila e configuração preservadas. Backup criptografado restaurado em PostgreSQL isolado; contagens das tabelas exceto sessões e identidades de eventos/reconhecimentos preservadas. Sessões foram excluídas da comparação posterior por causa dos logins periódicos do monitor. Smoke e containers saudáveis. [Evidências](evidence/production-prep-promotion-20261105/).

O rollback para a API anterior restabelece a exclusão de eventos após 90 dias e dos reconhecimentos associados; antes de qualquer retorno, conferir idade dos registros e evitar perda de dados. O rollback da configuração foi ensaiado em bases sintéticas, não executado no recurso ativo. Política de retenção, capacidade, ACLs e bloqueio de I/O seguem pendentes. Produção permanece NO-GO.

## Heartbeat e horário de coleta — correção local em 05/11/2026

O agente passa a executar heartbeat em rotina independente da coleta e do flush, mantendo horário da última coleta separadamente. `sent_at` opcional permite à API calcular diferença de relógio sem confundir coleta atrasada com relógio incorreto; no 422 de central antiga, o agente retira primeiro `sent_at` e só remove `queue_capacity` se a central ainda o rejeitar. Agentes antigos continuam usando a interpretação legada do horário observado. Testes com detector de corridas e PostgreSQL sintético passaram, inclusive teste de compatibilidade e de coleta atrasada com relógio correto. A mudança ainda não foi implantada; faltam imagens verificadas e ensaio no piloto com indisponibilidade de I/O simulada.
