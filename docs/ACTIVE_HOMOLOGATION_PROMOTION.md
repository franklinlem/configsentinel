# ConfigSentinel RC2 — promoção controlada da homologação ativa

**Status: PLANO PARA AUTORIZAÇÃO; nenhuma promoção executada.** Revisão em 31/10/2026, 21:51–21:57 America/Sao_Paulo (01/11, 00:51–00:57 UTC). Branch de preparação: `plan/active-homologation-rc2`, baseada em `9825fb7`. A autorização futura abrangerá somente o recurso abaixo. Produção continua NO-GO.

## 1. Alvo, artefatos e limites

| Item | Valor obrigatório |
| --- | --- |
| Recurso Coolify existente | `oi6lvzwzomwtbbgzf5uzofuh`, Docker Compose, Contabo |
| URL preservada | `https://configsentinel-dev.franklem.uk` |
| Estado atual confirmado | RC1, commit `5819b7fce93c10cceabbe59fde5fac4f647b707c`, branch `main`, deploy automático desabilitado |
| Compose atual | `/deploy/compose.coolify.yml`; arquivo gerado no host: `/data/coolify/applications/oi6lvzwzomwtbbgzf5uzofuh/docker-compose.yaml` |
| Compose preparado | [compose.active-homologation.yml](../deploy/compose.active-homologation.yml), ainda não aplicado |
| Dados obrigatoriamente reutilizados | volume externo `oi6lvzwzomwtbbgzf5uzofuh_postgres_data`, destino `/var/lib/postgresql/data` |
| Redes existentes | `oi6lvzwzomwtbbgzf5uzofuh_database` (interna), `oi6lvzwzomwtbbgzf5uzofuh_app`, `coolify` |
| Código das imagens RC2 | `ea868efaa3e3b364d012981e597c8faf6bc30651`, linux/amd64 |
| Manifest de referência | [release-manifest.candidate.json](../deploy/release-manifest.candidate.json), `v0.1.0-rc.2-review` |

Fixar separadamente o SHA final desta preparação, que contém o Compose, e o SHA do código das imagens. Selecionar o commit de preparação explicitamente no recurso; não trocar imagens por tags nem reconstruir durante a promoção. Não alterar `main` para provocar deploy. `production_approved`, `candidate_review_approved` e `active_homologation_promoted` permanecem falsos nesta preparação.

Não criar recursos de produção, previews ou projetos. Não modificar DNS, firewall, Traefik, logins Docker compartilhados ou serviços alheios. As labels de roteamento preparadas são idênticas às labels atuais. Não publicar portas. Não executar `down`, `down -v`, prune, truncate, revoke de tokens ou restore sobre dados ativos. Não usar os scripts de instalação inicial do piloto para atualizá-lo: eles copiam configuração/token/fixture e não são um upgrade preservador.

## 2. Conferências realizadas nesta preparação

