# Otimização da ingestão

A API mantém o lock por agente, o commit transacional e as verificações de replay e conflito, mas agrupa as consultas de replay em uma chamada pgx `SendBatch` e as gravações em outra. Um mapa de eventos pendentes mantém a verificação de sequência/UUID dentro do próprio lote. Se houver conflito ou erro de banco, a transação é revertida; o conflito segue auditado.

Testes em PostgreSQL isolado cobrem replay entre e dentro de lotes, conflito e falha na segunda gravação com rollback integral. Um trace de lote com 100 eventos registrou 300 comandos agrupados em duas chamadas `SendBatch`, além de quatro comandos fora dos lotes; não é medição direta de pacotes de rede.

Uma amostra local sem detector de corridas, com 25 agentes, 100 eventos por lote e concorrência 5, mediu p95 de **244,15 ms antes** e **145,16 ms depois**, sem erros. A medição usa handler HTTP em processo e PostgreSQL Docker isolado; não é diretamente comparável ao benchmark anterior por rede nem comprova SLO de produção. [Evidência](evidence/ingestion-optimization-20261104/sample.json). A alteração foi promovida à homologação por digest após backup e restore isolado; produção permanece desativada.

Em três execuções alternadas por implementação, a mediana dos p95 por execução foi **260,48 ms antes** e **158,72 ms depois**, com zero erros. O mesmo limite se aplica: é ambiente local e não comprova SLO em produção. [Amostras](evidence/ingestion-optimization-20261104/paired.json).

Em 04/11, o job Coolify `f35f690b-5f82-4b8f-9cf0-a4abfab14753` terminou com sucesso. API, web e banco saudáveis, smoke e integridade passaram; agente sintético com heartbeat recente e fila vazia. O retorno à API anterior foi ensaiado no helper em SQLite e PostgreSQL sintéticos, sem executar rollback ativo. [Evidências](evidence/ingestion-promotion-20261104/).
