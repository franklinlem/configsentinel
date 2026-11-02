# J5 — Fase 1 sintética concluída

Data: 02/11/2026. Base: `9a59450`. **PASS para o ensaio sintético; NO-GO para J5 ativo e produção.** Nenhum banco ativo, credencial real ou registro de aplicação do Coolify foi consultado. Não houve deploy, restart de serviços existentes, mudança de roles ou limpeza. A situação atual da homologação não foi revalidada: sua indisponibilidade é a última condição operacional documentada.

Implementação: [harness](../scripts/j5_synthetic/README.md). Evidência consolidada: [result.json](evidence/j5-synthetic-phase1/result.json), [hashes](evidence/j5-synthetic-phase1/sha256.json), [runtime](evidence/j5-synthetic-phase1/runtime.json) e [dependências](evidence/j5-synthetic-phase1/dependencies.json).

## Ambiente e isolamento

Criados exclusivamente dois containers novos na Contabo: PostgreSQL 15.19 e PHP CLI 8.4.27, usando as imagens exatas aprovadas do PostgreSQL 15 e Coolify 4.5.3. IDs completos e diretórios privados constam no inventário abaixo e no JSON. O código/modelos/framework vêm da imagem Coolify; não houve instalação de dependências ou pull de tags.

Rede Docker exclusiva `--internal`, gateway IPv4 em modo `isolated`, IPv6 desativado, sem portas publicadas, rootfs somente leitura, capacidades removidas, sem Docker socket e sem mounts de volumes existentes. CPU limitada a 0,5 por container; memória limitada a 256 MiB para PostgreSQL e 512 MiB para PHP, sem swap adicional. Banco, código e caches usam tmpfs exclusivos. Credenciais e APP_KEY são geradas ficticiamente, com arquivo privado 0600.

O gate anterior às fixtures confirmou conexão positiva ao banco sintético e **228 conexões TCP negativas**: 28 endereços do host e 200 combinações IP/porta das redes de serviços existentes. Todas falharam com `ENETUNREACH` (101), sem sessão com serviço real. Somente endereços de infraestrutura foram descobertos; não foram lidos metadados de aplicações, envs ou credenciais ativas. Os endereços não foram publicados. DNS externo não resolveu e ambos os containers não possuem rota IPv4 padrão. O gate foi repetido nas continuações manuais, antes de qualquer carga de fixtures. Isso comprova o recorte de isolamento ensaiado; não pretende cobrir alterações futuras de rede ou acesso administrativo do host.

Somente o processo PHP CLI ocioso, comandos CLI de teste e processos próprios do PostgreSQL foram iniciados. Nenhum supervisor, worker, scheduler ou servidor HTTP foi iniciado. Durante os testes PHP, `exec`, `system`, `passthru`, `shell_exec`, `proc_open`, `popen` e `pcntl_exec` ficaram desabilitados. Comandos Compose/build foram apenas metadados sintéticos, nunca executados. A rede impede chamadas a DNS/proxy/deploy externos e não existe Docker socket no clone.

## Resultados

| Cenário | Resultado e evidência |
|---|---|
| Primeira aplicação e idempotência | PASS: mudança inicial, segunda chamada `changed=false`, snapshot de dados idêntico após segunda chamada. |
| Rollback após escrita parcial | PASS: exceção injetada depois de INSERT, dados iguais à baseline. |
| Constraint | PASS: colisão de PK injetada durante a transação, categoria `database`, rollback dos registros. Não representa todas as constraints reais. |
| Warning PHP | PASS: `ErrorException` classificada `php_warning`, rollback. |
| Buffer durante transação | PASS: 23 bytes fictícios detectados, categoria `output_buffer`, rollback. |
| Buffer preexistente | PASS: 28 bytes fictícios detectados, rollback. |
| Fila `queued` | PASS: rejeição de estado e preservação dos registros. |
| Fila `in_progress` | PASS: rejeição de estado e preservação dos registros. |
| Variável duplicada | PASS: rejeição antes da mudança. |
| Senha anterior divergente | PASS: rejeição, sem rotação da credencial sintética. |
| Auto-deploy divergente | PASS: rejeição de settings inválidos, sem mudança. |
| Concorrência por lock | PASS: segunda conexão sintética mantém lock; helper sofre timeout de 200 ms e reverte. Não é uma reprodução de corrida de deploy real. |
| Resposta ambígua após commit | PASS no cenário simulado: dados confirmados independentemente e resposta deliberadamente truncada, sem retry automático. O teste não injeta queda real de SSH. |
| Criptografia e flags | PASS: ciphertext sintético difere do valor, decriptação coincide em memória e flags previstas são persistidas. |

Foram **14 cenários PostgreSQL aprovados**, sem eventos `saving` da aplicação/variáveis, conforme `saveQuietly`; não surgiu entrada extra na fila. O resultado inclui verificações do helper e comparações de snapshots sintéticos; não valida o job real do Coolify. PostgreSQL sequences podem avançar em transações revertidas: a comparação garante preservação dos registros, não rollback de contadores de sequences.

