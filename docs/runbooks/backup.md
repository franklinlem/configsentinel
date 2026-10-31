# Backup

`scripts/backup.sh` executa pg_dump -Fc do banco exclusivo, criptografa AES256 com GPG e calcula SHA-256. Exige DB_CONTAINER, BACKUP_DIR e BACKUP_PASSPHRASE_FILE. Passphrase deve ficar em arquivo 0600 fora do repositório. Dump contém dados administrativos, hashes de credenciais/sessões e metadados sensíveis; tratar como restrito.

Um ensaio não configura agendamento. Para operação recorrente: timer dedicado no host, cópia criptografada para outro servidor, política de 7 diários / 4 semanais e verificação do último backup. Não apagar backups antigos antes de provar restore e retenção. Passphrase precisa de cópia separada sob controle do operador; perder a chave torna backup irrecuperável.

## Instalação ativa de homologação

O timer de usuário `configsentinel-backup.timer` no frank-note2 agenda pull às 03:35 America/Sao_Paulo, com jitter de até 2 minutos e Persistent=true; linger está habilitado. `scripts/offsite-backup.py` mantém 7 snapshots diários e 4 semanais criptografados em `~/.local/share/configsentinel-backups`. O snapshot semanal é criado na primeira execução de cada semana ISO.

Uma chave SSH exclusiva fica em `~/.config/configsentinel-backup/id_ed25519`; na Contabo a chave só pode executar `/home/franklin/.local/bin/configsentinel-backup-export` com `restrict` (sem PTY/forwarding). O comando exporta apenas o banco deste recurso. A chave de criptografia fica em `~/.config/configsentinel-backup/encryption.key`, 0600. Não está no Git nem junto dos dumps. O operador ainda deve guardar uma cópia protegida separada dessa chave para sobreviver à perda do frank-note2.

`last-success.txt` registra a última execução. Alertas para idade/falha do backup devem ser acompanhados operacionalmente; o monitor HTTP do Kuma não mede a idade do backup.
