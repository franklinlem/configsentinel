# ConfigSentinel — revisão de prontidão para produção

Data: **31/10/2026**. Candidato: **v0.1.0-rc.1**. Base examinada: `5819b7fce93c10cceabbe59fde5fac4f647b707c`.

**Decisão: NO-GO para produção.** O aceite visual informado por Franklin permanece válido. Ele não resolve os bloqueadores de dependências e operação abaixo. Produção permanece desativada; esta revisão não publicou imagens nem executou deploy.

A arquitetura foi preservada. Foram acrescentados testes, uma mitigação de retenção de segredos em traces E2E, um probe somente leitura para backups e exemplos de preparação de release. Os exemplos não estão instalados nem integrados ao Coolify/Kuma. Nenhum arquivo real de configuração foi monitorado, nenhuma porta pública foi aberta, nenhum outro serviço ou proxy foi modificado. As consultas remotas foram somente leitura e restritas ao ConfigSentinel; os ensaios de falha e as escritas de teste ocorreram localmente com fixtures sintéticas.

## Evidência e limites

- Homologação: `https://configsentinel-dev.franklem.uk`; aplicação Coolify `oi6lvzwzomwtbbgzf5uzofuh`. API, web e banco saudáveis na inspeção; piloto restrito a `/fixtures/demo.conf` no frank-note2.
- Inspeção ao vivo em 31/10, incluindo snapshot de logs às 18:28 UTC; não constitui monitoramento contínuo.
- [Inventário sanitizado, vulnerabilidades completas e benchmark](evidence/production-readiness-2026-10-31.json). As contagens de scanner são ocorrências pacote/advisory, com possíveis repetições do mesmo CVE em pacotes diferentes.
- SBOM CycloneDX das imagens exatas inspecionadas: [API](evidence/api-sbom-2026-10-31.cdx.json), [web](evidence/web-sbom-2026-10-31.cdx.json), [banco](evidence/db-sbom-2026-10-31.cdx.json). Checksums no inventário. Gerados a partir dos arquivos de imagem exportados por leitura; não são atestações assinadas de um build de release.
- Relatórios brutos e logs locais ficam em `.local/readiness/`, ignorado pelo Git. Segredos e dumps não integram o relatório versionado.
- Testes não são auditoria externa, certificação WCAG, fuzzing prolongado nem prova de ausência de exploração.

## Checklist de segurança

| Controle | Resultado e evidência |
| --- | --- |
| Tokens de agentes emitidos uma vez | PASSOU: resposta `no-store`, segredo somente na emissão, persistência por hash, metadados sem token bruto. Teste de emissão, consulta, auditoria e logs. |
| Browser não persiste token de agente | PASSOU no E2E: resposta sintética de provisionamento, ausência em localStorage/sessionStorage e remoção do campo ao fechar o diálogo. Não provisionou agente remoto. |
| Segredos nos logs | Nenhum token no formato completo `cs_` + 43 caracteres ou cookie de sessão encontrado nas últimas 2 h dos logs da API/web e piloto. Escopo limitado a esses padrões/janela; não prova todo histórico. |
| Artefatos de teste | MITIGADO: Playwright agora usa `trace: off`; `retain-on-failure` podia persistir senhas/respostas de emissão. Não foram encontrados traces antigos no checkout. Falhas de testes não imprimem credenciais. |
| Arquivos de credenciais | Arquivos locais de homologação/configuração/token e chave do backup com modo 0600; token fica fora da fila e do snapshot do agente no cenário testado. Docker/Coolify ainda são domínios de confiança do operador. |
| Sessões | PASSOU: cookie Secure/HttpOnly/SameSite=Strict, validade de 8 h, sessão no banco por hash, logout e reset administrativo revogam sessões. Cookie seguro verificado em resposta do servidor de teste; homologação usa HTTPS. |
| CSRF | PASSOU: alterações administrativas exigem CSRF e origem permitida; requisição sem valor válido retorna 403. Segredo CSRF da sessão é guardado em sessionStorage, distinto do token do agente. |
| RBAC e tenants | PASSOU nos testes: sem sessão 401, viewer não provisiona, admin de projeto não acessa outro projeto, organização alheia 404; consultas vinculam organização/projeto. Não foi encontrado bypass nos caminhos examinados. |
| Separação agente/admin | PASSOU: bearer do agente não autoriza administração; cookie administrativo não autoriza ingestão; tentativa de injetar `agent_id` no payload rejeitada com 422; token expirado/revogado retorna 401. |
| Banco com menor privilégio | **FALHOU**: `current_user=configsentinel`, `rolsuper=true` em homologação. A mesma credencial inicializa o banco e atende a API. |
| Rede e containers | Sem portas do host na central/piloto; banco em rede interna; API e agente UID 10001, capacidades removidas e no-new-privileges. Piloto read-only sem Docker socket. |
| Dependências de aplicação | npm sem achados; Go sem vulnerabilidades alcançáveis detectadas, mas há advisory de módulo não importado; ver scanner de imagens abaixo. |
| Dependências de imagem | **FALHOU**: web e banco contêm achados CRITICAL/HIGH. Imutabilidade da base não substitui atualização de segurança. |

