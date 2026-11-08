# Backup

`scripts/backup.sh` executa pg_dump -Fc do banco exclusivo, criptografa AES256 com GPG e calcula SHA-256. Exige DB_CONTAINER, BACKUP_DIR e BACKUP_PASSPHRASE_FILE. Passphrase deve ficar em arquivo 0600 fora do repositório. Dump contém dados administrativos, hashes de credenciais/sessões e metadados sensíveis; tratar como restrito.

Um ensaio não configura agendamento. Para operação recorrente: timer dedicado no host, cópia criptografada para outro servidor, política de retenção aprovada e verificação do último backup. Não apagar backups antigos antes de aprovar a política e provar restore. Passphrase precisa de cópia separada sob controle do operador; perder a chave torna backup irrecuperável.

## Instalação ativa de homologação

O timer de usuário `configsentinel-backup.timer` no frank-note2 agenda pull às 03:35 America/Sao_Paulo, com jitter de até 2 minutos e Persistent=true; linger está habilitado. `scripts/offsite-backup.py` preserva os snapshots diários e semanais criptografados em `~/.local/share/configsentinel-backups`, sem exclusão automática; o primeiro backup da semana também é guardado como snapshot semanal. A capacidade de armazenamento precisa ser acompanhada até existir uma política de retenção aprovada.

Uma chave SSH exclusiva fica em `~/.config/configsentinel-backup/id_ed25519`; na Contabo a chave só pode executar `/home/franklin/.local/bin/configsentinel-backup-export` com `restrict` (sem PTY/forwarding). O comando exporta apenas o banco deste recurso. A chave de criptografia fica em `~/.config/configsentinel-backup/encryption.key`, 0600. Não está no Git nem junto dos dumps. Em 05/11 foi conferida uma cópia da chave, com permissão restrita e conteúdo correspondente, no host `frank-note`, separado do `frank-note2`. Sua disponibilidade em caso de perda simultânea ou falha de hardware não foi ensaiada; o operador deve manter recuperação protegida adicional conforme a política de produção.

`last-success.txt` registra a última execução. O monitor independente verifica idade, checksum e decriptação e envia resultados ao monitor push Kuma 21; a ausência de push também é sinalizada pelo Kuma.
