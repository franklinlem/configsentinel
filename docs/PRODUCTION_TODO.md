# Preparação para produção — lista atual

Estado em 05/11/2026. Esta lista resume o estado posterior aos registros históricos do relatório; evidência sintética não é aceite de produção. Produção segue NO-GO e sua implantação requer autorização específica.

- [ ] **Retenção confiável:** a correção foi promovida à homologação: a manutenção repete após falhas e preserva eventos e reconhecimentos. Definir política de retenção, arquivamento, capacidade e recuperação para produção. O retorno à API anterior retomaria a exclusão após 90 dias e exige verificar o risco aos dados antes de qualquer rollback.
- [ ] **Agente e credenciais:** agente sintético atualizado: token sem symlinks e diretório de estado previamente criado, próprio do agente e não gravável por grupo/outros; arquivo e lock rejeitam symlinks e hardlinks. Avaliar bloqueios de I/O, ACLs e comprometimento do próprio UID; preservar allowlist e eventos.
- [ ] **Observabilidade:** exercitar offline, coleta atrasada e fila acumulada de ponta a ponta em fixtures sintéticas; verificar alertas por ausência de push e métricas de falha. O monitor 22 hoje cobre apenas o agente sintético selecionado, não agentes futuros automaticamente.
- [ ] **Desempenho:** medir ingestão por rede no ambiente representativo, com concorrência e latências documentadas, e definir SLO e limite de carga. O p95 mediano de 136,96 ms em TCP local não inclui TLS ou rede externa e não demonstra o desempenho de produção.
- [ ] **Backup e recuperação:** comprovar agendamento, armazenamento externo, retenção, chave de recuperação e alertas do ambiente de produção; ensaiar restore e medir RPO/RTO em ambiente isolado, sem restaurar sobre dados ativos.
- [ ] **Release e rollback:** renovar scans e análise de dependências, assinaturas e SBOM; fixar imagens por digest, revisar acesso ao registry e ensaiar migração e rollback compatível com o schema corrente. Preparar configuração e segredos específicos de produção.
- [ ] **Segurança e aplicação:** revalidar isolamento entre tenants, RBAC, sessões, CSRF, tokens e auditoria; revisar limites globais, recuperação de sessão, offboarding e falhas de interface. Confirmar acessibilidade e responsividade em cenários relevantes.
- [ ] **Operação e aceite:** definir ambiente, domínios, capacidade, responsáveis, alertas, runbooks, janela e critérios de rollback; concluir verificações e registrar decisão fundamentada. Aceite de homologação não implica aprovação de produção.

Já concluído em homologação: API otimizada promovida por digest, schema 2 e agente sintético atualizados; backup restaurado isoladamente; monitor de agente dedicado com recebimento humano confirmado. Ver [prontidão](PRODUCTION_READINESS.md), [ingestão](INGESTION_OPTIMIZATION.md) e [alertas](CAPACITY_AND_ALERT_DELIVERY.md).
