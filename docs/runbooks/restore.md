# Restore isolado

Valide o checksum do backup criptografado. Execute `scripts/restore-test.sh` com BACKUP_FILE e BACKUP_PASSPHRASE_FILE. O script cria PostgreSQL descartável sem rede, dados em tmpfs, restaura com --exit-on-error e consulta versão do schema e contagens. Remove somente o container temporário identificado pelo próprio script.

Para recuperação real, provisionar banco novo exclusivo, restaurar, apontar somente a API correspondente e validar autenticação/eventos. Não sobrescrever o volume ativo. Sessões/tokens do dump podem precisar revogação; revisar acesso antes de reabrir tráfego.

RPO/RTO são metas pendentes de medição operacional, não garantias. Backup não contém arquivos monitorados, configuração/token/fila locais do agente nem credenciais do Coolify.
