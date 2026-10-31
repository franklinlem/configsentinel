# ADR 0002 — Abertura Linux e persistência transacional

Aceito, 31/10/2026. openat2 com RESOLVE_NO_SYMLINKS e RESOLVE_NO_MAGICLINKS; nenhum fallback inseguro. O_NONBLOCK evita bloqueio em FIFO; fstat exige arquivo regular e nlink=1. Rejeitar caminhos não absolutos, normalização implícita, globs, aliases repetidos, paths negados e hash_only=false. Denylist padrão não pode ser removida por configuração.

Hash streaming limitado; fstat antes/depois e comparação com reabertura protegida detectam alterações concorrentes comuns. Nenhuma garantia contra invasor root ou mudanças intermediárias entre polls. SQLite WAL guarda snapshot e evento na mesma transação; estado não avança quando fila cheia. UUID e sequência duráveis, tentativas com backoff/jitter e ACK explícito antes de remoção. Reinício preserva fila; agente impede execução concorrente sobre o mesmo banco.
