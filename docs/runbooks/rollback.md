# Rollback

No Coolify, selecione o commit anteriormente validado e execute deploy manual. Preserve volume PostgreSQL, secrets, rede privada e fila do agente. Confirme schema_migrations e compatibilidade antes de rollback; trocar imagem não desfaz migration. Nunca execute down -v.

Primeira versão não possui schema anterior para reversão. Desabilitar monitor no Kuma se a homologação for removida intencionalmente, preservando histórico. Produção requer ensaio de promoção com imagens de registry fixadas por digest.
