# ConfigSentinel — candidato corrigido e preparação de release

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

Monitor **21**, `ConfigSentinel · Backup criptografado`, associado somente ao canal existente **HermesFranklem**. Ensaios com diretórios sintéticos produziram DOWN para atraso de 27 h e checksum corrompido, seguidos de UP com o backup real íntegro. O teste do provedor Telegram foi aceito; **leitura/recebimento humano não foi confirmado**. A ausência de push está configurada, sem ensaio cronometrado de 10 min nesta rodada. O monitor HTTP 20 permanece independente.

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
| P2 — release/backup | Rotação da retenção por semanas e ausência de push por 10 min ainda sem ensaio prolongado; registrar recepção humana do alerta e medir RPO/RTO completo; revisar pinning de ferramentas/actions do CI legado |
| P3 | Acompanhar GO-2026-5932 não alcançável e reavaliar nas atualizações |

**NO-GO para produção mantido.** O candidato está disponível para revisão com P0/P1 corrigidos, evidências e recuperação preservadas. A autorização recebida abrangeu correções e ensaio isolado; nenhuma promoção para tráfego ativo ou produção foi inferida.
