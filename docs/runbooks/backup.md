# Backup

`scripts/backup.sh` executa pg_dump -Fc do banco exclusivo, criptografa AES256 com GPG e calcula SHA-256. Exige DB_CONTAINER, BACKUP_DIR e BACKUP_PASSPHRASE_FILE. Passphrase deve ficar em arquivo 0600 fora do repositório. Dump contém dados administrativos, hashes de credenciais/sessões e metadados sensíveis; tratar como restrito.

Um ensaio não configura agendamento. Para operação recorrente: timer dedicado no host, cópia criptografada para outro servidor, política de retenção aprovada e verificação do último backup. Não apagar backups antigos antes de aprovar a política e provar restore. Passphrase precisa de cópia separada sob controle do operador; perder a chave torna backup irrecuperável.

## Instalação ativa de homologação

O timer de usuário `configsentinel-backup.timer` no frank-note2 agenda pull às 03:35 America/Sao_Paulo, com jitter de até 2 minutos e Persistent=true; linger está habilitado. `scripts/offsite-backup.py` preserva os snapshots diários e semanais criptografados em `~/.local/share/configsentinel-backups`, sem exclusão automática; o primeiro backup da semana também é guardado como snapshot semanal. A capacidade de armazenamento precisa ser acompanhada até existir uma política de retenção aprovada.

Uma chave SSH exclusiva fica em `~/.config/configsentinel-backup/id_ed25519`; na Contabo a chave só pode executar `/home/franklin/.local/bin/configsentinel-backup-export` com `restrict` (sem PTY/forwarding). O comando exporta apenas o banco deste recurso. A chave de criptografia fica em `~/.config/configsentinel-backup/encryption.key`, 0600. Não está no Git nem junto dos dumps. Em 05/11 foi conferida uma cópia da chave, com permissão restrita e conteúdo correspondente, no host `frank-note`, separado do `frank-note2`. Sua disponibilidade em caso de perda simultânea ou falha de hardware não foi ensaiada; o operador deve manter recuperação protegida adicional conforme a política de produção.

`last-success.txt` registra a última execução. O monitor independente verifica idade, checksum e decriptação e envia resultados ao monitor push Kuma 21; a ausência de push também é sinalizada pelo Kuma.

O monitor também informa `backup_low_space` quando o espaço disponível no filesystem dos backups fica abaixo de 1 GiB ou 5% da capacidade total. Esse limiar é uma salvaguarda operacional de homologação; a capacidade e a política de retenção de produção ainda precisam ser dimensionadas. O teste de espaço baixo foi feito com filesystem simulado; a consulta real retornou saudável. [Evidência](../evidence/production-prep-20261108/backup-space-monitor.json).

## Instalação ativa de produção

Implementada em 08/11/2026 seguindo o mesmo padrão de segregação restrita:
- Chave SSH dedicada `id_ed25519` em `~/.config/configsentinel-prod-backup/`; na VPS Contabo (`158.220.120.2`) a chave possui comando forçado (`restrict,command="/home/franklin/.local/bin/configsentinel-prod-backup-export"`).
- O script `/home/franklin/.local/bin/configsentinel-prod-backup-export` localiza dinamicamente o container ativo do PostgreSQL de produção via labels `com.docker.compose.project=rtk5g5dxkq498fiw9k23marq` e `service=db`, executando `pg_dump -U configsentinel -d configsentinel -Fc`.
- Chave de criptografia AES256 dedicada em `~/.config/configsentinel-prod-backup/encryption.key` (0600) com cópia de contingência em subdiretório isolado.
- Destino local offsite em `~/.local/share/configsentinel-prod-backups/daily` e `weekly` no host `frank-note2`.
- Agendamento via timer de usuário `configsentinel-prod-backup.timer` (diário às 03:45 America/Sao_Paulo, Persistent=true).
- Monitor de integridade `configsentinel-prod-backup-monitor.timer` executando a cada 5 minutos com teste de decriptação, checksum e envio push ao monitor Uptime Kuma 24 (`ConfigSentinel · Produção · Backup criptografado`), vinculado ao canal de notificação `HermesFranklem`.
- Restore em banco isolado comprovado com RTO total de 2,76 s (395 ms de streaming de decriptação/restore).