Permissões de negócio foram verificadas pelo backend; a interface ainda mostra ações/menus administrativos ao viewer, que recebe 403 ao tentar usá-los. Não existe fluxo completo de desligamento de membros no painel. Validar revogação de permissões/sessões no procedimento de saída antes de operação com usuários reais.

Acesso a outro tenant foi exercitado nos testes de integração existentes, assim como replay idempotente, UUID/seq conflitantes, reconhecimento e retenção. Isso não equivale a testar todas as combinações possíveis de papéis e recursos.

## Agente Linux

A leitura permanece restrita a caminhos absolutos explicitamente autorizados e `hash_only`. A denylist embutida é cumulativa. `openat2` usa `RESOLVE_NO_SYMLINKS` e `RESOLVE_NO_MAGICLINKS`, sem fallback inseguro; `O_NONBLOCK`, `fstat`, exigência de arquivo regular e `nlink == 1` rejeitam FIFO, diretórios e hardlinks. O streaming limita bytes e compara identidade/timestamps antes e depois, incluindo reabertura do caminho.

Passaram os casos de symlink final/intermediário, troca concorrente por symlink (300 tentativas adicionais), hardlink, permissão negada, FIFO, diretório, limites e arquivo instável. Fila SQLite preserva eventos/UUIDs/seq em reabertura, rejeita identidade divergente e não avança snapshot quando cheia. Teste adicional confirma que bearer não é persistido na fila. Não houve ampliação de allowlist, capabilities ou permissões.

Limites pendentes: não há prazo total/cancelamento garantido de I/O em filesystem bloqueado ou de rede; operar somente com filesystem local. A leitura do arquivo de token faz stat/leitura sem as mesmas garantias de `openat2`/tipo/limite dos arquivos monitorados. A fila pode seguir um symlink caso seu diretório seja gravável por um atacante local. Manter token/diretório da fila privados ao UID dedicado; endurecer esses acessos em correção posterior. Não há proteção contra root/UID do próprio agente comprometido nem captura garantida de mudanças entre polls.

## Vulnerabilidades de dependências

Scanner: Trivy **0.76.1**, distribuição oficial com checksum conferido; base atualizada em 31/10/2026 às 13:09 UTC, consultada nesta revisão. Imagens exportadas dos containers de homologação, sem rebuild ou substituição remota.

| Imagem examinada | CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN |
| --- | ---: | ---: | ---: | ---: | ---: |
| API | 0 | 0 | 0 | 0 | 1 |
| Web | 1 | 46 | 82 | 96 | 4 |
| PostgreSQL | 1 | 25 | 31 | 3 | 1 |