Os **11 testes existentes do protocolo** passaram: JSON válido, vazio/truncado/texto adicional, bytes inválidos, erro de execução/transporte, limites de tamanho, stderr inesperado, allowlists de diagnóstico e ausência de conteúdo sensível nos erros. O protocolo operacional não foi alterado. O oracle original executado em SQLite `:memory:` dentro do novo container também passou para rollback, idempotência, digest inválido, criptografia e serializer.

O helper operacional conserva SHA-256 `bd67c1cea61b834f8913ed6fddccde1164640f31068ba18853c3c7200a5b60c4`. A cópia de teste altera exatamente dois tokens string: o UUID aceito pelo modo ativo para um identificador sintético e o nome do projeto no comando armazenado. O modo SQLite do original foi exercitado separadamente; não se afirma identidade byte a byte entre os helpers PostgreSQL e ativo. Nenhuma alteração genérica textual foi feita no código operacional.

## Correções do harness durante a execução

As tentativas estão preservadas, sem sobrescrever evidências:

1. `attempt-1.json`: Docker recusou `docker cp` sobre o container com rootfs somente leitura; nenhuma fixture foi carregada. Corrigido para transferência de fonte por stdin/tar ao tmpfs de `/tmp`, mantendo rootfs read-only.
2. `attempt-2.json`: isolamento passou; bootstrap não tinha permissão para escrever cache porque PHP usa UID/GID 9999 e o tmpfs era de root. Corrigido apenas nos novos diretórios temporários. O roteiro de criação agora especifica UID/GID 9999 e modo 0700. Nos recursos preservados desta tentativa, os dois diretórios raiz de tmpfs receberam modo 01777 para permitir a continuação sem restart; não contêm credenciais reais. Arquivo de credenciais fictícias continuou 0600.
3. `attempt-3.json`: bootstrap exigia `storage/framework/views`, ausente no tmpfs novo. O harness passou a criar somente os subdiretórios necessários com modo 0700.
4. `attempt-4.json`: PASS, duração de 15,466 s para a continuação e os testes remotos. Esse tempo não inclui implementação, criação inicial, correções ou testes locais.

Nenhum recurso foi recriado, parado ou removido para corrigir essas falhas. Não houve leitura de stderr bruto em relatórios; logs guardam fase, categoria, classe/posição de código quando pertinente, código de saída e tamanhos. As falhas do harness não demonstram a origem do J5 histórico: permissões e diretórios do clone foram escolhas desta execução.

## Recursos preservados

| Recurso | Identificação |
|---|---|
| Prefixo | `configsentinel-j5-phase1-f72ab6b2a2` |
| Rede | `b9fc0b5e93f4598032225628c587bc5e3434ce563f37ff53a00e1e2c913ab9e7` |
| Container PostgreSQL | `66cbeba8e28af33c1a729b8fce8927d67dfd444a007ce8f7bc69133df1353166` |
| Container PHP | `23c4193969bdab2314f06de39a5b0870f04f226f4f9b4926367adc81f8911449` |
| Diretório privado | `/home/franklin/.config/configsentinel-j5-phase1-f72ab6b2a2` |
| Código privado do ensaio | `/home/franklin/.config/configsentinel-j5-phase1-code-dea4fdf055` |

Ambos permaneceram em execução e sem OOM ao final. Quatorze schemas sintéticos ficaram preservados, além do estado dos testes SQLite descartado naturalmente ao fim daquele processo em memória. A chave fictícia existe somente no ambiente privado do ensaio. Não há cleanup automático. Parar os containers pode perder tmpfs; limpeza requer autorização separada. Recursos e dados anteriores ao ensaio não foram removidos.

## Diferenças e próxima etapa

O schema é um subconjunto sintético de sete tabelas com constraints escolhidas, não um catálogo extraído da instalação. Modelos, casts e mutators são os da imagem; registros, timestamps, identificadores, chave de criptografia e senhas são inventados. Não foram reproduzidos todos os relacionamentos de equipe/projeto, configurações globais, integrações, migrations, constraints/triggers reais, middleware, jobs ou ambiente HTTP. Não foram copiados ciphertext nem valores reais, portanto dados malformados ou peculiaridades de criptografia do ativo continuam fora da reprodução.

**A causa histórica do `internal_error` permanece desconhecida.** O ensaio comprova caminhos de sucesso/rejeição e falhas sintéticas, não a condição original. A Fase 1 está concluída, mas não justifica executar J5 ativo.

A Fase 2 ainda é necessária se o objetivo for aumentar a fidelidade aos metadados instalados: revisão de allowlist de catálogo/colunas e relações, extração somente leitura com sanitização na origem e sem valores/ciphertext reais, comparação estrutural e nova carga no clone. Ela exige autorização específica; o plano-base continua em [J5_DIAGNOSTIC_CLONE_PLAN.md](J5_DIAGNOSTIC_CLONE_PLAN.md). Nenhuma extração foi preparada para execução automática nem executada nesta fase. Alternativa de configuração nativa permanece em avaliação, sem chamadas de controller/API.

**Decisão: GO para revisão da Fase 1; NO-GO para J5 ativo, J6–J8 e produção.** Não há aceite automático da homologação. A próxima operação depende do escopo que Franklin autorizar, incluindo autorização separada para limpeza dos recursos sintéticos.
