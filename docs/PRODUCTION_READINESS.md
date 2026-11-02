# ConfigSentinel — candidato corrigido e preparação de release

**02/11/2026 — Fase 1 do clone J5: PASS exclusivamente sintético.** Quatorze cenários PostgreSQL, 11 testes de protocolo e oracle SQLite original passaram. Isolamento de rede comprovado no recorte ensaiado; nenhum banco/credencial real foi consultado e não houve deploy. Helper operacional intacto; recursos novos preservados. A causa histórica continua desconhecida, o estado ativo não foi revalidado e **J5 ativo/produção permanecem NO-GO**. [Relatório](J5_SYNTHETIC_PHASE1.md), [evidências](evidence/j5-synthetic-phase1/result.json). Fase 2 e limpeza exigem autorização específica.


**Atualização J3:** repetição isolada interrompida antes de iniciar o banco de teste: erro sintático no harness ao substituir `POSTGRES_PASSWORD`. Backup final com SHA-256 conferido; nesta tentativa não houve decriptação nem restore. Banco ativo verificado antes/depois sem alteração, API/web permanecem paradas. Correção de marcador preparada e compilada apenas com valor fictício; restore continua pendente e homologação/produção permanecem NO-GO. [Evidência](evidence/active-rc2-window/j3-retest/summary.json).


**Resultado atual de J3:** PASS em restore isolado do backup final, com checksum, decriptação em streaming e `pg_restore --exit-on-error` bem-sucedidos. Schema 1, 14 contagens, quatro eventos e dois reconhecimentos coincidem com a baseline; banco ativo e containers preservados. Duração do streaming/restore: 3,479 s. O resultado pertence ao backup e à baseline testados; a promoção exige nova autorização e reconferência de frescor. [Evidência](evidence/active-rc2-window/j3-authorized-restore/result.json). RC2 não implantado, API/web paradas e produção NO-GO.


**Retomada posterior interrompida em J5 — NO-GO.** API/web continuam paradas; PostgreSQL ativo saudável. Prechecks e J4 passaram: três roles restritas aplicadas, dez negações de privilégio verificadas e dados originais preservados. O helper J5 retornou saída não interpretável; inspeção confirma configuração e variáveis originais do Coolify, sem deploy em fila. Causa ainda não comprovada. J6/J7 e deploy não ocorreram. [Evidência](evidence/active-rc2-resume/summary.json). Produção continua não autorizada.


**Revisão isolada do helper J5:** aprovado para nova tentativa controlada após autorização e gates; o recurso ativo não foi alterado. Causa específica da resposta anterior permanece desconhecida porque seu conteúdo não foi preservado. A perda de diagnóstico foi corrigida com envelope e categorias sanitizadas; testes em Coolify instalado/SQLite em memória passaram para rollback, idempotência e criptografia. O ensaio não equivale a execução real do job Coolify. Homologação continua indisponível e produção NO-GO. [Evidência](evidence/j5-isolated/probe.json).


**Tentativa específica de J5: FAIL.** O helper retornou `internal_error` na única chamada; diagnóstico específico ainda desconhecido. Leitura independente mostrou metadados e envs iguais ao snapshot, nenhuma persistência parcial, banco íntegro, roles J4 preservadas e nenhum deploy. API/web continuam paradas; homologação e produção NO-GO. [Evidência](evidence/j5-active-attempt/summary.json).


**Diagnóstico posterior de J5: NO-GO para nova tentativa ativa.** Buffer não estava preenchido no bootstrap observado; ruído sintético causou `internal_error` e rollback em clone PostgreSQL 15, mas a origem real permanece desconhecida. O helper ganhou fase/tipo sanitizados no protocolo v2, sem afirmar que a falha foi corrigida. [Evidência](evidence/j5-diagnostic/diagnostic.json). Recurso ativo permaneceu sem alterações.

## Estado operacional — janela autorizada de 01/11/2026

**NO-GO para aceite da homologação e para produção. API/web estão paradas desde 09:41:52 -03; banco RC1 permanece healthy e íntegro. RC2 não foi implantado.** Janela interrompida em J3 conforme o procedimento aprovado, antes da aplicação de roles/configuração/deploy.

