# Backup

`scripts/backup.sh` executa pg_dump -Fc do banco exclusivo, criptografa AES256 com GPG e calcula SHA-256. Exige DB_CONTAINER, BACKUP_DIR e BACKUP_PASSPHRASE_FILE. Passphrase deve ficar em arquivo 0600 fora do repositório. Dump contém dados administrativos, hashes de credenciais/sessões e metadados sensíveis; tratar como restrito.

Um ensaio não configura agendamento. Para operação recorrente: timer dedicado no host, cópia criptografada para outro servidor, política de 7 diários / 4 semanais e verificação do último backup. Não apagar backups antigos antes de provar restore e retenção. Passphrase precisa de cópia separada sob controle do operador; perder a chave torna backup irrecuperável.
