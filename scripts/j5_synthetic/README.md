# Clone J5 sintético — Fase 1

Harness exclusivo para PostgreSQL sintético, imagens aprovadas por ID e PHP CLI. Não lê registros, credenciais ou configuração do banco ativo. A única descoberta de infraestrutura é a lista de endereços IP de interfaces/redes Docker para tentativas negativas de conexão; endereços não entram nas evidências versionadas.

- `launch.py`: empacota fonte e manifests, cria diretório privado de código via SSH Contabo e executa `run.py`. **Cria novos recursos**, nunca reutiliza nomes ativos.
- `run.py`: capacidade, imagens, credenciais fictícias 0600, rede interna com gateway isolado, PostgreSQL 256 MiB/0,5 CPU e PHP 512 MiB/0,5 CPU; rootfs read-only, capacidades removidas, logs Docker desativados e tmpfs exclusivos. Carrega fixtures somente após o gate de isolamento.
- `isolation.php`: conexão positiva ao banco sintético, tentativas TCP negativas ao host/serviços e DNS externo bloqueado. O inventário final verifica também ausência de rota padrão em ambos os containers.
- `adapt.php`: altera exatamente dois tokens string em cópia de teste: UUID do guard e nome do projeto no comando armazenado. Helper operacional intacto; nenhuma substituição genérica em Python/PHP.
- `schema.sql`: subconjunto sintético com PK/FKs e constraints escolhidas para o ensaio; não representa o catálogo real.
- `matrix.php`: 14 cenários com Eloquent real da imagem, schemas sintéticos independentes, sem remover dados de cenários anteriores. Falhas são injetadas por listener de queries, sem editar a transação operacional.
- `resume.py`/`continue.py`: continuação **manual** após correção do harness, limitada aos IDs, labels, imagens e rede inventariados. Não cria, reinicia ou apaga recursos; revalida escopo e isolamento antes dos testes. Não usar para falha de isolamento. Não há retry automático.

Comandos de execução, somente dentro de autorização vigente:

```bash
python3 scripts/j5_synthetic/launch.py
# Uma continuação explícita exige evidência anterior e novo arquivo de saída:
python3 scripts/j5_synthetic/resume.py <evidencia-anterior.json> <nova-evidencia.json>
```

Os testes de protocolo usam `python3 -m unittest discover -s tests/operations -p 'test_j5_protocol.py' -v`; não chamam o helper ativo. O oracle SQLite original roda dentro do novo container PHP, nunca no container Coolify ativo. Seus valores sintéticos serializados são descartados, mantendo somente invariantes permitidos.

O processo PHP permanece ocioso entre chamadas CLI. Não executa supervisor, workers, scheduler, HTTP, comandos Compose/build nem chamadas de controller. Além da rede isolada, execução de comandos via PHP é desabilitada durante os testes; não há socket Docker, portas publicadas ou mount de volume existente. O helper só armazena os comandos como dados sintéticos.

Nenhum script contém limpeza automática, `--rm`, `down -v`, `prune` ou conexão ao banco ativo. Containers, rede, diretórios privados e tmpfs são preservados. A parada/removal e a perda de tmpfs exigem autorização separada. As credenciais fictícias ficam fora do repositório; stdout/stderr de subprocessos são reduzidos a códigos/tamanhos, sem persistência bruta.

Resultado e diferenças: [relatório da Fase 1](../../docs/J5_SYNTHETIC_PHASE1.md).
