# ConfigSentinel RC2 — procedimento de homologação ativa

Atualizado em **01/11/2026, America/Sao_Paulo**. Branch `plan/active-homologation-rc2`.

**Uma única nova tentativa de J5 retornou internal_error; homologação indisponível e NO-GO.** API/web continuam **paradas desde 09:41:52 -03**; banco RC1 saudável no volume original. As três roles de J4 foram aplicadas; configuração Coolify permanece RC1 e nenhum deploy RC2 foi solicitado. Produção continua não autorizada. [Resultado da janela](evidence/active-rc2-window/execution-summary.json).

SHA de preparação autorizado: `36baf66f4656f86d157cd070202323db9465c5f4`; código das imagens: `ea868efaa3e3b364d012981e597c8faf6bc30651`. A autorização específica desta execução substitui o G0 pendente da preparação; não autoriza continuar após o ponto de parada abaixo. As seções de preparação e ensaios anteriores permanecem como histórico, com os respectivos limites.

## 1. Alvo e artefatos congelados

| Item | Valor |
| --- | --- |
| Recurso existente | Coolify `oi6lvzwzomwtbbgzf5uzofuh`, Contabo, raw Compose, sem build server |
| Versões verificadas | Coolify **4.5.3**, Docker Compose **5.6.1** |
| Homologação ativa | RC1 `5819b7fce93c10cceabbe59fde5fac4f647b707c`, branch `main`, `/deploy/compose.coolify.yml`, auto-deploy desabilitado |
| URL preservada | `https://configsentinel-dev.franklem.uk` |
| Compose da promoção | [compose.active-homologation.yml](../deploy/compose.active-homologation.yml) no SHA de preparação que Franklin aprovar; não usar HEAD móvel |
| Volume obrigatório | `oi6lvzwzomwtbbgzf5uzofuh_postgres_data`, externo, `/var/lib/postgresql/data` |
| Redes existentes | `oi6lvzwzomwtbbgzf5uzofuh_database` (interna), `oi6lvzwzomwtbbgzf5uzofuh_app`, `coolify` |
| Código RC2 | `ea868efaa3e3b364d012981e597c8faf6bc30651`; plataforma linux/amd64 |
| Manifest principal | [release-manifest.candidate.json](../deploy/release-manifest.candidate.json) |
| Manifest de fallback | [release-manifest.fallback.json](../deploy/release-manifest.fallback.json) |

O SHA da preparação contém Compose/procedimentos; ele é distinto do SHA do código das imagens. A autorização da janela deve identificar ambos, os manifests e seus checksums. Não reconstruir imagens durante promoção ou rollback.

Digests aprováveis para a janela (todos em `ghcr.io/franklinlem/`):

| Papel | Repositório | Digest SHA-256 |
| --- | --- | --- |
| API RC2 / migrator | `configsentinel-api` | `ea0a14eda7478d9b4a5091effbb7a990a40594fd56085dd0c483809201a16ec4` |
| API fallback compatível com RC1 | `configsentinel-api` | `cacace0b74ddb9bdef72109436035c59305e4c6bb02c063fe0788ce069cffc66` |
| Web endurecida | `configsentinel-web` | `e7604db734053aed8834c0c4025001fcafab1026e50bca1f8b02aee1fb6cd8d3` |
| PostgreSQL 17.11 endurecido | `configsentinel-db` | `ceeafd17328e0a09fa2999be01ccdec407e3318306d392c00646cf1dc74b4447` |
| Agente RC2, etapa posterior | `configsentinel-agent` | `4c2936e175883f0488682989b3cd8d8218eeca871beb5d1467a1bb10744ab6d1` |

**MIGRATION_IMAGE é independente de API_IMAGE:** o RC1 não possui `--migrate`. Mesmo no rollback HTTP, o migrator permanece no digest RC2. Web e DB RC1 históricos têm vulnerabilidades bloqueadoras e nunca fazem parte deste rollback. Seus archives ficam preservados como origem/evidência, não como imagens executáveis aprovadas.

## 2. Checklist G0–G6 e limites das evidências

[Checklist estruturado](evidence/promotion/precheck-gates.json). PASS significa precheck executado no escopo permitido, não implantação ativa ou operação futura já concluída.