| Precheck somente leitura | Evidência e resultado |
| --- | --- |
| Recurso ativo e banco | [active-precheck.json](evidence/promotion/active-precheck.json): três containers healthy; PostgreSQL 17.11, schema 1, 4 eventos, 2 reconhecimentos, 1 usuário; novas roles ainda ausentes |
| Digests e código | [image-rescan.json](evidence/promotion/image-rescan.json): quatro referências no cache da VPS, RepoDigests exatos, linux/amd64 e revision correspondentes ao manifest |
| Scans repetidos | Trivy 0.76.1 sobre exports das quatro imagens exatas, sem executar seus containers: zero HIGH/CRITICAL; API mantém 1 UNKNOWN, GO-2026-5932; demais zero. Base atualizada em 31/10 às 13:09 UTC, próxima atualização indicada em 01/11 às 13:09 UTC. Não se forçou atualização nem se suprimiu CVE |
| SBOM e provenance | [artifact-recheck.json](evidence/promotion/artifact-recheck.json): oito assinaturas DSSE verificadas novamente com OpenSSL/ECDSA e a chave pública fixada; subjects/digests, commit e quatro checksums conferem; predicates SBOM idênticos aos arquivos versionados |
| Assinatura direta da imagem no registry | Cosign passou no workflow [41253986413](https://github.com/franklinlem/configsentinel/actions/runs/41253986413). A nova verificação online ainda depende da credencial de leitura; JSON de claims decodificados não substitui nova verificação criptográfica dessa assinatura |
| Recuperação RC1 | [recovery-precheck.json](evidence/promotion/recovery-precheck.json): três archives 0600 com SHA-256 novamente conferido. API RC1 reescaneada: zero HIGH/CRITICAL, 1 UNKNOWN; web/DB históricos vulneráveis não podem ser redeployados |
| Backup | [backup-agent-precheck.json](evidence/promotion/backup-agent-precheck.json): último sucesso 31/10 19:02:27 UTC, idade aproximadamente 5h50, checksum e decriptação para `/dev/null` válidos; dois backups diários preservados; serviços com Result=success, timers ativos |
| Restore histórico recente | [homologation-rollback.json](evidence/remediation/homologation-rollback.json): restore isolado schema 1, 4 eventos, 2 reconhecimentos. Não foi repetido restore nem iniciado container remoto nesta preparação |
| Compose | [compose-precheck.json](evidence/promotion/compose-precheck.json): renderização local com senhas fictícias; sem build/ports; volume/redes externos explícitos; runtime/migrator separados; API/migrate sem ADMIN_PASSWORD; labels Traefik iguais às atuais |
| Kuma 21 | Quatro execuções recentes do monitor exclusivo retornaram status=ok e push aceito, aproximadamente a cada 5 min. Badge pública retornou N/A. Não foi consultado banco, JWT ou configuração global de notificações do Kuma |
| Piloto | Somente `/fixtures/demo.conf`, hash_only=true, UID 10001, rootfs read-only, cap_drop ALL e volumes atuais confirmados; binário antigo montado por bind, sem atualização |

A conferência de Compose acima não valida ainda a renderização pelo parser do Coolify com os segredos reais. Não foi criada credencial GHCR permanente nem mudada variável protegida. A suite completa verde do candidato permanece documentada em [validation.md](validation.md) e [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md); não foi repetida como se este plano fosse uma nova versão da aplicação.

## 3. Gates antes de qualquer parada

Todos os gates devem estar registrados como PASS; falha ou dúvida interrompe a promoção mantendo o RC1 ativo.

1. **G0 — autorização explícita:** Franklin aprova este plano e uma janela de indisponibilidade restrita ao ConfigSentinel; agente piloto fica para etapa posterior. Registrar operador, hora, SHA de preparação e manifest/checksum aprovados.
2. **G1 — autenticidade e pull:** credencial somente leitura testada, quatro digests acessíveis, assinaturas diretas/SBOM/provenance verificadas novamente, scan sem HIGH/CRITICAL com base dentro da validade indicada e sem ignores. Se houver novo achado bloqueador, parar e abrir novo candidato.
3. **G2 — fallback limpo:** publicar/assinar/escanear uma imagem de API compatível com RC1 por digest e ensaiá-la com web/DB endurecidos do RC2, runtime restrito e schema 1. A API RC1 preservada é a origem proposta, não um fallback já publicado/aprovado. Gerar manifest de rollback separado e testar login, RBAC, eventos e auditoria. Não reutilizar o ensaio antigo de rollback total: ele incluiu web/DB RC1 hoje proibidos pela restrição de vulnerabilidades.
4. **G3 — recuperação:** snapshot protegido da configuração exclusiva deste recurso e novo backup criptografado pré-mudança, com checksum/decriptação e restore isolado na imagem DB RC2. Não iniciar teste com `scripts/restore-test.sh` sem adaptação: ele usa tag PostgreSQL mutável. Registrar schema/contagens e duração. Não remover recovery points existentes.
5. **G4 — persistência e Compose:** parser do Coolify preserva exatamente o nome do projeto, volume e redes; comparar labels, mounts, secrets e imagens antes de iniciar. Banco deve ser 17.11/schema 1 e ter usuários existentes. Volume ausente, banco vazio ou versão diferente é parada obrigatória; nunca permitir bootstrap de banco substituto.
6. **G5 — operação (parcialmente atendido):** recebimento humano dos alertas DOWN/UP e da mensagem de teste confirmado por Franklin, com captura de tela; [registro sanitizado](evidence/promotion/alert-receipt-confirmation.json). Ainda conferir estado/configuração atual do monitor 21 por acesso limitado a esse monitor ou conferência de Franklin. Teste de ausência de push por 10 min permanece pendente e deve ser feito em janela própria, antes da parada da central, com recuperação confirmada.
7. **G6 — credenciais e ensaio:** segredos gerados e protegidos, provisionamento transacional e rollback limpo ensaiados no clone; funcionamento dos comandos customizados da versão instalada do Coolify confirmado antes de autorizar deploy ativo. Recurso confirmado em raw Compose, sem build server; atualmente Docker Compose 5.6.1. O suporte observado no código do Coolify não substitui ensaio do caminho real.

**Estado atual: G0/G1/G2/G3/G4/G5/G6 ainda têm partes pendentes; NO-GO para iniciar a promoção agora.** Isso não reabre produção nem autoriza operações de risco adicionais. Se não houver fallback limpo de DB 17.11, falha da nova imagem do banco exige manter os dados parados e corrigir a imagem; não voltar automaticamente ao PostgreSQL RC1 vulnerável.

## 4. GHCR somente leitura sem interferir em outros projetos

A [documentação GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) prevê PAT classic `read:packages` ou GITHUB_TOKEN de workflow com acesso ao pacote. A [documentação Coolify](https://coolify.io/docs/applications/builds/docker-registries) informa que o login padrão fica no Docker config do usuário do servidor: ele é compartilhado e não será sobrescrito neste procedimento.

**Caminho preferido:** preparar um workflow manual exclusivo de pull, com `permissions: {contents: read, packages: read}` no job; usar os secrets SSH exclusivos já existentes e `scripts/request-registry-pull.py`. Materializar os quatro `image.json` do manifest em `.local/registry/<componente>/image.json` somente após verificar assinaturas/scans. O forced-command existente valida os quatro repositórios/digests, recebe o GITHUB_TOKEN pelo stdin do SSH e faz login em DOCKER_CONFIG temporário 0700, apagado ao final. Não reutilizar o workflow de build com `packages: write` como prova de pull somente leitura. Esse novo workflow não foi criado/disparado nesta etapa: implementação e execução são precheck após autorização, antes de tocar no recurso ativo.

Se for exigida credencial duradoura, usar identidade dedicada com leitura somente dos quatro pacotes ConfigSentinel, PAT classic apenas `read:packages`, expiração e rotação definidas. Não usar PAT pessoal amplo, token de assinatura, write/delete/repo ou credenciais de outros projetos. A criação de identidade/token e sua entrega segura continuam pendentes; nenhum valor deve entrar em chat, relatório, YAML, CLI com argumento, log ou git.

Forma de login para a alternativa duradoura, em ambiente privado exclusivo e sem `set -x`:

```bash
# Somente após G0; GHCR_PULL_TOKEN_FILE é arquivo 0600 provisionado por canal seguro.
umask 077
export DOCKER_CONFIG="$(mktemp -d /tmp/configsentinel-pull.XXXXXXXX)"
docker login ghcr.io --username "$GHCR_PULL_USER" --password-stdin < "$GHCR_PULL_TOKEN_FILE"
# Ler os digests do manifest e fazer pull/verify com esse DOCKER_CONFIG.
# Ao terminar, apagar somente o diretório temporário criado nesta sessão.
```

Não executar `docker login/logout` no config padrão nem copiar config de autenticação para diretórios de outros serviços. Para o Coolify operar a partir do cache já verificado, configurar **somente neste recurso** custom build sem build (inspeção das imagens) e custom start com `--pull never --no-build`. O código instalado possui caminho que pula o pull automático quando há custom build e não há build server; confirmar essa condição no recurso e ensaiá-la. Se essa condição não funcionar, parar antes do deploy; não contornar com login global.

## 5. Preparação e verificações executáveis

Os comandos abaixo são roteiro para execução **após autorização**, com fail-fast, sem shell tracing. Segredos e saída completa de Compose permanecem em diretório privado exclusivo, fora de Git. Placeholders e artefatos pendentes não podem ser tratados como passos já concluídos.

### Artefatos e assinatura

```bash
# Workstation/runner exclusivo, já autenticado com packages:read; ferramentas fixadas.
set -euo pipefail
umask 077
mkdir -p .local/promotion-approval
for component in api web db agent; do
  ref=$(jq -er --arg c "$component" '.[$c].image' deploy/release-manifest.candidate.json)
  expected=$(jq -er --arg c "$component" '.[$c].sbom_sha256' deploy/release-manifest.candidate.json)
  printf '%s  %s\n' "$expected" "docs/evidence/remediation/$component-sbom.cdx.json" | sha256sum --check
  .local/remediation/cosign verify --key deploy/release-signing.pub --insecure-ignore-tlog "$ref" > ".local/promotion-approval/$component-signature.json"
  .local/remediation/cosign verify-attestation --key deploy/release-signing.pub --insecure-ignore-tlog --type slsaprovenance1 "$ref" > ".local/promotion-approval/$component-provenance.json"
  .local/remediation/cosign verify-attestation --key deploy/release-signing.pub --insecure-ignore-tlog --type cyclonedx "$ref" > ".local/promotion-approval/$component-sbom-proof.json"
  .local/readiness/tools/trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 "$ref" > ".local/promotion-approval/$component-scan.txt"
done
```

Além do exit code, decodificar as atestações verificadas: subject deve ser o digest/repositório esperado; externalParameters deve conter commit `ea868ef...`, componente e plataforma esperados; predicate SBOM deve ser idêntico ao SBOM cujo SHA foi conferido. Verificar assinatura do próprio digest, não apenas a booleana do manifest. A política usa chave autogerenciada fixada, sem Rekor: `--insecure-ignore-tlog` dispensa transparência, não dispensa a assinatura. Não há identidade OIDC garantida por essa política.

### Variáveis e renderização protegida

Variáveis exigidas no recurso: `CONFIGSENTINEL_{API,WEB,DB}_IMAGE` com os digests aprovados; `POSTGRES_PASSWORD` existente, sem rotação; novas `RUNTIME_DB_PASSWORD` e `MIGRATOR_DB_PASSWORD`, distintas, aleatórias, pelo menos 32 bytes, representadas em hexadecimal para DSNs. Fixar PUBLIC_URL e COOKIE_SECURE no Compose. Não injetar ADMIN_PASSWORD/ADMIN_EMAIL no HTTP ou no migrator deste banco já inicializado. Manter senha administrativa somente no DB. Não mudar o token do piloto.

A [inspeção de metadados](evidence/promotion/protected-variable-metadata.json) confirmou ADMIN_EMAIL, ADMIN_PASSWORD e POSTGRES_PASSWORD atuais como runtime, sem build e com is_literal=true, sem ler seus valores. As novas variáveis ainda não existem. Preservar is_literal para os segredos e desabilitar qualquer envio ao build. A renderização deverá confirmar presença e tipo dos valores sem imprimi-los, senhas distintas, ausência de CR/LF e sem substituição inesperada de `$` no segredo existente. Não executar `source` de arquivo de secrets. Variáveis de runtime não são build args. Não colocar GHCR_TOKEN no ambiente dos serviços. O Docker/Coolify armazena variáveis runtime acessíveis ao operador do host; isto não oferece proteção contra administrador comprometido.

```bash
# Workstation, arquivo privado provisionado após autorização; não mostrar o JSON gerado.
docker compose --env-file .local/promotion-approval/active.env \
  --project-name oi6lvzwzomwtbbgzf5uzofuh \
  -f deploy/compose.active-homologation.yml config --format json \
  > .local/promotion-approval/compose.rendered.json
```

Comparar esse JSON com a renderização pelo Coolify antes da execução. Exigir: quatro serviços, nenhuma porta/build, external volume com nome exato, redes externas existentes e database interna já confirmada, mesma URL/labels, migrate one-shot sem restart, dependência `service_completed_successfully`, HTTP somente runtime e readiness. Conferir logs de validação sanitizados. O helper `check-release-manifest.py` é gate de **produção** e continua retornando NO-GO: nunca alterar `production_approved` para satisfazê-lo na homologação.

Snapshot de recuperação: após G0 e antes de editar qualquer campo, copiar somente Compose/variáveis/settings deste UUID para arquivo criptografado 0600 com chave exclusiva ConfigSentinel, registrar SHA e localização privada. Não exportar configurações globais do Coolify nem registrar valores de env. Guardar também lista de labels, volume, redes, digests e settings customizados anteriores. Esses arquivos conterão credenciais e não serão anexados ao relatório.

## 6. Sequência da janela autorizada

1. **Precarregar e parar no gate:** concluir G1/G2/G4/G5/G6 com RC1 ainda em execução. Conferir espaço em disco para imagens/snapshot e capacidade do banco; não fazer limpeza automática. Confirmar zero deployment em andamento deste UUID e impedir operações manuais concorrentes. Deploy automático permanece desligado.
2. **Drenar a aplicação:** parar somente API e web ConfigSentinel, preservando o DB. Não parar nem recriar o agente: ele mantém a fila durante a indisponibilidade. Como o piloto ainda é RC1, seu heartbeat pode ficar atrasado durante falha de ingestão; não confundir isso com teste do worker corrigido. Esperar encerramento das transações, registrar contagens de todas as 14 tabelas e versão, sem conteúdo/credenciais. Verificar que o timer de retenção da API também terminou.
3. **Backup final consistente:** com escritores parados, executar o serviço exclusivo de backup e validar checksum, decriptação, restore em DB RC2 isolado e contagens da baseline. O lock evita concorrência com o timer; lock ocupado/timeout/falha implica parada, não remover lock para forçar. Manter todos os pontos anteriores. O serviço conserva sua política de retenção; se a execução implicar remoção de um backup existente, usar snapshot adicional sem retenção e obter aprovação específica antes de qualquer exclusão. Não relaxar checagem por backup ainda ter menos de 26 h: o backup da janela é obrigatório.
4. **Provisionar roles atomicamente no DB existente:** usar somente administrador dedicado `configsentinel`, via socket do container, com arquivo de senhas 0600 exclusivo. Confirmar que não há memberships indiretos inesperados. Adotar propriedade e grants numa transação; aplicar lock_timeout=5s e statement_timeout=60s. Timeout/erro => rollback da transação e parada. Não dropar schema/tabela/role ou reinicializar volume.
5. **Persistir configuração preparada do mesmo recurso:** no Coolify, selecionar a branch/commit de preparação revisado e `/deploy/compose.active-homologation.yml`, adicionar secrets protegidos e digests, custom build/start revisados abaixo. Não salvar/acionar antes de passar os gates. O SHA exato de preparação deverá constar na autorização operacional; não usar HEAD móvel.
6. **Executar um deploy manual desse UUID:** o DB muda somente para o digest RC2 PostgreSQL 17.11, sobre o volume existente. Esperar pg_isready e versão 17.11; migrate usa migrator, valida banco existente, mantém schema 1 e aplica grants; HTTP inicia com runtime; web inicia após readiness. Não aceitar migração com bootstrap, recriação de usuários ou versão inesperada. Não usar botão de rollback genérico do Coolify, que pode restaurar Compose vulnerável/admin DSN.
7. **Validar imediatamente:** verificar digests/volume/redes/sem portas, logs sanitizados, schema/permissões e smoke tests abaixo. Prazo inicial: readiness em até 150 s após DB saudável; duas falhas consecutivas ou qualquer violação de integridade/permissão interrompe o aceite e aciona o procedimento de recuperação. Não executar retries de deploy indefinidamente.
8. **Aceite e observação:** duas passagens completas de smoke, acompanhar heartbeat do piloto e fila voltando ao baseline, auditoria, backup pós-mudança/restore e dois ciclos de monitoramento (pelo menos 10 min). Registrar indisponibilidade/RPO/RTO observados, sem prometer SLA. Atualizar evidências/manifest apenas com fatos confirmados. Não marcar produção aprovada.

Comandos de drenagem, somente após G0 e gates preliminares:

```bash
ssh contabo docker stop --time 30 oi6lvzwzomwtbbgzf5uzofuh-api-1 oi6lvzwzomwtbbgzf5uzofuh-web-1
```

Comando transacional no host Contabo, em checkout protegido exclusivo do ConfigSentinel. O arquivo `roles.env` contém somente `CONFIGSENTINEL_RUNTIME_PASSWORD` e `CONFIGSENTINEL_MIGRATOR_PASSWORD`, com os mesmos valores dos campos protegidos. Desabilitar logging de statements apenas nesta sessão administrativa para evitar registrar SQL de senha; não mudar logging global. Evitar eco/psql history e registrar somente exit code. `roles-adopt-and-grant.sql` deve ser composto, sem secrets, por `db/roles/provision.sql`, `SET ROLE configsentinel_owner;` e `db/roles/runtime-grants.sql`, com checksums conferidos.

```bash
# Executar no host Contabo, não em outro banco.
docker exec -i --env-file "$CONFIGSENTINEL_PRIVATE_DIR/roles.env" \
  -e 'PGOPTIONS=-c lock_timeout=5s -c statement_timeout=60s -c log_statement=none -c log_min_error_statement=panic' \
  oi6lvzwzomwtbbgzf5uzofuh-db-1 \
  psql -X --single-transaction -v ON_ERROR_STOP=1 -U configsentinel -d configsentinel -f - \
  < "$CONFIGSENTINEL_PRIVATE_DIR/roles-adopt-and-grant.sql"
```

Inspecionar somente booleanas/nomes de role, nunca pg_authid/passwords. Owner NOLOGIN; migrator LOGIN NOINHERIT membro de owner; runtime LOGIN NOINHERIT sem memberships administrativos; todos NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS. Confirmar ownership das 14 tabelas, grants e versão antes de iniciar HTTP.

Custom build proposto para este recurso: `docker image inspect` seguido das **três referências literais aprovadas API/web/DB**, com stdout redirecionado a `/dev/null`. Não usar `build`, `pull`, comandos de limpeza ou secrets nessa string. Conferir as três referências contra o manifest. O start command proposto é:

```bash
docker compose --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build
```

O Coolify injeta `--project-directory`, `-f` e `--env-file`; validar a string final gerada na versão instalada. Não executar esse comando manualmente em paralelo ao Coolify. O parser deve respeitar volume/redes externos e o migrate one-shot antes de HTTP. Se os hooks não forem reproduzíveis no ensaio, parar em G6 e revisar o plano, preservando o RC1 ativo.

## 7. Smoke tests e critérios de aceite

| Área | Procedimento/resultado obrigatório |
| --- | --- |
| Readiness e exposição | GET `/api/health/ready` 200; GET `/healthz` 200; `/api/v1/events` sem sessão 401; `/metrics` público 404; sem novas portas; três serviços healthy e migrate exit 0 |
| Imutabilidade/persistência | Inspecionar referências/RepoDigests reais, revision e volume nomeado exato; PG 17.11/schema 1; baseline das 14 tabelas preservada antes de reabrir tráfego e sem exclusões inesperadas depois |
| Login/sessão | Login com conta existente por canal privado, navegação funcional, cookie Secure/HttpOnly/SameSite esperado, logout invalida sessão. Sem captura de requests, traces, vídeos ou storageState com cookies |
| RBAC/tenant | Conta viewer de teste restrita: leituras permitidas, mutação negada 403; conta sem membership não lê IDs de tenant alheio. Preparar identidades/IDs exclusivamente sintéticos no clone antes da janela; se não houver essas identidades no ativo, registrar etapa pendente e preparar contas sintéticas autorizadas sem alterar role do único owner existente |
| CSRF | Mutation com sessão sem CSRF/origin inválida deve ser negada; mutation legítima funciona. Usar somente entidades sintéticas e conservar registros de auditoria |
| SQL runtime | Conectar de verdade como runtime via DSN protegido; SELECT e auditoria INSERT permitidos. CREATE TABLE/SCHEMA, ALTER, TRUNCATE, SET ROLE owner/migrator, UPDATE/DELETE audit_logs e alteração schema_migrations negados SQLSTATE 42501. Executar tentativas em transações sempre revertidas e uma conexão por tentativa; permissões não podem ser testadas só como superuser com SET ROLE |
| Eventos e replay | Evento novo somente da fixture `/fixtures/demo.conf` aparece na central, com agent_id/UUID e hash; backlog existente é entregue sem descarte. Comparar UUID/contagens, sem exigir fila zero se houver geração contínua. Não rodar benchmark ou seed genérico contra ativo |
| Heartbeat | Piloto permanece reconhecido, last_seen avança, queue_size e última coleta coerentes após reconexão. Testes 409/422/503/backlog do novo worker continuam no clone até atualizar o piloto posteriormente |
| Auditoria | Login, operações sintéticas e ações testadas auditadas sem bearer/senha/cookie; leitura de auditoria conforme role; histórico anterior preservado |
| Interface | Login, overview, eventos, servidores, credenciais e auditoria em 390/768/1280; navegação teclado e mensagens de erro; axe nas sete páginas. Falhas 503 simuladas somente no browser/clone, sem derrubar central |
| Backup pós-mudança | Novo snapshot criptografado sem perda dos anteriores, healthcheck e decriptação; restore isolado com owners/grants reprovisionados, schema/contagens e login do candidato válidos |
| Monitoramento | Readiness/Kuma 20 e backup/Kuma 21 coerentes; push periódico aceito; receber e confirmar alerta DOWN e recuperação UP no canal, sem mexer na configuração global |

Não executar a suite E2E integral contra a homologação ativa: `tests/e2e/seed.py` e testes de jornada criam entidades/credenciais e têm pressupostos de banco descartável. Preparar smoke dedicado sem seed, usando credenciais já existentes do projeto por leitura privada; testes de erros, tenants e permissões potencialmente mutantes primeiro no clone. Não copiar HTML autenticado, cookies, tokens ou senha ao relatório. Relatar cenário realmente executado e lacunas, sem inferir aprovação visual do RC2 a partir do RC1.

## 8. Rollback seguro e pontos de parada

**Gatilhos:** readiness não estabiliza no prazo, login/RBAC/CSRF falha, role privilegiada no HTTP, mount/versão de schema inesperados, perda/duplicação de evento, backup irrecuperável, secrets em logs ou regressão impeditiva. Parar somente API/web afetados, manter DB/volume e fila; registrar causa sem dados sensíveis.

| Momento da falha | Ação |
| --- | --- |
| Antes de G0/gates/parada | Não modificar o recurso; RC1 segue como estava |
| Backup/provisionamento falha antes de substituir imagens | Reverter transação, preservar snapshots e parar a janela. Não recriar imagens RC1 vulneráveis como “recovery”. A eventual retomada dos containers já existentes precisa ser avaliada sob a restrição de imagens; não assumir exceção automática |
| Roles adotadas, antes/depois do deploy RC2 | Manter roles restritas e schema 1. Usar apenas o conjunto fallback limpo assinado/ensaiado de G2, com DSN runtime; não restaurar SUPERUSER, ownership antigo nem ADMIN_PASSWORD no HTTP |
| Regressão da API | Via mesmo UUID/Compose fixado, substituir somente `CONFIGSENTINEL_API_IMAGE` pelo digest do manifest fallback aprovado; manter web/DB RC2. Cache verificado, custom build coerente com fallback e custom start sem pull/build; migration schema 1 não destrutiva, grants reaplicáveis |
| Falha da imagem DB RC2 | Manter volume íntegro, parar app e investigar. Sem fallback PostgreSQL 17.11 limpo e ensaiado, manter serviço parado e preparar correção; não iniciar DB vulnerável ou fazer downgrade |
| Suspeita de dano aos dados/schema | Não executar restore/downgrade sobre ativo. Restaurar somente em volume isolado para diagnóstico. Qualquer substituição de dados, exclusão ou perda de eventos exige aprovação específica de Franklin |

O ensaio anterior prova compatibilidade de schema 1 e retorno de binários, mas não autoriza o uso das imagens RC1 vulneráveis nesta janela. A API RC1 reescaneada tem zero HIGH/CRITICAL, mas seu archive local não é ainda digest GHCR assinado de fallback; G2 deve fechar essa lacuna antes de interromper tráfego. A web mantém os assets do produto na base endurecida. Conferir toda a combinação no clone, incluindo permissões e readiness.

Preservar os três archives RC1 e respectivos checksums como evidência e origem de recuperação. Caso seja necessário reempacotar a API RC1 em base atualizada, tratar como artefato novo, com digest/SBOM/assinatura/scans/ensaio próprios. Manifest de rollback não pode apontar para `latest` ou para o Compose histórico. Após rollback repetir smoke e conferir baseline/fila/monitor; registrar decisão de abortar RC2. Nunca modificar Traefik ou outros recursos para contornar falha.

## 9. Etapa posterior — agente sintético frank-note2

Somente após aceite da central e **autorização explícita para a etapa do piloto**. O agente atual é Alpine com bind do binário antigo; trocar apenas a imagem mantendo esse bind executaria o binário antigo e não validaria o RC2.

1. Verificar assinatura/scans do digest `agent` do manifest e arquitetura. Guardar spec, hash da configuração/allowlist e binário atual em armazenamento privado exclusivo; preservar token sem imprimir/rotacionar. Scan do fallback do agente obrigatório antes de considerá-lo executável.
2. Parar somente `configsentinel-agent-lab`, aguardar encerramento limpo e snapshot SQLite consistente pelo backup API ou, parado, pelo conjunto de arquivos DB/WAL/SHM; não copiar apenas SQLite ativo nem remover WAL. Registrar UUIDs/contagem/sequência e hash da configuração. A chave do backup da central não é backup da fila do piloto.
3. Preparar container RC2 com o digest agent, entrypoint nativo `/usr/local/bin/configsentinel-agent`, **sem bind do binário antigo**. Reutilizar `configsentinel-lab-config:/config:ro`, `configsentinel-lab-fixtures:/fixtures:ro`, `configsentinel-lab-state:/state:rw`, mesmo nome final/config, UID/GID 10001, read-only, cap_drop ALL, no-new-privileges, memory 160m/cpu 0.15/pids 64; sem socket/portas/privilégios novos. Não executar dois agentes simultâneos sobre a mesma fila.
4. Preservar container/spec anterior sem remoção de volumes. Conferir `/config/agent.yaml`, token_file e `/state/events.sqlite` idênticos; allowlist única `/fixtures/demo.conf`, hash_only=true, intervalo atual 5 s. Não passar token por CLI/env e não monitorar outros arquivos.
5. Iniciar candidato, verificar heartbeat enquanto flush falha em ensaio controlado primeiro no clone. No piloto, apenas interrupção de ingestão sintética autorizada, sem firewall/DNS e sem alterar allowlist; reconexão entrega os mesmos UUIDs sem duplicação, inclusive backlog anterior. Não descartar lotes 409/422 ou resetar fila. Medir queue_size/last_seen/coleta na central.
6. Se falhar: parar candidato, preservar DB/WAL atuais (a metadata nova é retrocompatível), validar fallback escaneado antes de retomá-lo. Nunca restaurar snapshot antigo de fila sobre eventos novos. Se não houver fallback limpo, manter piloto parado com fila intacta e corrigir; não aumentar permissões. Aceite do piloto registrado separadamente.

## 10. Kuma 21 e entrega efetiva

O monitor independente e seu push usam configuração exclusiva ConfigSentinel. Os journals recentes demonstram health/decriptação e resposta aceita pelo endpoint. O badge N/A é inconclusivo. Franklin confirmou explicitamente “Recebi o alerta do ConfigSentinel” e enviou captura mostrando DOWN/UP por backup_overdue às 16:04, DOWN/UP por checksum_mismatch às 16:12 e mensagem de teste às 20:47. **Recebimento humano confirmado para esses testes.** Horários são os exibidos na captura; não foram consultados no provedor. [Registro sanitizado](evidence/promotion/alert-receipt-confirmation.json), sem copiar a captura com conversas/serviços alheios. Os avisos foram produzidos pelos ensaios controlados anteriormente documentados; não demonstram falha real do backup.

Não executar `scripts/kuma-backup-monitor.cjs` ou `scripts/kuma-configsentinel.cjs` nesta preparação: eles acessam autenticação/configuração global do Kuma, fora do limite atual de credenciais. Não consultar tokens Telegram, JWT ou banco global. Para fechar G5, Franklin confere monitor 21/canal na UI ou fornece acesso realmente limitado ao ConfigSentinel, com evidência sanitizada.

Depois da autorização e antes de parar a central, combinar horário/identificador do teste. Usar apenas endpoint push exclusivo do ConfigSentinel e fixtures de falha/corrupção/atraso, preservando arquivos e último sucesso reais; receber DOWN e UP no canal, com horário e confirmação do destinatário. Ensaiar ausência de push pausando **somente** `configsentinel-backup-monitor.timer` na janela própria, por intervalo suficiente para Kuma 600 s + retries confirmados na UI. Não parar backup diário nem mudar monitor global. Retomar timer/service em rotina de recuperação garantida mesmo se o teste falhar e confirmar push UP. Se não puder consultar retries/canal sem credencial global, pedir conferência humana antes do teste, não inferir valores.

Não agendar esse ensaio durante a promoção. O recebimento dos testes anteriores está confirmado; a pendência de ausência de push e de conferência da configuração atual mantém o gate operacional aberto, sem ser convertida em “alerta configurado e testado integralmente”.

## 11. Registro final e autorização solicitada

Após uma execução futura, anexar resultados sanitizados em `docs/evidence/promotion/`, atualizar [validation.md](validation.md), [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) e manifest com digests reais, SHA de preparação, backup, contagens, roles, smoke, tempos e eventual rollback. `active_homologation_promoted=true` somente se efetivamente promovido e validado; `production_approved=false` permanece. Atualização do piloto tem aceite separado.

**Agora:** plano/Compose/evidências preparados, sem alterações na homologação ativa, credenciais, filas ou agendamentos. Aguardar aprovação explícita de Franklin para executar os prechecks restantes e, somente com todos PASS, modificar este recurso de homologação. Essa autorização não abrange produção, imagens vulneráveis, exclusão de dados/backups ou alterações a outros serviços.
