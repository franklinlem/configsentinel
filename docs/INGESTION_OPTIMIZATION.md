# Otimização da ingestão

A API mantém o lock por agente, o commit transacional e as verificações de replay e conflito, mas agrupa as consultas de replay em uma chamada pgx `SendBatch` e as gravações em outra. Um mapa de eventos pendentes mantém a verificação de sequência/UUID dentro do próprio lote. Se houver conflito ou erro de banco, a transação é revertida; o conflito segue auditado.

Testes em PostgreSQL isolado cobrem replay entre e dentro de lotes, conflito e falha na segunda gravação com rollback integral. Um trace de lote com 100 eventos registrou 300 comandos agrupados em duas chamadas `SendBatch`, além de quatro comandos fora dos lotes; não é medição direta de pacotes de rede.

Uma amostra local sem detector de corridas, com 25 agentes, 100 eventos por lote e concorrência 5, mediu p95 de **244,15 ms antes** e **145,16 ms depois**, sem erros. A medição usa handler HTTP em processo e PostgreSQL Docker isolado; não é diretamente comparável ao benchmark anterior por rede nem comprova SLO de produção. [Evidência](evidence/ingestion-optimization-20261104/sample.json). A alteração está em preparação; a imagem da homologação continua usando a implementação anterior até sua promoção.