| Gate | Status | Evidência e limite |
| --- | --- | --- |
| G0 — janela ativa | **PASS** | Autorização explícita de Franklin para J0–J8 neste UUID e SHA de preparação aprovado; execução interrompida no gate J3 |
| G1 — autenticidade/pull | **PASS** | [Workflow read-only](https://github.com/franklinlem/configsentinel/actions/runs/41305428149), [resultados finais](evidence/promotion/readonly-pull-final-results.json): cinco digests, assinatura direta, provenance, SBOM e scans verificados online. Token reportado pelo GitHub: contents/read, metadata/read, packages/read. Nenhum deploy; [inspeção final dos quatro digests centrais](evidence/promotion/cache-inspection.json) passou após refresh |
| G2 — fallback limpo | **PASS** | [Build assinado](https://github.com/franklinlem/configsentinel/actions/runs/41259750008), [manifest](../deploy/release-manifest.fallback.json), [ensaio](evidence/promotion/isolated-promotion-rehearsal.json): RC2 → fallback → RC2; login/RBAC/CSRF/eventos/replay/heartbeat/auditoria passaram |
| G3 — recuperação preparada | **FAIL na janela J3** | [Backup final](evidence/active-rc2-window/final-backup-encrypted.json) com checksum/decriptação válidos e catálogo legível; [destino isolado falhou no bootstrap](evidence/active-rc2-window/isolated-bootstrap-diagnostic.json), sem restore efetivo. Snapshot renovado/offsite passou; restores anteriores não substituem este gate. |
| G4 — Compose/persistência/variáveis | **PASS** | [Validação protegida](evidence/promotion/protected-compose-validation.json), [caminho instalado](evidence/promotion/coolify-installed-path.json): nomes externos preservados, sem build/ports, DSNs separados, secrets preservados no serializer e sem ADMIN_PASSWORD no HTTP/migrator. Persistência das novas variáveis no Coolify ainda não foi executada |
| G5 — backup/Kuma/entrega | **PASS no escopo isolado/leitura** | [Monitor 21](evidence/promotion/kuma21.json): push ativo, 600 s, retry 60 s/maxretries 0, canal HermesFranklem e UPs recentes. [Recebimento humano](evidence/promotion/alert-receipt-confirmation.json) confirmado. [Ausência de push](evidence/promotion/kuma21-missing-push.json) testada no ramo exato do código instalado com relógio isolado |
| G6 — roles e caminho Coolify | **PASS no escopo isolado/leitura** | [Ensaio](evidence/promotion/isolated-promotion-rehearsal.json), [probe](evidence/promotion/coolify-installed-path.json): adoção transacional preservou contagens de 14 tabelas; runtime autenticado por TCP, dez operações negadas; parser raw, validação de comandos, injeção de flags e skip de pull exercitados na versão instalada |

**Limites que continuam explícitos:** não se pausou o timer real por 10 min para disparar alerta de ausência de push; sua lógica foi testada com relógio isolado, e a entrega humana comprovada refere-se aos testes de atraso/checksum/DOWN/UP anteriores. Não foi executado um job completo de deploy na fila do Coolify: os métodos indicados foram exercitados com clone em memória, transação read-only e bloqueio de SSH/log persistence; o comando gerado foi executado no Compose isolado. O caminho completo, persistência de envs e smoke pela URL ativa pertencem à janela. Se Franklin exigir esses dois ensaios end-to-end antes da janela, eles permanecem **PENDENTES**, exigindo nova infraestrutura isolada completa ou autorização específica; não equivalem a resultados já obtidos.

Todos os scans podem envelhecer. Atualizar base Trivy, repetir verificação online e confirmar o cache imediatamente antes de qualquer parada. Qualquer novo HIGH/CRITICAL, alteração de versão/configuração ou divergência de digest revoga o PASS correspondente. Nenhuma supressão em bloco ou `ignore-unfixed` foi usada. API RC2 e fallback possuem somente GO-2026-5932 UNKNOWN, anteriormente analisado como módulo openpgp não chamado; web/DB/agente sem achados nos scans registrados.

## 3. Ensaios e recuperação preservada

O clone `configsentinel-prechecks-5a04dd888b` utilizou redes internas e volume próprios, sem portas, Traefik, rede Coolify ou dados montados do recurso ativo. Para iniciar um banco com o estado do RC1, o init de roles foi desabilitado apenas no bootstrap isolado; restaurou-se o dump e confirmou-se ausência das três novas roles. Depois, provisionamento transacional, grants e migrator adotaram o schema existente. O DB foi reaberto com a configuração normal da imagem endurecida, sem reinicializar os dados.

As 14 contagens permaneceram iguais na adoção. No ciclo RC2/fallback/RC2, os eventos foram de 4 para 5/6/7 porque cada etapa inseriu um evento sintético e repetiu seu UUID: sem duplicação; dois reconhecimentos preservados. [Comparação por identidade e conteúdo](evidence/promotion/preserved-event-rows.json) confirmou os quatro eventos e dois reconhecimentos originais integralmente iguais no clone. Readiness 200, RBAC/CSRF 403, tenant negado, heartbeat **202** conforme contrato, auditoria legível e logout invalidando sessão passaram nas três etapas. Os containers isolados estão parados e todos os volumes foram preservados, inclusive o primeiro ensaio interrompido.

Snapshot GPG AES256 0600: somente application/settings/env desse UUID, spec dos seus três containers, Compose gerado e novas credenciais de roles ainda não instaladas. Roundtrip de decriptação e SHA-256 passaram; há cópia criptografada no frank-note2. Chave de recuperação exclusiva ConfigSentinel permanece fora do repositório. Localizações privadas/checksums estão na evidência, sem valores de secrets.

Backup adicional: `2026-11-01T011256619570Z.dump.gpg`, em destino exclusivo de precheck no frank-note2. Mesmo transporte forced-command/GPG, sem alterar marker, retenção ou arquivos do backup regular. Restore isolado: **3,806 s** de streaming/pg_restore, não RTO completo; schema 1, 4 eventos, 2 reconhecimentos. O backup regular de **01/11 às 03:35:51 -03** também passou em checksum/decriptação na consulta de 09:06 -03; esse arquivo regular posterior não foi o dump restaurado no ensaio. Não confundir os snapshots.

Backup de DB não cobre fila/config/token do piloto. Nenhum arquivo real passou a ser monitorado. O snapshot da configuração contém segredos criptografados: nunca anexar plaintext, chave ou arquivo `.env` ao relatório.

## 4. Pull somente leitura e assinaturas

[readonly-pull.yml](../.github/workflows/readonly-pull.yml) verifica os quatro componentes do candidato e a API fallback com `packages: read`, chave pública fixada, checksums e predicates SBOM, vínculo digest/commit/plataforma e Trivy. Só depois usa [request-registry-pull.py](../scripts/request-registry-pull.py) pelo SSH restrito existente.

O forced-command [registry-pull-only.py](../scripts/registry-pull-only.py) aceita somente os quatro repositórios ConfigSentinel por digest; recebe o token efêmero no stdin do SSH e usa DOCKER_CONFIG temporário 0700, removido ao terminar. O workflow não tem comando de deploy. Não foi criado PAT pessoal nem lido/alterado login Docker compartilhado. A credencial read-only é efêmera por execução, suficiente para precache; não foi instalada credencial duradoura no Coolify.

A [política GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) permite token de workflow para pacotes associados. O [login padrão do Coolify](https://coolify.io/docs/applications/builds/docker-registries) usa configuração Docker do usuário do servidor; este procedimento evita substituí-la. Se houver falha no precache, parar e corrigir o workflow. Não contornar com PAT amplo, token de escrita ou login global.

Cosign 3.1.4 usa [release-signing.pub](../deploy/release-signing.pub), assinatura autogerenciada sem Rekor. Dispensar transparência (`--insecure-ignore-tlog`) não dispensa assinatura; a política não comprova identidade OIDC pública. Trivy 0.76.1 e Cosign são baixados com SHA-256 fixado nos workflows. Verificar os mesmos digests na janela e guardar saídas sanitizadas; não confiar apenas nos booleanos dos manifests.

Reconferência manual testada com sucesso, sem deploy:

```bash
gh workflow run readonly-pull.yml --ref plan/active-homologation-rc2
```

Antes do disparo e ao concluir, conferir que o `headSha` da execução coincide com o SHA de preparação aprovado; divergência bloqueia a janela. O deploy no Coolify continua fixado por SHA, independentemente do nome da branch do workflow.

**Incidente de cache registrado:** ao retomar, o fallback estava ausente do cache. A execução `41305147376` verificou assinaturas/scans e baixou o lote do candidato, mas falhou no segundo lote com diagnóstico genérico. A causa exata não foi estabelecida. A execução manual `41305428149` passou e a inspeção dos quatro digests centrais passou após o refresh. Não se presume cache durável nem se altera limpeza global. O helper exclusivo de precache recebeu somente diagnóstico por etapa/categoria, sem expor stderr/URLs/tokens; versão anterior preservada e quatro testes de não vazamento/isolamento passaram. Falha futura exige parar **antes** da drenagem e reconferir, sem fallback por tag ou credencial ampla.

## 5. Variáveis e comandos definitivos do Coolify

Novas senhas: runtime e migrator distintas, aleatórias de 32 bytes representados em hexadecimal, guardadas somente em arquivos privados 0600/snapshot criptografado. Não instaladas no ativo. Preservar POSTGRES_PASSWORD existente sem rotação. Configurar somente neste UUID, como runtime e literal, nunca como build args:

| Variável | Valor/origem |
| --- | --- |
| `POSTGRES_PASSWORD` | Segredo atual exclusivo do DB, preservado |
| `RUNTIME_DB_PASSWORD` | Preparação privada `promotion-credentials.json`, chave runtime |
| `MIGRATOR_DB_PASSWORD` | Mesmo arquivo, chave migrator |
| `CONFIGSENTINEL_API_IMAGE` | API RC2 do manifest; somente esta muda para API fallback em rollback |
| `CONFIGSENTINEL_MIGRATION_IMAGE` | Sempre API RC2 do manifest, inclusive no rollback HTTP |
| `CONFIGSENTINEL_WEB_IMAGE` | Web endurecida do manifest |
| `CONFIGSENTINEL_DB_IMAGE` | PostgreSQL 17.11 endurecido do manifest |

O Compose fixa PUBLIC_URL/COOKIE_SECURE. Não enviar ADMIN_EMAIL/ADMIN_PASSWORD ao HTTP ou migrator deste banco já inicializado; não remover os campos protegidos atuais antes de guardar snapshot. Não colocar GHCR_TOKEN no ambiente dos serviços. Operador Docker/Coolify é domínio de confiança, com acesso aos secrets runtime.

Renderizar em arquivo privado, sem imprimir o resultado:

```bash
umask 077
docker compose --env-file .local/prechecks/coolify-generated.env \
  --project-name oi6lvzwzomwtbbgzf5uzofuh \
  -f deploy/compose.active-homologation.yml config --format json \
  > .local/prechecks/active-compose.rendered.json
```

O arquivo acima é saída privada do serializer instalado, conferida contra os valores originais sem exposição. Na janela, regenerar a partir dos valores finais protegidos e confirmar nomes externos, imagens, DSNs, ausência de portas/build e dependência `service_completed_successfully`. Não usar `source` de env e não habilitar shell tracing.

**Custom build:** copiar o comando literal `custom_build_command` de [coolify-installed-path.json](evidence/promotion/coolify-installed-path.json). Ele executa `docker image inspect --format '{{.Id}}'` nos quatro digests centrais necessários (API RC2, API fallback, web, DB), imprimindo somente IDs. Foi validado pelo método da versão instalada. O comando anterior com `>/dev/null` é rejeitado pelo validator do Coolify e foi substituído.

**Custom start:**

```bash
docker compose --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build
```

O Coolify injeta project-directory, Compose e env-file, conforme ensaio; não executar CLI manual concorrente. Manter raw Compose e build server desabilitado. Com custom build e sem build server, o método instalado pula o pull automático; essa condição foi exercitada sem executar operações remotas. Imagem ausente deve falhar, sem download implícito ou fallback para tag.

O job completo do Coolify normalmente para/remove os containers antigos, inclusive DB, antes de criar os novos. Na janela isso significa indisponibilidade da aplicação; o volume externo deve permanecer. O job também verifica a rede do UUID e tenta conectá-la ao proxy: ambos já existem/estão conectados na inspeção final. Se essa condição mudar, **parar**, sem autorizar modificação de Traefik ou criar conexões novas ao proxy. Não usar opção de deploy forçado/rebuild para contornar gate.

## 6. Sequência da futura janela — somente após G0

1. **J0 — autorização e exclusão mútua.** Registrar aprovação explícita deste recurso/janela, responsável, SHA de preparação, manifests/checksums e ciência dos limites G5/G6. Confirmar ausência de deploy em andamento; auto-deploy continua desligado. Nenhuma atualização do piloto ou produção está incluída.
2. **J1 — reconferência com RC1 rodando.** Repetir G1: assinatura/scans com base vigente e precache read-only. Conferir cache dos quatro digests centrais, volume/redes, Coolify 4.5.3, raw Compose/sem build server, snapshot/roles preparados, capacidade de disco/memória e acesso à chave. Se houver drift, bloquear a janela e rever o plano; não fazer limpeza automática.
3. **J2 — snapshot e drenagem.** Renovar snapshot criptografado somente desse UUID antes de editar campos. Parar somente API/web ConfigSentinel, com 30 s de término; aguardar transações/retention worker. Registrar contagens das 14 tabelas/schema e IDs dos eventos, sem conteúdo sensível. O DB continua em execução. O agente RC1 continua ativo e preserva fila; heartbeat pode atrasar durante indisponibilidade de ingestão no binário antigo.
4. **J3 — backup final obrigatório.** Com escritores drenados, criar backup criptografado em destino exclusivo novo, sem retenção, usando o script existente com `--base` próprio. Validar checksum/decriptação/restore isolado e contagens contra a baseline. Backup antigo ou teste anterior não substitui este passo. Lock/timeout/chave ausente/falha: parar a janela e preservar todos os arquivos; nunca forçar lock nem excluir recovery points.
5. **J4 — adoção transacional.** Com administrador exclusivo do DB, aplicar provisionamento e grants numa transação com lock_timeout 5 s/statement_timeout 60 s; somente credentials novas previamente preparadas. Confirmar schema 1, usuários existentes, owners/grants e ausência de memberships indiretos. Falha => rollback da transação; não dropar objetos ou recriar banco.
6. **J5 — configuração apenas deste UUID.** Fixar o SHA de preparação aprovado e `/deploy/compose.active-homologation.yml`, variáveis da tabela e os comandos customizados já validados. Conferir renderização protegida. Se volume estiver ausente, banco vazio, schema diferente de 1 ou usuários ausentes, parar; nunca permitir bootstrap de substituto.
7. **J6 — um deploy manual.** Acionar somente esse UUID, sem rebuild. DB muda para digest endurecido 17.11 sobre o volume existente; migrate RC2 usa migrator e aplica grants; API usa runtime; web espera readiness. Não executar comandos Docker concorrentes, botão de rollback genérico, `down`, prune ou alterações de redes/Traefik.
8. **J7 — smoke e aceite.** Readiness em até 150 s depois de DB saudável; duas falhas consecutivas ou falha de integridade/permissão impedem aceite. Executar tabela abaixo duas vezes, acompanhar pelo menos 10 min/dois ciclos de monitor, fazer backup pós-mudança e restore isolado. Medir indisponibilidade e recuperação observadas, sem confundir tempo de pg_restore com RTO completo.
9. **J8 — registro.** Atualizar validation/readiness/manifest com digests reais, SHA, backup/contagens, roles, smoke/tempo/rollback. Somente fatos concluídos mudam flags. `production_approved=false`; o piloto continua pendente de autorização própria.

Drenagem futura, **não executada nesta preparação**:

```bash
ssh contabo docker stop --time 30 oi6lvzwzomwtbbgzf5uzofuh-api-1 oi6lvzwzomwtbbgzf5uzofuh-web-1
```

Provisionamento futuro no host Contabo: preparar arquivo SQL sem secrets concatenando [provision.sql](../db/roles/provision.sql), `SET ROLE configsentinel_owner;` e [runtime-grants.sql](../db/roles/runtime-grants.sql). Conferir seus hashes contra o checkout aprovado. O arquivo privado roles.env contém somente CONFIGSENTINEL_RUNTIME_PASSWORD e CONFIGSENTINEL_MIGRATOR_PASSWORD, idênticas às variáveis preparadas. Não imprimir SQL expandido.

```bash
docker exec -i --env-file "$CONFIGSENTINEL_PRIVATE_DIR/roles.env" \
  -e 'PGOPTIONS=-c lock_timeout=5s -c statement_timeout=60s -c log_statement=none -c log_min_error_statement=panic' \
  oi6lvzwzomwtbbgzf5uzofuh-db-1 \
  psql -X --single-transaction -v ON_ERROR_STOP=1 -U configsentinel -d configsentinel -f - \
  < "$CONFIGSENTINEL_PRIVATE_DIR/roles-adopt-and-grant.sql"
```

Logging de statements é desabilitado somente nessa sessão administrativa para evitar SQL de senha em erros; não se muda logging global. Conferir booleanas/nomes de roles, nunca hashes de pg_authid. Owner NOLOGIN; migrator NOINHERIT membro de owner; runtime sem memberships administrativos. Todos NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS.

## 7. Smoke tests da janela

| Área | Resultado obrigatório |
| --- | --- |
| Infraestrutura | Digests exatos, mesmo volume/redes, PostgreSQL 17.11/schema 1, três serviços healthy, migrate exit 0, sem novas portas |
| HTTP | `/api/health/ready` e `/healthz` 200; eventos sem sessão 401; `/metrics` público 404 |
| Sessão | Login existente, cookie Secure/HttpOnly, navegação e logout invalidando sessão, sem trace/vídeo/storageState com credentials |
| RBAC/CSRF/tenant | Viewer lê e recebe 403 na mutação; sem membership não acessa outro tenant; request de mutação sem CSRF negado. Preparar somente identidades sintéticas autorizadas; não alterar o único owner para simular viewer |
| SQL runtime | Login real por TCP; leitura e auditoria INSERT permitidas. DDL, TRUNCATE, mutação de audit/schema_migrations, SET ROLE e SUPERUSER negados 42501 em transações revertidas |
| Eventos/heartbeat | Fixture exclusiva `/fixtures/demo.conf`; backlog preservado, UUID replay sem duplicação, heartbeat aceito 202 e last_seen avançando após reconexão. Sem benchmark/seed genérico contra ativo |
| Auditoria/UI | Histórico preservado, ações sintéticas auditadas sem bearer/cookie/senha; páginas e navegação 390/768/1280 sem regressão impeditiva. Estados de falha simulados no browser/clone |
| Backup/Kuma | Backup pós-mudança íntegro/restaurável; monitor 20 readiness e 21 backup coerentes, pushes periódicos e canal confirmado |

Não executar suite E2E com seed contra ativo: ela pressupõe banco descartável e cria credenciais/entidades. Usar smoke dedicado com contas deste projeto por canal privado. Se não houver viewer/tenant sintéticos no ativo, registrar a pendência e preparar somente sob autorização da janela; os testes no clone já passaram, sem alegar que ocorreram no recurso ativo.

## 8. Rollback e pontos de parada

Gatilhos: readiness não estabiliza, regressão impeditiva, login/RBAC/CSRF falha, privilégio administrativo no HTTP, volume/schema inesperado, perda/duplicação de eventos, backup irrecuperável ou secrets em logs.

- **Antes de J2:** não modificar nada; RC1 continua como está.
- **Depois da drenagem, antes do deploy:** falha de backup/provisionamento interrompe a janela. Não recriar web/DB RC1 vulneráveis nem reverter para SUPERUSER. Se ainda não houver condições de usar o conjunto limpo, preservar dados e manter a aplicação parada enquanto se corrige; não assumir exceção para imagens bloqueadas.
- **Regressão da API:** manter web/DB endurecidos, roles restritas e migrator RC2; trocar somente API_IMAGE para o digest fallback do manifest. Usar mesmo recurso/Compose/custom commands/cache, sem pull/build. Repetir smoke/contagens/fila/backup; registrar aborto do RC2.
- **Falha do DB endurecido:** sem outra imagem PostgreSQL 17.11 limpa e ensaiada, manter volume preservado e aplicação parada para correção. Não voltar ao DB RC1 vulnerável, fazer downgrade ou substituir dados.
- **Dano aos dados/schema:** restaurar somente em volume isolado para diagnóstico. Restore sobre ativo, exclusão/perda de dados ou alteração destrutiva exige aprovação específica.

Schema permanece 1 e rollback não executa down migrations. Conservar eventos/ACKs e UUIDs coletados após promoção; nunca restaurar automaticamente snapshot antigo por cima deles. O botão genérico do Coolify pode recuperar Compose/admin DSN antigos e não é o procedimento aprovado.

## 9. Agente e monitoramento posteriores

**Agente ativo não atualizado.** Depois do aceite da central, requer autorização própria para o piloto frank-note2. Preservar config/token/allowlist e volumes `configsentinel-lab-config`, `configsentinel-lab-fixtures`, `configsentinel-lab-state`; snapshot SQLite consistente com DB/WAL/SHM antes da troca. Não copiar só SQLite ativo nem restaurar fila antiga sobre eventos novos. O agente atual usa bind de binário antigo: o novo container por digest precisa remover somente esse bind, ou continuará executando o RC1. Manter UID/GID 10001, read-only, cap_drop ALL, no-new-privileges, limites 160m/0.15 CPU/64 pids, sem socket/portas; somente `/fixtures/demo.conf`, hash_only=true, intervalo 5 s. Nunca executar dois agentes sobre a mesma fila. Fallback do agente exige scan próprio antes de uso.

**Kuma:** [kuma21-readonly.cjs](../scripts/kuma21-readonly.cjs) consulta somente monitor 21/histórico e nomes do canal em transação read-only, via socket local sem ler config/JWT/tokens. Não executar helpers antigos que acessam autenticação/notifier global. O teste de ausência de push usou o ramo exato do código instalado e relógio isolado: recente/599 s não derrubam, 601,001 s/ausência detectam falha, novo push recupera. O timer/serviço reais não foram pausados. A captura/declaração de Franklin comprova recebimento dos alertas anteriores; não foi versionada a imagem com conversas de terceiros. Não alegar um novo ensaio completo de notificação por silêncio real.

## 10. Validação final

[CI 41305147386](https://github.com/franklinlem/configsentinel/actions/runs/41305147386) passou em API, agente, web e segredos no commit `836d297`: race/vet/govulncheck, integração PostgreSQL, build/OpenAPI/npm audit, Playwright/axe e Gitleaks. [Resumo e limites](evidence/promotion/verification-summary.json). Os quatro testes locais adicionais do helper cobrem credencial em erro de login/pull, rejeição de repositório alheio e remoção de DOCKER_CONFIG temporário. Não se repetiram suites de aplicação após a mudança exclusiva de diagnóstico; o código da aplicação permanece o do candidato original.

## 11. Execução autorizada e decisão operacional — 01/11/2026

**NO-GO para aceite da homologação ativa. A central HTTP está indisponível.** Aplicado o ponto de parada da seção 8: API/web paradas; DB RC1 healthy, volume preservado. Nenhum restart com imagens vulneráveis, nenhuma troca de imagem/Compose/env, adoção de roles ou job de deploy foi executado. Última versão implantada continua RC1 `5819b7f`; RC2 não foi implantado. [Estado final](evidence/active-rc2-window/interrupted-final-state.json).

| Etapa | Resultado desta janela |
| --- | --- |
| J0 | PASS: autorização explícita, SHA de preparação aprovado fixado, branch operacional separada e ausência de deploy concorrente |
| J1 | PASS: workflow [41307377319](https://github.com/franklinlem/configsentinel/actions/runs/41307377319), headSha exato do SHA aprovado; cinco assinaturas/provenance/SBOMs e scans; quatro digests centrais presentes em linux/amd64; Coolify 4.5.3/Compose 5.6.1; volume/redes/proxy já conectados |
| J2 | PASS: snapshot exclusivo renovado AES256/0600, roundtrip e cópia criptografada offsite verificados; somente API/web paradas, baseline das 14 tabelas registrada |
| J3 | **FAIL**: backup final com checksum e GPG verificados; catálogo pg_restore legível, mas destino isolado não iniciou. **Restore efetivo não executado** |
| J4–J6 | Não executados: nenhuma nova role, configuração ou solicitação de deploy |
| J7 | Não executado: não existem smokes pós-deploy/aceite por 10 min/backup pós-RC2 nesta janela |
| J8 | Evidências e documentação da interrupção registradas; produção não autorizada |

Falha identificada: o harness operacional que preparei criou `empty-init` com permissões 0700 herdadas de umask 077. O processo PostgreSQL UID 70 não conseguiu ler o bind de `/docker-entrypoint-initdb.d`; container isolado encerrou com código 1. Não houve tentativa de pg_restore no alvo isolado nem no banco ativo. Isso é uma falha do ensaio, não comprova corrupção do dump ou regressão da imagem. Container/volume isolados e seus arquivos privados foram preservados. [Diagnóstico sanitizado](evidence/active-rc2-window/isolated-bootstrap-diagnostic.json).

Dados ativos: schema 1, quatro eventos e dois reconhecimentos iguais por conteúdo; contagens das 14 tabelas integralmente iguais à baseline drenada. Permanecem um usuário, três agentes e três tokens armazenados pela aplicação; nenhum token foi descartado. Metadados e mounts do piloto preservados, sem atualização da sua configuração, binário ou allowlist. A fila do agente não foi apagada nem inspecionada por alteração do SQLite.

Backup final: 2026-11-01T124248828081Z.dump.gpg, SHA-256 `97572b10c1de20ce0dfaa4e6ee9c580d51bb473ce8f0727067086857d31cdb71`; AES256/0600, em destino exclusivo no frank-note2. Checksum, decriptação GPG e catálogo PostgreSQL 17.11 passaram; **não declarar backup final restaurado**. Os restores anteriores continuam válidos somente para seus próprios dumps/ensaios. [Metadados](evidence/active-rc2-window/final-backup-encrypted.json), [diagnóstico do archive](evidence/active-rc2-window/final-backup-archive-readonly.json).

Kuma 20 passou a DOWN/503 após a drenagem, coerente com a central parada; Kuma 21 permaneceu UP com `backup verified`. Não se silenciou monitor nem alterou notificação. Não foi confirmada entrega humana de um alerta novo nesta janela; o recebimento humano comprovado anteriormente permanece evidência histórica. [Consulta 20/21](evidence/active-rc2-window/kuma-interrupted.json).

### Retomada preparada, não executada

1. Revisar esta interrupção e autorizar uma **nova janela**, mantendo o alvo e ambos os SHAs fixados. Não retomar automaticamente esta janela após um FAIL.
2. Corrigir apenas o harness: diretório vazio não sensível `empty-init` com modo 0755 explícito; diretório privado pai 0700 e envs 0600. Correção preparada localmente; **não aplicada nem retestada remotamente**. Usar destino/volume isolados novos, preservando o que falhou. [Registro da correção](evidence/active-rc2-window/prepared-harness-fix.json).
3. Revalidar assinaturas/scans/cache/versões/configuração; banco e aplicação precisam ter estado confirmado, sem reiniciar RC1 vulnerável. Renovar snapshot e baseline/backup final, pois o DB continua ativo e a fila do piloto pode acumular.
4. Provar restore real contra as 14 contagens e eventos/ACKs originais, antes de J4. Depois seguir J4–J8 sem alterar o procedimento de roles, imagens por digest e deploy único.
5. Fallback seguro continua preparado: somente API fallback limpa, web/DB endurecidos e migrator RC2, após todos os gates necessários. **Não foi acionado**; não é possível tratar o RC1 HTTP/banco histórico como rollback executável aprovado. Restore sobre volume ativo continua fora da autorização.

Não houve modificação de produção, outros projetos, Traefik, DNS, firewall ou agente. **Produção permanece NO-GO**. A central continua parada até nova decisão de recuperação/promoção autorizada.


## 12. Repetição limitada de J3 — interrompida antes do restore

Franklin autorizou exclusivamente a correção do harness e um novo restore isolado. O banco ativo foi consultado antes e depois: schema 1, todas as 14 contagens e conteúdo dos quatro eventos e dois reconhecimentos iguais à baseline; API/web continuam paradas e o banco saudável. A causa anterior foi reconfirmada: diretório vazio `empty-init` em modo 0700 e log do entrypoint com permissão negada.

O SHA-256 do backup final e seu arquivo de checksum passaram. A repetição **não chegou a criar o destino nem a executar GPG/pg_restore**: uma substituição textual no harness alterou o nome `POSTGRES_PASSWORD` e gerou Python inválido. A tentativa foi interrompida; não há duração de restore nem resultado de integridade restaurada a declarar. [Diagnóstico sanitizado](evidence/active-rc2-window/j3-retest/sanitized-log.json) e [estado ativo posterior](evidence/active-rc2-window/j3-retest/active-after.json).

Corrigi localmente a substituição para usar um marcador exclusivo e confirmei que o código gerado compila com valor fictício e mantém `POSTGRES_PASSWORD`. Essa verificação é apenas sintática: o harness corrigido **não foi executado novamente**, e diretório 0755, acesso do UID 70, decriptação e restore continuam sem validação nesta tentativa. J3 continua FAIL; J4–J8, deploy e produção não foram autorizados nesta etapa.

A próxima janela deve executar o restore em recursos novos e exclusivos, comparar as 14 tabelas e os registros originais, reconferir o banco ativo e só então, com autorização específica e gates revalidados, considerar J4–J8 conforme a seção 6. A central permanece indisponível até decisão operacional autorizada.


## 13. Restore isolado autorizado — J3 PASS

A repetição limitada restaurou efetivamente o backup final `2026-11-01T124248828081Z.dump.gpg`, SHA-256 `97572b10c1de20ce0dfaa4e6ee9c580d51bb473ce8f0727067086857d31cdb71`, no PostgreSQL 17.11 endurecido por digest. A decriptação ocorreu em streaming, sem arquivo de dump aberto; `pg_restore --exit-on-error` terminou com código 0. O streaming e restore duraram **3,479 s**; isso não mede o RTO total.

Foram comparados schema 1, contagens das 14 tabelas e conteúdo/identidade dos quatro eventos e dois reconhecimentos originais. O banco ativo, consultado somente em leitura antes e depois, e os IDs e estados dos containers ativos permaneceram iguais. API/web continuam paradas; banco ativo saudável. O teste não executou migrations ou roles no ativo.

O novo container e volume exclusivos usam rede interna sem portas, sem montar o volume ativo; `empty-init` vazio modo 0755 e seus pais visíveis foram acessíveis ao UID 70. As credenciais ficaram em arquivo 0600 e diretório 0700. A imagem e os recursos isolados estão identificados na [evidência](evidence/active-rc2-window/j3-authorized-restore/result.json); permanecem preservados. O container isolado segue em execução, sem portas públicas.

**J3 PASS para este backup e esta baseline.** A seção 11 registra o FAIL histórico da janela interrompida e a seção 12 a tentativa que não chegou ao restore. J4–J8 e o deploy não foram executados; a promoção ainda depende de autorização específica e reconferência de gates, estado e frescor do backup no momento da janela. Produção permanece NO-GO.


## 14. Retomada J4–J8 autorizada — interrompida em J5

**NO-GO: homologação indisponível; RC2 não implantado.** A autorização foi para o UUID `oi6lvzwzomwtbbgzf5uzofuh`, preparação `36baf66f4656f86d157cd070202323db9465c5f4` e imagens de `ea868efaa3e3b364d012981e597c8faf6bc30651`. API/web permanecem paradas desde 09:41:52 -03; banco ativo healthy. [Resumo e estado final](evidence/active-rc2-resume/summary.json).

Prechecks passaram: banco e restore isolado J3 coincidem nas 14 contagens e conteúdo de eventos/ACKs; schema 1, quatro eventos e dois reconhecimentos; snapshot de configuração decriptável, checksum/sidecar do backup, rede/volume/capacidade preservados. [Workflow 41309355528](https://github.com/franklinlem/configsentinel/actions/runs/41309355528) passou no SHA fixado com assinaturas, provenance, SBOMs e scans dos cinco digests e pull restrito; os quatro digests centrais foram inspecionados no cache. Não havia deploy concorrente.

**J4 PASS:** roles e grants foram aplicados em transação. As 14 contagens e eventos/ACKs não mudaram; runtime autenticou via TCP sem privilégios administrativos e dez operações proibidas receberam SQLSTATE 42501. [Evidência](evidence/active-rc2-resume/roles-adopted.json). As três roles novas permanecem no banco; não há rollback automático nem eliminação de roles.

**J5 FAIL:** o helper de configuração retornou saída que seu verificador não conseguiu interpretar como JSON. A causa precisa não foi estabelecida: a saída original não foi preservada; uma análise sintática posterior com dados fictícios não reproduziu o problema. A inspeção somente leitura confirmou source `main`/commit `5819b7f`, Compose RC1, três chaves de ambiente originais e auto-deploy desligado. Não repetir a operação automaticamente nem presumir que foi configurada. [Estado](evidence/active-rc2-resume/interrupted.json) e [diagnóstico limitado](evidence/active-rc2-resume/j5-syntax-diagnostic.json).

**J6/J7 não executados:** nenhuma solicitação de deploy, smoke pós-deploy, backup pós-mudança ou observação de aceite de 10 minutos. Kuma 20 DOWN/503 pela aplicação parada; Kuma 21 UP/backup verified na consulta de interrupção. Agente não foi atualizado. O fallback limpo continua assinado/cacheado e ensaiado em isolamento, mas não implantado; não reiniciar imagens RC1 vulneráveis ou aplicar rollback genérico.

Próxima ação proposta para revisão: reproduzir e corrigir o helper J5 em clone isolado ou transação comprovadamente revertida, preservando diagnóstico sanitizado e testando leitura/persistência das variáveis. Antes de nova janela, reconferir backup, estado e os privilégios J4 já aplicados; não reaplicar roles cegamente. Somente após autorização específica, configurar o UUID e seguir J6–J8 com um deploy manual por digest. Não executar restore sobre o banco ativo. Produção permanece não autorizada.


## 15. Diagnóstico e correção isolada de J5

**Resultado histórico: helper 6c79eb9 foi aprovado em isolamento; a aprovação foi suspensa após o FAIL ativo da seção 16.** O recurso ativo não foi alterado nesta revisão; J4 permanece aplicado, API/web continuam paradas e RC2 não foi implantado. A aprovação cobre o helper e os ensaios descritos, não constitui prova de um job completo do Coolify nem autoriza promoção.

O helper anterior estava em `.local/resume-configure.py`: `echo json_encode(...)` ocorria dentro da transação PHP; o Python em `.local/window-lib.py` retornava somente stdout e chamava `json.loads` sobre todo o conteúdo. Uma saída não JSON causava exceção sem preservar a resposta, código de saída e classificação. Isso explica a **causa raiz da perda do diagnóstico** e o mecanismo do erro de parse. Como os bytes da resposta real não foram conservados, **não é possível identificar se aquela saída veio de aviso, exceção ou outra fonte**. O teste sintático anterior passou; não se afirma uma causa específica sem evidência.

O helper versionado agora separa código PHP fixo de JSON no stdin e retorna um envelope explícito somente após a transação. [Cliente](../scripts/j5_client.py), [protocolo](../scripts/j5_protocol.py), [entrada PHP](../scripts/j5_coolify_entry.php) e [transação](../scripts/j5_coolify_transaction.php) não interpolam dados sensíveis em código ou shell. Falhas registram somente categoria, código e tamanhos; stdout/stderr, SQL, envs e mensagens arbitrárias não são publicados. O código SSH 255 é tratado como falha de transporte **ou processo remoto**, pois não permite distingui-los com certeza. Saída extra, UTF-8 inválido, JSON vazio/truncado, formatos inesperados, timeout, falha de processo e dados extras são rejeitados. Em caso de resposta ambígua após chamada futura, consultar o estado em leitura e parar, sem retry automático, pois o commit pode ter ocorrido antes da perda da resposta.

A transação fixa UUID, SHA, Compose, quatro digests aprovados, comandos e flags; compara a senha PostgreSQL existente sem revelá-la, rejeita drift e duplicatas e mantém runtime/migrator distintos. Usa `saveQuietly` para evitar callbacks que criariam automaticamente variáveis de preview ou efeitos laterais; somente variáveis runtime do recurso são alteradas. O ensaio com os modelos Coolify instalados e SQLite `:memory:` verificou criptografia/descriptografia, falha injetada com rollback integral e segunda execução idempotente; um digest incorreto foi rejeitado. Os testes não simulam todas as particularidades do banco MySQL de metadados nem um job completo de deploy.

O serializer instalado e o Compose foram testados com valores sintéticos, inclusive cifrão, aspas e `#`. `docker compose config` representa cifrão como `$$`, mas um container sintético sem rede confirmou que o valor efetivamente recebido coincide com o original. Compose, redes externas e volume esperados foram conferidos, sem portas nem build. Foram executados 18 testes operacionais: 16 passaram e 2 de integração PostgreSQL foram ignorados por ausência do container de teste; os testes J4 reais já estavam documentados separadamente. [Resultados e hashes](evidence/j5-isolated/probe.json), [preservação do ativo](evidence/j5-isolated/active-preservation.json).

Antes de qualquer próxima tentativa ativa: revalidar assinaturas/scans/cache, snapshot e backup, estado das roles já aplicadas, volume/redes, fila de deploy e SHA fixado; executar apenas após nova autorização e manter o limite de uma janela controlada. J6–J8 e produção continuam não autorizados.


## 16. Tentativa específica de J5 — FAIL

A autorização de Franklin cobriu uma única chamada do helper `6c79eb9`, exclusivamente ao recurso `oi6lvzwzomwtbbgzf5uzofuh`, sem J6–J8. Gates passaram: SHA de preparação e do código fixados, hashes dos helpers/manifests, backup/restore J3 correspondente à baseline, snapshot criptografado, 14 tabelas e registros originais, roles/ownership e matriz de grants J4, runtime TCP, redes/volume/capacidade e ausência de deploy concorrente. A renderização privada anterior à chamada confirmou quatro imagens, DSNs, volume/redes e ausência de portas/build. O [workflow 41311042013](https://github.com/franklinlem/configsentinel/actions/runs/41311042013) verificou assinaturas, SBOMs, provenance, scans atuais e pull restrito; os quatro digests centrais estavam no cache.

**J5 FAIL:** a única chamada retornou envelope sanitizado `internal_error`, código 2, 68 bytes em stdout e stderr vazio. A categoria não identifica a causa específica; não se presume um problema de sintaxe, banco ou transporte. Não houve repetição. [Resposta sanitizada](evidence/j5-active-attempt/helper-response.json).

A inspeção independente em leitura comparou commit, branch, Compose, comandos customizados e valores das variáveis com o snapshot anterior: **iguais**, sem configuração parcial observada. Permanecem somente as três variáveis originais; as sete previstas não foram persistidas, portanto não existe renderização pós-persistência a aprovar. Banco preserva baseline, API/web paradas, PostgreSQL saudável e fila de deploy vazia. Roles J4 permaneceram aplicadas sem reaplicação. [Estado](evidence/j5-active-attempt/independent-state.json).

J6/J7/J8 operacionais e deploy não foram executados. O fallback limpo não foi acionado; não usar rollback genérico nem reiniciar imagens vulneráveis. O helper aprovado em isolamento na seção 15 **não está aprovado para nova chamada ativa após este FAIL**, até diagnóstico e revisão específicos. Produção continua NO-GO.


## 17. Investigação diagnóstica de J5 — causa ativa ainda não comprovada

**Recomendação: NO-GO para nova tentativa ativa.** O único J5 ativo continuou sem repetição, e a resposta preservada não contém fase nem classe de exceção. Os 68 bytes, código 2 e stderr vazio comprovam apenas a categoria `internal_error`; não identificam sua origem. Leituras posteriores confirmaram que recurso, envs, dados, roles e containers permanecem no estado documentado em 8de6581.

No PHP/Laravel instalado, a medição somente de metadados retornou `ob_get_level=0` antes de abrir o buffer, nível 1/tamanho 0 depois de `ob_start` e nível 1/tamanho 0 após bootstrap. No clone com a **mesma imagem Coolify 4.5.3 e PostgreSQL 15**, o caminho original do entrypoint com payload sintético passou, e sua segunda execução foi idempotente. O esquema de metadados é parcial/sintético, não uma cópia integral do banco ativo.

No mesmo clone, 27 bytes sintéticos injetados no buffer durante a transação produziram `internal_error` e rollback integral; com buffer limpo, mudança e idempotência passaram. Também foram reproduzidos aviso PHP e exceção de banco que o código anterior mascarava com a mesma categoria. **Buffer contaminado é uma hipótese possível, não uma causa comprovada da falha ativa**; warning, erro de banco ou outro Throwable continuam possíveis. Nenhum conteúdo de buffer, SQL, segredo ou stdout/stderr bruto foi registrado.

Correção limitada ao defeito comprovado de observabilidade: [entrypoint](../scripts/j5_coolify_entry.php), [transação](../scripts/j5_coolify_transaction.php) e [protocolo](../scripts/j5_protocol.py) agora usam envelope versão 2, com fase e tipo obtidos de listas fechadas, preservando categoria, código e tamanhos sem mensagens arbitrárias. A verificação de saída inesperada e o rollback continuam ativos. Falhas na fase de resposta após commit continuam potencialmente ambíguas: consultar estado somente leitura e interromper, sem retry automático. O cliente e o helper devem ser revisados e utilizados juntos na mesma revisão; o contrato v1 é rejeitado. A mudança **não comprova correção da falha operacional anterior**.

O PostgreSQL sintético usa rede interna exclusiva, sem portas, dados em tmpfs e chave/credenciais sintéticas próprias; seu container e rede permanecem preservados. O teste de ponta a ponta validou entrypoint, idempotência, erro de banco com fase/tipo sanitizados e rollback com ruído injetado. Suite operacional: 21 testes, 19 passaram e 2 PostgreSQL de J4 foram ignorados sem container de integração configurado. [Diagnóstico e logs sanitizados](evidence/j5-diagnostic/diagnostic.json), [estado ativo](evidence/j5-diagnostic/active-preservation.json). Não foram executados J5 ativo, J6–J8 ou deploy. Produção permanece NO-GO.

## 18. Clone J5 — Fase 1 totalmente sintética

Em 02/11/2026, o [ensaio da Fase 1](J5_SYNTHETIC_PHASE1.md) terminou em **PASS**: 14 cenários PostgreSQL e 11 testes do protocolo; oracle SQLite do helper operacional também passou. Imagens aprovadas, Eloquent real da imagem Coolify 4.5.3, credenciais fictícias, rede exclusiva com gateway isolado, 228 conexões negativas bloqueadas, DNS externo bloqueado e ausência de rota padrão nos dois containers. Recursos criados permanecem preservados, sem cleanup. [Resultado e inventário](evidence/j5-synthetic-phase1/result.json).

O helper operacional não mudou; apenas uma cópia de teste teve dois tokens de escopo adaptados. Falhas iniciais de transferência, permissões e diretórios de cache do próprio harness foram corrigidas no clone e estão documentadas. Nenhum registro/credencial de banco ativo foi lido; o estado operacional atual não foi reconfirmado nesta fase. Não houve J5 ativo, J6–J8, deploy ou mudança em serviços existentes. A causa histórica continua desconhecida. Fase 2, leitura de metadados reais e limpeza requerem autorização específica. **J5 ativo e produção continuam NO-GO.**
