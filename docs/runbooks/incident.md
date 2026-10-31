# Incidentes

- API indisponível: verificar health/readiness e logs JSON dos containers exclusivos; checar conexão PostgreSQL e espaço do volume. Não executar limpeza genérica do Docker.
- Agente offline: distinguir última comunicação de última coleta; verificar rede, TLS e token expirado/revogado. Não modificar o reinício do roteador.
- Fila crescendo: preservar SQLite/WAL e configuração; corrigir acesso ou token. Retry usa backoff/jitter. Ao atingir o limite, snapshots não avançam e há erro em log. Eventos já persistidos permanecem; mudanças intermediárias durante saturação podem ser perdidas.
- Arquivo unreadable/unstable: revisar allowlist, perms, tamanho, tipo e links; não executar agente como root.
- Suspeita de token comprometido: revogar no painel e emitir novo token. Reconhecimento não significa aprovação da mudança.
- Comprometimento de root: tratar hashes como sinais, preservar backup e evidências externas. A plataforma não oferece atestação inviolável.
- Retenção: job interno horário apaga eventos >90 dias em lotes de 5000 e sessões expiradas/revogadas >1 dia. Reconhecimentos antigos acompanham eventos por cascade. Últimas observações e auditoria têm retenção independente; auditoria não é apagada automaticamente.
