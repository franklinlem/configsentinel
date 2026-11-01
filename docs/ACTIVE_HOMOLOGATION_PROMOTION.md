# ConfigSentinel RC2 — procedimento de homologação ativa

Atualizado em **01/11/2026, America/Sao_Paulo**. Branch `plan/active-homologation-rc2`.

**Preparação autorizada e executada em isolamento/leitura. A janela ativa NÃO está autorizada.** Nenhum deploy, stop/restart, nova role ou variável foi aplicado ao recurso ativo. Produção permanece NO-GO. Os PASS abaixo têm o escopo e os limites descritos; exigem reconferência na janela, não constituem autorização de promoção.

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
| G0 — janela ativa | **PENDENTE** | Franklin autorizou somente preparação isolada/leitura. Falta autorização específica da janela, SHA final, responsável e aceite dos limites abaixo |
| G1 — autenticidade/pull | **PASS** | [Workflow read-only](https://github.com/franklinlem/configsentinel/actions/runs/41259950111), [resultados](evidence/promotion/readonly-pull-results.json): cinco digests, assinatura direta, provenance, SBOM e scans verificados online. Token reportado pelo GitHub: contents/read, metadata/read, packages/read. Nenhum deploy |
| G2 — fallback limpo | **PASS** | [Build assinado](https://github.com/franklinlem/configsentinel/actions/runs/41259750008), [manifest](../deploy/release-manifest.fallback.json), [ensaio](evidence/promotion/isolated-promotion-rehearsal.json): RC2 → fallback → RC2; login/RBAC/CSRF/eventos/replay/heartbeat/auditoria passaram |
| G3 — recuperação preparada | **PASS** | [Snapshot criptografado](evidence/promotion/config-snapshot.json), [backup novo/restore](evidence/promotion/fresh-isolated-backup.json), [backup regular atual](evidence/promotion/backup-health-final.json). Backup final com escritores drenados continua obrigatório **na janela autorizada** |
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

## 10. Decisão operacional

**Prechecks concluídos no escopo autorizado; janela ativa PENDENTE em G0.** [Inspeção final](evidence/promotion/active-preservation-final.json): mesmos containers/imagens RC1, start em 31/10, healthy, 4 eventos/2 reconhecimentos/1 usuário, novas roles ausentes, mesma branch/Compose e auto-deploy desabilitado. Sem mudança do piloto, Traefik, DNS, firewall, portas ou produção.

Aguardar autorização específica de Franklin para a janela descrita, com SHA final e aceite dos limites dos ensaios. Antes da parada, reconferir os gates e renovar snapshot/backup conforme J1–J3. Produção permanece **NO-GO** e fora desta autorização.