Nova verificação [41307377319](https://github.com/franklinlem/configsentinel/actions/runs/41307377319), fixada no SHA de preparação `36baf66f4656f86d157cd070202323db9465c5f4`: assinaturas, provenance, SBOMs e scans dos cinco digests passaram; API/fallback somente o UNKNOWN já analisado, zero HIGH/CRITICAL. Quatro imagens centrais no cache, versões e configuração protegida conferidas, snapshot criptografado renovado/offsite. Código das imagens preservado em `ea868efaa3e3b364d012981e597c8faf6bc30651`.

**Pendência P1 operacional:** corrigir permissões do diretório vazio de bootstrap do harness isolado e executar restore final real em destino novo. O umask 077 do harness gerou modo 0700, ilegível pelo UID 70 PostgreSQL; o banco isolado encerrou antes do restore. Correção0755 preparada localmente, sem reteste remoto ou nova tentativa de promoção. O banco ativo não foi substituído nem atualizado. A parada é aplicação do ponto seguro previsto; retomada requer nova autorização após revisão.

Backup final: checksum, decriptação e catálogo pg_restore passaram, **restore final não executado**. Dados ativos: 14 contagens idênticas à baseline, schema 1, quatro eventos e dois reconhecimentos integralmente preservados. Nenhuma role nova, nova env ou job de deploy; última implantação permanece RC1 `5819b7f`. Kuma 20 DOWN/503 esperado após drenagem, Kuma 21 UP/backup verified. Smokes pós-RC2, observação de 10 min e backup pós-deploy não se aplicam a uma promoção não realizada.

Fallback limpo assinado/escaneado permanece preparado e não foi acionado. Não reiniciar web/DB RC1 vulneráveis nem usar rollback genérico do Coolify. Agente ativo/fila/allowlist preservados, sem atualização; correção do heartbeat RC2 continua somente no candidato. Achados históricos do RC1 permanecem no banco ainda em execução. Produção não criada nem autorizada.

[Evidências da janela](evidence/active-rc2-window/execution-summary.json), [estado final e dados](evidence/active-rc2-window/interrupted-final-state.json), [procedimento/retomada](ACTIVE_HOMOLOGATION_PROMOTION.md#11-execução-autorizada-e-decisão-operacional--01112026).

## Revisão anterior do candidato — histórico anterior à janela


Atualizado em **31/10/2026**. Branch: `fix/production-blockers`, baseada na revisão `0524bee`. Candidato de revisão: **v0.1.0-rc.2-review**, imagens construídas do commit `ea868efaa3e3b364d012981e597c8faf6bc30651`. Não foi criada release pública nem tag de promoção.

**Decisão: NO-GO para produção.** Os bloqueadores de código/imagem P0/P1 foram corrigidos e validados no candidato. A promoção de qualquer candidato aguarda revisão de Franklin. A implantação real por digest no recurso Coolify, a credencial permanente de pull somente leitura e o aceite operacional do novo candidato permanecem gates manuais. Os testes abaixo não autorizam produção.

## Escopo e ponto de recuperação

| Ambiente/componente | Situação confirmada |
| --- | --- |
| Homologação ativa no Coolify | RC1 preservado; mesmos IDs de imagens, dados, volume e rotas. Continua sendo o ponto de recuperação, com os achados históricos do RC1 |
| Candidato | Registry privado, quatro imagens por digest, assinadas e escaneadas; validado localmente e em cópia isolada na VPS de homologação |
| Ensaio remoto | Rede interna e volume próprios; sem portas públicas, routers ou ligação à rede Coolify; todos os seus containers parados ao concluir, volume preservado |
| Agente piloto | Instalação e fila existentes preservadas; somente fixture sintética, sem ampliação de allowlist ou permissões. Binário corrigido ainda não promovido ao piloto |
| Backup/monitoramento | Correções instaladas nos serviços exclusivos ConfigSentinel do frank-note2; monitor Kuma 21 criado, monitor HTTP 20 preservado |
| Produção | Não criada, não implantada e sem autorização |

O [ponto de recuperação](evidence/remediation/recovery-point.json) registra commit/IDs do RC1, arquivos de imagem locais protegidos 0600 com SHA-256 e tags locais de recuperação na VPS. Não houve reinício da central ativa. [Revisão anterior completa](evidence/production-readiness-rc1.md).

Nenhum serviço de outro projeto, Traefik, firewall ou DNS foi alterado. As portas de teste locais são loopback; o ensaio remoto não publica portas. As únicas mudanças operacionais fora da cópia foram backup/monitor ConfigSentinel, tags de recuperação e acesso SSH restrito a baixar suas imagens. Não se montou volume ativo no ensaio.

## P0 — imagens corrigidas

A web passou à base **nginx-unprivileged stable-alpine-slim**, fixada por digest. Pacotes musl/musl-utils `1.2.6-r3` e zlib `1.3.2-r1` são explicitamente fixados durante o build. Isso também encerrou os achados MEDIUM/UNKNOWN encontrados no primeiro build reduzido. O usuário runtime permanece 101, com a mesma configuração nginx e a mesma SPA.

O PostgreSQL permanece **17.11**, na base oficial 17-alpine mais recente disponível na inspeção, fixada por digest. O binário Go obsoleto `gosu` foi removido; os dois entrypoints usam **su-exec 0.3-r0** para baixar ao UID postgres 70. Inicialização, migração, restore e reabertura do volume foram exercitados. Não houve pg_upgrade nem alteração do formato de dados. A atualização foi ensaiada somente após verificar backup e plano de compatibilidade, em volume próprio.

| Imagem final linux/amd64 | CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN |
| --- | ---: | ---: | ---: | ---: | ---: |
| Web | 0 | 0 | 0 | 0 | 0 |
| PostgreSQL | 0 | 0 | 0 | 0 | 0 |
| API | 0 | 0 | 0 | 0 | 1 |
| Agente | 0 | 0 | 0 | 0 | 0 |

Trivy **0.76.1**, executado contra os **digests publicados**, com gate HIGH/CRITICAL que falha o job. Não foi usado ignore global, `ignore-unfixed` ou supressão de CVEs. [Resultados, versões, digests e achados](evidence/remediation/results.json). Scans refletem a base do scanner na execução, não garantem ausência de futuros advisories.

O único achado restante é **GO-2026-5932**, módulo `golang.org/x/crypto v0.58.0`, pacote openpgp sem manutenção e sem fix indicado. A API importa argon2; `govulncheck` detecta zero vulnerabilidades alcançáveis e o advisory de módulo não chamado. É pendência P3 acompanhada, sem supressão. O GPG externo do backup não é esse pacote. [Advisory oficial Go](https://pkg.go.dev/vuln/GO-2026-5932).

SBOMs runtime CycloneDX: [API](evidence/remediation/api-sbom.cdx.json), [web](evidence/remediation/web-sbom.cdx.json), [banco](evidence/remediation/db-sbom.cdx.json) e [agente](evidence/remediation/agent-sbom.cdx.json). Checksums no manifest/inventário.

## P1 — roles separadas e runtime restrito

| Role | Acesso |
| --- | --- |
| `configsentinel_owner` | NOLOGIN; proprietária do schema e das tabelas da aplicação |
| `configsentinel_migrator` | LOGIN, NOINHERIT, sem SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS; deve executar SET ROLE owner no comando one-shot `--migrate` |
| `configsentinel_runtime` | LOGIN, NOINHERIT, sem privilégios administrativos e sem membership de owner/migrator; somente grants explícitos necessários à operação |

O processo HTTP não executa migrations ou bootstrap e não recebe ADMIN_PASSWORD. Recusa credencial administrativa e schema diferente de 1. O comando de migração exige a identidade migrator; bootstrap e grants ocorrem nessa etapa separada. O administrador inicial do PostgreSQL permanece somente para provisionamento/recuperação, fora do processo HTTP.

Testes reais de permissões passaram: leitura, inclusão de auditoria e operações da jornada permitidas; CREATE TABLE/SCHEMA, ALTER TABLE, TRUNCATE, UPDATE/DELETE da auditoria, alteração de schema_migrations, SET ROLE owner/migrator e elevação a SUPERUSER negados com SQLSTATE 42501. O migrator cria DDL como owner; o runtime passa pela jornada HTTP/E2E com autenticação PostgreSQL e sem privilégio de DDL.

[Provisionamento](../db/roles/provision.sql) adota a propriedade das tabelas existentes sem substituir dados. [Grants](../db/roles/runtime-grants.sql) mantêm auditoria SELECT/INSERT e negam sua mutação pelo runtime. Novas tabelas exigem grants deliberados. Credenciais continuam sendo segredos de operação Docker/Coolify; o operador desse ambiente é um domínio de confiança.

**Ativação ainda pendente na central ativa:** init scripts não rodam novamente em volume já inicializado. Antes da futura promoção, provisionar roles com o administrador exclusivo desse banco e variáveis protegidas; depois executar `--migrate` com migrator e trocar a API para runtime. O ensaio adotou exatamente as tabelas restauradas e conferiu compatibilidade. Não executar o Compose histórico do RC1 como procedimento automático de atualização.

## P1 — heartbeat independente da fila

O flush possui worker e relógio de retry próprios. O ciclo de coleta/heartbeat continua durante backoff e requisição de ingestão bloqueada. Falha do flush não apaga eventos. Cancelamento encerra o worker antes de fechar a fila.

O horário da última coleta persistida fica em metadata SQLite; filas anteriores usam o timestamp do último evento como fallback. Isso permite heartbeat válido após reinício com fila cheia, sem marcar uma coleta não persistida como recente. A identidade, sequência, UUID e conteúdo dos eventos existentes são preservados; binários anteriores ignoram a nova chave de metadata.

Passaram: **409/422/503**, ingestão esperando heartbeat concorrente, fila limitada a um evento e saturada, reconexão, ACK perdido/replay com mesmo UUID, coleta da mudança pendente após liberar espaço e cancelamento com evento ainda na fila. O protocolo e as permissões do agente não foram ampliados.

Persistem os limites do MVP: fila cheia pode deixar de capturar mudanças intermediárias ainda não enfileiradas; um lote permanentemente inválido exige procedimento de operação, sem descarte automático. A central ainda possui os problemas P2 de prioridade única e limiar fixo dos alertas.

## P1 — backup, integridade e alertas

Instalado o backup corrigido no frank-note2:

- Lock exclusivo não bloqueante evita execuções simultâneas.
- Chave existente obrigatória, regular, do próprio usuário e sem leitura por grupo/outros; ausência falha fechada. Não gera chave substituta automaticamente.
- Deadline total de **300 s** para SSH/GPG, opções de conexão/keepalive e término dos subprocessos em timeout; serviço limitado a 360 s.
- Arquivo parcial e metadata publicados atomicamente; falhas preservam o último sucesso. Sucessos do mesmo dia usam timestamp e não sobrescrevem o recovery point anterior.
- Política preservada: sete datas diárias e quatro semanas; pontos do mesmo dia são mantidos. Os dois backups existentes deste dia continuam presentes e com checksum válido.

O novo monitor independente executa a cada **5 min**: verifica resultado systemd, idade máxima **26 h**, checksum e decriptação GPG com plaintext descartado, sem gravar dump aberto. O Kuma monitora ausência de push com intervalo de 600 s. Usa a porta **loopback já existente** do Kuma; o endpoint público retornou 403 e não foi alterado. O serviço tem timeout próprio de 150 s.

Monitor **21**, `ConfigSentinel · Backup criptografado`, associado somente ao canal existente **HermesFranklem**. Ensaios com diretórios sintéticos produziram DOWN para atraso de 27 h e checksum corrompido, seguidos de UP com o backup real íntegro. O teste do provedor Telegram foi aceito; **recebimento humano posteriormente confirmado por Franklin**, com captura dos alertas DOWN/UP e da mensagem de teste ([evidência sanitizada](evidence/promotion/alert-receipt-confirmation.json)). A ausência de push está configurada, sem ensaio cronometrado de 10 min nesta rodada. O monitor HTTP 20 permanece independente.

A chave de recuperação foi conferida em outro host, fora do repositório, em diretório privado e arquivo 0600. Nenhum segredo foi incluído nas evidências. Não é comprovação de um cofre externo gerenciado. [Evidências sanitizadas](evidence/remediation/results.json).

Restore final em streaming do backup criptografado mais recente: **schema 1, quatro eventos, dois reconhecimentos**. O snapshot anterior, preservado como recuperação, tinha um reconhecimento; não confundir os dois momentos. Backup cobre o banco ConfigSentinel, sem config/token/fila dos agentes ou segredos Coolify. RPO/RTO completo não foi contratado nem cronometrado.

## Build, registry privado e promoção por digest

[Workflow de imagens](https://github.com/franklinlem/configsentinel/actions/runs/41253986413) passou nos quatro componentes e no cache restrito da VPS. Constrói uma vez por commit, plataforma linux/amd64, gera BuildKit SBOM/provenance e SBOM runtime, escaneia o digest e verifica que os pacotes GHCR são privados. Não executa deploy.

Cosign **3.1.4** assina digests, SBOMs e provenance do workflow. A verificação usa [chave pública fixada](../deploy/release-signing.pub), conferindo vínculo digest/commit. Os quatro payloads SBOM assinados também foram comparados com os arquivos e checksums registrados: [conferência](evidence/remediation/attestation-content-checks.json). Provas de assinatura/provenance estão no mesmo diretório de evidências.

A política privada usa chave autogerenciada e não publica em Rekor: assinatura criptográfica é verificada com a chave fixada, enquanto a verificação de transparência é explicitamente dispensada. Isso não fornece identidade OIDC pública ou transparência independente; proteger/rotacionar a chave e os secrets de CI faz parte da operação. [Modelo documentado pelo Sigstore](https://docs.sigstore.dev/cosign/signing/signing_with_containers/).

A credencial GHCR do workflow é efêmera. Uma chave SSH dedicada possui forced-command exclusivo para baixar somente imagens ConfigSentinel por digest, sem shell/forwarding/deploy. O login Docker temporário é apagado ao concluir. As quatro imagens foram baixadas por digest na VPS, sem substituir containers ativos. O [GHCR suporta autenticação do workflow com GITHUB_TOKEN](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

[Manifest do candidato](../deploy/release-manifest.candidate.json): digests reais, SBOM SHA-256, scans, assinaturas, commit e referências de CI/rollback. `homologation_passed=true` refere-se **à cópia isolada**, com o modo explicitamente registrado. `active_homologation_promoted=false`, `candidate_review_approved=false` e `production_approved=false`.

O [Compose por digest](../deploy/compose.digest.example.yml) está preparado, com migrator one-shot, runtime separado e sem builds. É configuração para o host de homologação existente, sujeita à revisão, não template aprovado de produção. O validador do manifest verifica formato/declarações e retorna **NO-GO: explicit production approval required**; a autenticidade dos artefatos é conferida separadamente pelas assinaturas, não por booleanos.

Antes da promoção no recurso Coolify: revisar o manifest, fornecer credencial de pull somente leitura, conferir o mapeamento exclusivo de volumes/segredos, aplicar o procedimento de roles existente e validar o Compose no recurso. Nenhum auto-deploy, webhook de promoção ou recurso de produção foi habilitado.

## Rollback ensaiado e compatibilidade de migrations

[Evidência do ensaio na VPS de homologação](evidence/remediation/homologation-rollback.json), com rede/volume novos e limites de CPU/memória:

| Etapa | Schema | Eventos | Reconhecimentos | PostgreSQL | Readiness / sem sessão |
| --- | ---: | ---: | ---: | --- | --- |
| Candidato por digest | 1 | 4 | 2 | 17.11 | 200 / 401 |
| Rollback API/web para imagens RC1 | 1 | 4 | 2 | 17.11 | 200 / 401 |
| Rollback também da imagem PostgreSQL | 1 | 4 | 2 | 17.11 | 200 / 401 |
| Retorno aos mesmos digests candidatos | 1 | 4 | 2 | 17.11 | 200 / 401 |

Não houve nova migration de dados/schema: a alteração é de propriedade/grants. Tanto o binário anterior quanto o novo operaram sobre schema 1 e **credencial runtime restrita**. O rollback preserva essas credenciais/grants; não reintroduzir a conexão administrativa do Compose antigo. As imagens RC1 com achados são recovery point de homologação, sem aprovação para uso em produção.

Gatilhos de rollback: readiness sem estabilizar, falha de migração, 5xx/latência acima do limite acordado, perda/replay incorreto, autorização cruzada ou exposição de segredo. Usar digests previamente aprovados para o mesmo ambiente e preservar volume, identidade, fila e credenciais. Se a mudança de schema futura não for compatível com o binário anterior, bloquear rollback automático e planejar expand/contract.

Não há `down -v`, downgrade destrutivo ou restore sobre banco ativo neste procedimento. Restore deve primeiro validar em banco separado; substituição de banco ativo ou perda de dados exige aprovação específica. Na primeira produção, sem versão anterior aprovada, o plano é desativar somente o novo recurso e preservar os dados. O ensaio Docker isolado não equivale a um deploy/rollback do recurso Coolify ativo.

## Testes e checklist final

| Verificação | Resultado |
| --- | --- |
| API `go test -count=1 -race ./...` | PASSOU, incluindo PostgreSQL real isolado, RBAC/tenants, sessões, CSRF, tokens, replay e ingestão |
| Agente `go test -count=1 -race ./...` | PASSOU, incluindo leituras seguras, symlinks concorrentes, fila, worker, heartbeat e recuperação |
| `go vet ./...` | PASSOU nos dois módulos |
| Integração de roles/operação | 6 testes passaram, sem skips na execução com banco selecionado |
| Playwright | 4 testes passaram no candidato local atualizado; CI web/E2E também passou |
| Axe e responsividade | 0 violações A/AA nas sete páginas; jornada e larguras 390/768/1280 exercitadas |
| Segurança de dependências | npm audit 0; Go zero alcançáveis, um advisory de módulo não usado pela API; Trivy na tabela acima |
| Build/contrato | Build web e OpenAPI com 24 paths passaram |
| Tokens/segredos | Nenhum token/cookie nos padrões examinados nas últimas 2 h dos logs; credenciais locais 0600; traces E2E desligados; Gitleaks final: zero vazamentos no histórico versionado |
| Backup/restore/alertas | Lock, ausência de chave, falha de transporte, timeout, atraso e corrupção testados; restore e rollback remoto passaram |
| CI completo | [41253986449](https://github.com/franklinlem/configsentinel/actions/runs/41253986449): API, agente, web e segredos verdes |

Não foram reescritos UI, protocolo, arquitetura, allowlist ou permissões do agente. O aceite visual humano é do RC1; revisão do candidato permanece pendente. Testes automáticos não são auditoria externa, certificação WCAG, fuzzing prolongado ou prova de ausência de vulnerabilidades.

## Pendências e decisão

| Severidade/gate | Situação |
| --- | --- |
| P0/P1 do candidato | Correções implementadas e ensaiadas conforme seções acima |
| Gate manual antes de promoção | Revisão de Franklin; aceite operacional do candidato e procedimento por digest no Coolify, com pull somente leitura. Central e piloto ativos ainda são RC1 |
| P2 — desempenho | Ingestão não foi otimizada nesta rodada: último benchmark local p95 **280,71–364,53 ms**, zero erros, 304 comandos SQL por lote de 100 eventos. Meta de 300 ms não comprovada; não apresentar como SLO de produção |
| P2 — alertas/observabilidade | Fila alta ainda mascara offline; limiar 8.000 não acompanha max_queue; clock skew pode confundir coleta atrasada; retenção encerra após erro; métricas não cobrem todas as falhas nem oferecem histograma p95 |
| P2 — agente | Prazo de I/O de filesystem, abertura segura de token/fila e limites contra comprometimento do próprio UID continuam conforme revisão anterior |
| P2 — UX/operação | `/me` 503 mostra login; recuperação de sessão/nova aba/CSRF, ações de viewer, offboarding e limites globais ainda precisam de melhoria; acessibilidade manual completa pendente |
| P2 — release/backup | Rotação da retenção por semanas e ausência de push por 10 min ainda sem ensaio prolongado; recepção humana dos testes confirmada; medir RPO/RTO completo; revisar pinning de ferramentas/actions do CI legado |
| P3 | Acompanhar GO-2026-5932 não alcançável e reavaliar nas atualizações |

**NO-GO para produção mantido.** O candidato está disponível para revisão com P0/P1 corrigidos, evidências e recuperação preservadas. A autorização recebida abrangeu correções e ensaio isolado; nenhuma promoção para tráfego ativo ou produção foi inferida.

## Prechecks da homologação ativa — 01/11/2026

[Procedimento atualizado](ACTIVE_HOMOLOGATION_PROMOTION.md) e [checklist G0–G6](evidence/promotion/precheck-gates.json): G1–G6 passaram no escopo isolado/leitura; **G0 (janela ativa) PENDENTE**. Esse resultado não autoriza deploy. Nenhuma flag de aprovação humana/produção foi ativada.

- Fallback compatível com RC1 publicado/assinado, API digest `cacace0b74ddb9bdef72109436035c59305e4c6bb02c063fe0788ce069cffc66`, zero HIGH/CRITICAL. Mantém web/DB endurecidos e migrator RC2: o binário RC1 não aceita `--migrate`. [Manifest](../deploy/release-manifest.fallback.json).
- [Workflow somente leitura](https://github.com/franklinlem/configsentinel/actions/runs/41259950111) reverificou cinco digests, assinaturas diretas/provenance/SBOM/scans e cache via SSH restrito, sem login Docker compartilhado. UNKNOWN GO-2026-5932 continua acompanhado nas duas APIs; sem supressões.
- [Ensaio isolado](evidence/promotion/isolated-promotion-rehearsal.json): RC2 → fallback → RC2, login/RBAC/CSRF/tenants, eventos/replay, heartbeat 202 e auditoria passaram; 14 contagens preservadas na adoção das roles e dez operações negadas ao runtime autenticado por TCP. Quatro eventos e dois reconhecimentos originais conferem também por identidade/conteúdo. Volumes preservados e serviços de teste parados.
- Snapshot de configuração exclusivo criptografado AES256/0600, roundtrip e cópia offsite conferidos. Backup novo em destino isolado restaurado; backup regular de 01/11 às 03:35 -03 também íntegro/decriptável. Backup final após drenagem continua obrigatório na janela.
- [Coolify 4.5.3](evidence/promotion/coolify-installed-path.json): métodos raw parser/validação/injeção/skip de pull exercitados com clone em memória e barreiras de escrita/SSH. Comando gerado executado só no Compose isolado. `>/dev/null` foi substituído por `--format '{{.Id}}'`, aceito no validator. **Job completo de deploy não foi executado.**
- Kuma 21 confirmado ativo/UP e associado ao HermesFranklem; entrega humana previamente confirmada. Lógica de ausência de push testada com código instalado/relógio isolado; **não houve pausa real de 10 min nem novo ensaio end-to-end dessa notificação**.

Esses limites estão expressos nos gates. Exigência adicional de job completo isolado ou notificação real por silêncio não deve ser tratada como concluída. Na janela, renovar scans/cache/snapshot/backup e testar a URL ativa. A [inspeção final](evidence/promotion/active-preservation-final.json) confirma RC1 healthy, mesmas instâncias/imagens e start desde 31/10, roles novas ausentes, piloto preservado e nenhum deploy. **NO-GO para iniciar mudanças ativas sem autorização específica; NO-GO para produção mantido.**

Reconferência de 01/11: [CI 41305147386](https://github.com/franklinlem/configsentinel/actions/runs/41305147386) verde em API/agente/web/segredos; [workflow manual read-only 41305428149](https://github.com/franklinlem/configsentinel/actions/runs/41305428149) reverificou os cinco digests e repopulou o cache. Um refresh intermediário falhou no segundo lote; causa exata não estabelecida. [Inspeção posterior](evidence/promotion/cache-inspection.json) confirmou quatro digests centrais presentes. Pendência operacional P2: cache não é durável; conferir/renovar imediatamente antes da parada e falhar fechado. Diagnóstico sanitizado do helper e quatro testes locais de não vazamento/isolamento passaram; nenhuma credencial compartilhada alterada.