- **Web: CVE-2026-111497**, `brotli-libs 1.2.0-r0`, correção indicada `1.2.1-r0`. Escrita fora dos limites no decoder; o mantenedor publica a correção na [release Brotli 1.2.1](https://github.com/google/brotli/releases/tag/v1.2.1). O pacote está instalado; não foi demonstrado caminho de decodificação de conteúdo não confiável nesta configuração do nginx. Não presumir RCE do produto apenas pelo achado de pacote.
- HIGH da web incluem curl/libcurl, libcrypto/libssl, c-ares, libexpat, libuuid, libxml2, pcre2 e tiff. Versões/fixes por ocorrência no inventário. Recriar base mínima atualizada e reescanear; não suprimir em bloco.
- **Banco: CVE-2025-68121**, stdlib Go `1.24.6` no utilitário `/usr/local/bin/gosu`, com correção indicada a partir de `1.24.13`/`1.25.7`. O [advisory oficial Go](https://pkg.go.dev/vuln/GO-2026-4337) descreve condições específicas de retomada TLS. O scanner detectou a stdlib incorporada; não foi provado uso de TLS vulnerável pelo gosu nem vulnerabilidade do servidor PostgreSQL por esse CVE. Os 61 achados do banco estão associados ao binário gosu; esta varredura não achou vulnerabilidades nos pacotes Alpine desse banco. Atualizar a imagem upstream ou documentar análise de alcançabilidade/VEX específica, revisada e com prazo, antes de excepcionar o gate.
- **API: GO-2026-5932**, `golang.org/x/crypto v0.58.0`, pacote `openpgp` sem manutenção e sem versão corrigida indicada. `govulncheck` reporta um achado de módulo; a árvore efetiva importa argon2, não openpgp. Zero vulnerabilidades alcançáveis detectadas. [Advisory oficial](https://pkg.go.dev/vuln/GO-2026-5932). O GPG externo do backup não é esse pacote.
- Agente: `govulncheck` sem achados. Web: `npm audit` com 0 em todas as severidades. Esses resultados cobrem dependências de código e **não anulam os achados das imagens**. A imagem do piloto/agente não recebeu scanner de imagem nesta rodada; incluir o artefato distribuído ao liberar o agente.

## Backups e recuperação

O timer de usuário no frank-note2 continua habilitado, linger ativo, diário 03:35 America/Sao_Paulo com jitter de até 120 s. Serviço observado com `Result=success`; último sucesso **31/10/2026 17:55:32 UTC**, cerca de 32 minutos antes do snapshot. Arquivo criptografado de 7.187 bytes, SHA-256 conferido; chave 0600. Retenção configurada: 7 diários e 4 semanais. Ainda há apenas um dia de evidência, sem prova de rotação ao longo de semanas.

Restore repetido nesta revisão: GPG via SSH em streaming para PostgreSQL local descartável, sem rede/portas e sem dump plaintext em arquivo. `pg_restore --exit-on-error` passou: schema 1, 1 organização, 4 eventos, 1 reconhecimento. É restauração do conteúdo existente; não mede RTO completo nem recupera toda a infraestrutura.

Teste de transporte SSH falhando em ambiente temporário confirmou saída de erro, remoção de parcial e preservação do último backup/marker válido. **A falha é detectada pelo processo, mas não há alerta ativo de falha/atraso:** sem OnFailure/canal dedicado, sem avaliação independente da idade, monitor Kuma ID 20 verifica apenas readiness HTTP. Não chamar o monitor de backup de configurado.

Preparado [check-backup-health.py](../scripts/check-backup-health.py), somente leitura: idade padrão máxima 26 h, checksum, marker, arquivo e resultado systemd; retorna 2 em falha. Testes passam para backup recente, 27 h de atraso, serviço com erro e checksum corrompido. Executado uma vez por stdin no frank-note2, resultado OK. **Não foi instalado/agendado nem conectado a notificações.**

Pendências: timeout total SSH/GPG, trava contra sobreposição, falha fechada se chave já provisionada sumir (script atual cria outra), monitor independente de frescor e entrega de alerta confirmada, cópia protegida da chave fora do frank-note2. Backup cobre somente o banco ConfigSentinel, não token/config/fila dos agentes, segredos Coolify nem outros serviços.

## Alertas de agentes e manutenção

Os alertas atuais são estados exibidos/calculados pela central; não há entrega externa de notificações de eventos no MVP. Testes de integração da central e do ciclo real do agente exercitaram:

| Cenário sintético | Comportamento atual |
| --- | --- |
| Heartbeat recente, fila normal | saudável |
| Heartbeat antigo | offline |
| Última coleta antiga com contato recente | coleta atrasada |
| Fila ≥ 8.000 | queue_high |
| Fila alta + heartbeat antigo | queue_high prevalece e oculta offline |
| Ingestão falha com heartbeat acessível | agente não envia heartbeat nesse ciclo |

Bloqueador: o loop chama `Heartbeat` somente depois de `Flush` bem-sucedido. Resposta 503, lote inválido/conflitante 409/422 ou fila acumulada podem impedir a telemetria que explicaria a falha. Teste do runner real com `--once`, endpoint de heartbeat acessível e ingestão 503 reproduziu zero chamadas de heartbeat; após recuperar a ingestão, o lote preservado e o heartbeat foram enviados. Separar seus agendamentos com cancelamento/backoff preservando fila e identidade.

Outras lacunas: limiar fixo 8.000 não acompanha `max_queue`; prioridade única mascara condições simultâneas; clock skew baseado na observação antiga pode confundir coleta parada e relógio errado. Implementar estados independentes e cenários de recuperação. A goroutine de retenção encerra silenciosamente após o primeiro erro de `Retain`, sem retry/métrica; ensaio remoto de falha não foi executado. Métricas de ingestão não contam todas as falhas (principalmente conflito), e sum/count não fornece p95.

## Benchmark de ingestão

Mesmo endpoint Docker local, 25 agentes × 100 eventos, 5 lotes concorrentes, 25 amostras por repetição, sem descartar warm-up. Dados sintéticos; nenhuma carga gerada na homologação remota.

| Execução | p50/lote | p95/lote | Máximo | Erros |
| --- | ---: | ---: | ---: | ---: |
| Referência anterior | 217,73 ms | 349,86 ms | 365,54 ms | 0 |
| Revisão 1 | 218,71 ms | 364,53 ms | 365,19 ms | 0 |
| Revisão 2 | 245,06 ms | 303,83 ms | 306,31 ms | 0 |
| Revisão 3 | 235,28 ms | 280,71 ms | 283,99 ms | 0 |

7.500 eventos novos nesta rodada, zero erros. **Meta indicativa de 300 ms não está demonstrada consistentemente**; variação entre execuções e amostra pequena impedem afirmar SLO. Não substituir p95 por média entre repetições.

Tracing de integração mostrou **304 comandos PostgreSQL por lote de 100 eventos**, incluindo autenticação/transação/lock; cerca de três por evento. Nesse ensaio instrumentado com race/Unix socket: 112,77 ms acumulados nas consultas e 140,11 ms no handler, não comparáveis diretamente ao benchmark HTTP. EXPLAIN local usa índices de seq e UUID (`BitmapOr`), execução 0,792 ms; não há evidência de índice ausente como causa principal.

Hipótese prioritária: custo linear de round trips, validação e operações por evento. Próximo experimento limitado: pipeline `pgx.Batch`/pré-carregamento de duplicatas e inserções em lote, preservando transação atômica, lock por agente, replay/seq/UUID e observação mais recente por alias. UPSERT em lote precisa deduplicar aliases no mesmo lote. Nenhuma otimização funcional foi aplicada nesta revisão. Repetir com warm-up, centenas de lotes, tamanhos diferentes e recursos medidos após a correção.

## Testes executados nesta revisão

| Validação | Resultado |
| --- | --- |
| API `go test -race ./...` com PostgreSQL isolado | PASSOU, incluindo integração real, RBAC/tenants/CSRF, replay, reconhecimento/retenção e testes novos de tokens, sessões, alertas e contagem de consultas |
| Agente `go test -race ./...` | PASSOU, incluindo testes novos de troca concorrente de symlink, token/fila e heartbeat bloqueado por ingestão |
| `go vet ./...` nos dois módulos | PASSOU |
| Operação Python | 3 testes passaram: backup/falha, probe de idade/integridade/serviço e gate de release |
| Navegador Playwright | 4 testes passaram: jornada original, páginas/erros/responsividade, credencial efêmera e caracterização de indisponibilidade inicial |
| Axe WCAG A/AA | 0 violações nas sete páginas autenticadas examinadas; assertion adicionada ao E2E |
| Responsividade | Sem overflow horizontal em 390/768/1280 px nos cenários executados; jornada original inclui navegação mobile |
| Erro de eventos 503 | Alerta visível no painel, teste passou |
| Erro inicial `/me` 503 | Lacuna reproduzida: apresenta login sem informar indisponibilidade |
| `npm run build` / contrato OpenAPI | PASSOU; 24 paths validados |
| `govulncheck` / `npm audit` | Resultados e limites na seção de vulnerabilidades |
| Gitleaks | Sem vazamento encontrado no histórico versionado; arquivos ignorados de credenciais não publicados. Verificação final registrada em validation.md |
| CI remoto | [41230354166](https://github.com/franklinlem/configsentinel/actions/runs/41230354166): todos os jobs passaram (API, agente, web/E2E/axe/operação e segredos), commit `74d41fb`. |
| Compose por digest | Renderizado com digests sintéticos: 3 serviços, sem build/portas do host, banco interno. Nenhum `up` executado |
| Manifest de exemplo | NO-GO esperado: placeholders, scans/atestação e aprovações ausentes. Não autoriza release |

Asserções de caracterização documentam falhas conhecidas; passar esses testes não significa que heartbeat, prioridade dos alertas ou `/me` 503 foram corrigidos. A cobertura visual humana permanece o aceite informado pelo usuário. Axe não testa integralmente leitores de tela, ordem de foco em todos os estados, zoom 200%, todos os perfis ou todas as combinações de dados. Sessão expirada e nova aba sem CSRF em sessionStorage precisam de UX de recuperação; backend continua negando mutações não autorizadas.

## Pendências por severidade

Severidade abaixo representa prioridade de liberação, separada do CVSS do scanner.

| Prioridade | Pendência | Condição de encerramento |
| --- | --- | --- |
| P0 — bloqueador | Imagem web com CRITICAL e 46 HIGH; banco com CRITICAL e 25 HIGH em gosu | Atualizar/reduzir imagens, gerar SBOM, reescanear artefatos finais. Eventual VEX deve comprovar não alcançabilidade por advisory, ter revisão e prazo; gate atual não aceita exceção automática |
| P1 — bloqueador | API conecta como superusuário | Separar migrador/owner de usuário de execução, grants mínimos e teste de operação/negação; impedir mutação indevida de auditoria por grants quando aplicável |
| P1 — bloqueador | Heartbeat condicionado ao sucesso da fila | Telemetria independente comprovada sob 409/422/503, fila cheia e recuperação, sem perda de eventos |
| P1 — bloqueador | Backup sem alerta de atraso/falha e sem cópia externa da chave comprovada | Agendar probe independente, confirmar alerta recebido, timeout/trava/chave fail-closed e recuperação com cópia protegida |
| P1 — bloqueador | Promoção imutável não ensaiada | Registry privado, atestações/SBOM/scan de API/web/banco, mesmo digest aprovado em homologação, ensaio de rollback e aprovação humana |
| P2 | Alertas simultâneos, limiar configurável e clock skew | Testes independentes de offline/coleta/fila e recuperação |
| P2 | Retenção para após erro; observabilidade incompleta | Retry/backoff/log sem segredo, métrica de falhas e histograma de latência |
| P2 | p95 varia de 280,71 a 364,53 ms | Medição sustentada reproduzível e decisão documentada sobre meta de 300 ms |
| P2 | Arquivo do token/fila e prazo de I/O | Acessos seguros e limitados, diretórios privados, teste de deadline sem ampliar permissões |
| P2 | UX de sessão/nova aba/indisponibilidade e ações sem permissão | Fluxos de recuperação e erro, testes com viewer/expiração e acessibilidade manual |
| P2 | Limites globais de login/agente e desligamento de membro | Política que evite starvation entre identidades e procedimento de revogação verificado |
| P2 | Reprodutibilidade do CI | Fixar actions/ferramentas por versão/digest revisado; scanner de imagens periódico e gate antes da publicação |
| P3 | Advisory openpgp não alcançável | Acompanhar dependência e revalidar reachability nas atualizações; não suprimir o módulo inteiro |

## Estratégia de release preparada

1. Corrigir os bloqueadores em branch, mantendo o RC e a arquitetura. Não promover este relatório como autorização. Atualizações de bases devem usar novos digests revisados, sem `apk upgrade` imprevisível durante o deploy.
2. Pipeline manual de candidato: build API/web uma vez a partir do commit aprovado, com `docker buildx build --sbom=true --provenance=mode=max --push` para GHCR privado. Publicar agente por arquitetura com checksum/SBOM quando distribuído. Revisar o contexto/argumentos para não incluir segredos na provenance; usar BuildKit secrets quando necessário. [Documentação oficial de SBOM](https://docs.docker.com/build/metadata/attestations/sbom/).
3. Capturar digest do índice/manifest e os manifests de plataforma; escanear cada plataforma efetivamente utilizada, incluindo banco/gosu. Gerar CycloneDX/SPDX, SHA-256, relatório com base/data do scanner e vínculo ao commit. Atestar/verificar identidade/proveniência; assinatura e política ainda não estão implementadas nesta revisão.
4. Gates: testes pertinentes verdes, zero HIGH/CRITICAL no gate atual, análise dos UNKNOWN e SBOM/atestação verificadas. Não confundir campos booleanos preenchidos com verificação criptográfica. Novos advisories exigem reavaliação mesmo com digest imutável.
5. Homologar os exatos digests e ensaiar rollback isolado. Preparado [compose.digest.example.yml](../deploy/compose.digest.example.yml), apenas exemplo do host de homologação existente, sem builds e com API/web/banco por referência obrigatória. Ele não é template pronto de produção e não corrige sozinho o papel superusuário. No Coolify usar Compose com imagens do registry e credencial de pull somente leitura, sem alterar proxy/portas/outros serviços. [Documentação Coolify](https://coolify.io/docs/applications/builds/docker-compose).
6. Registrar commit, três digests, checksums SBOM, scans e aprovações no [manifest de exemplo](../deploy/release-manifest.example.json). `python3 scripts/check-release-manifest.py <manifest>` valida formato e declarações; **não autentica os artefatos nem executa deploy**. O exemplo retorna NO-GO deliberadamente.
7. Somente após correções, revisão do manifest e aprovação explícita de Franklin, preparar a aplicação de produção isolada. Nenhum webhook ou deploy automático foi configurado nesta rodada. Preservar o digest anterior e sua documentação no registry.

## Critérios de rollback e autorização

Interromper promoção e reverter o candidato se readiness não estabilizar, houver aumento sustentado de 5xx/latência além do limite aprovado, perda/duplicação indevida de eventos, autorização cruzada, exposição de segredo, migração malsucedida ou falha de persistência/fila. Definir janela e limites quantitativos no ensaio do próximo candidato; os dados atuais não sustentam um SLO de produção.

Rollback de aplicação: selecionar os últimos digests **aprovados para o mesmo ambiente**, verificar compatibilidade do schema e healthchecks, manter volumes/identidades/fila/segredos e confirmar login, autorização, ingestão/replay e recuperação do agente. Nunca usar `latest` ou reconstruir o commit antigo esperando a mesma imagem. Na primeira liberação, sem versão anterior de produção, desativar somente a nova aplicação conforme plano aprovado e preservar evidências/dados.

Migrações precisam de estratégia expand/contract e compatibilidade com o binário anterior. Não reverter schema destrutivamente nem executar `down -v`. Antes de migrar, obter backup recente verificável. Restore deve primeiro ocorrer em banco separado, validar integridade e avaliar perda desde o snapshot; substituir banco ativo exige aprovação explícita. Não há RPO/RTO contratados: diário implica exposição nominal de até 24 h entre backups bem-sucedidos, podendo ser maior com falhas; restauração completa cronometrada e cópia da chave ainda são gates.

**Conclusão:** homologação funcional e aceite visual mantidos; evidência insuficiente e bloqueadores concretos impedem produção. Aguardar aprovação de Franklin para a rodada de correções. Nenhum deploy em produção realizado.
