# Medição de Desempenho e Latência de Rede Representativa para Produção

Data: 08/11/2026  
Módulos: `apps/api` e `apps/agent`  
Hosts de teste:
- Agente: `frank-note2` (Linux x86_64, Brasil)
- Central: VPS Contabo (Linux x86_64, Alemanha / Europa, domínio `configsentinel-dev.franklem.uk`)

---

## 1. Contexto e Motivação

O planejamento do ConfigSentinel estabeleceu uma meta indicativa de latência para ingestão de eventos em lotes de 100 itens com p95 < 300 ms em rede local de referência.

Em medições anteriores locais via TCP e em processo (conforme documentado em `docs/INGESTION_OPTIMIZATION.md` e `docs/evidence/production-prep-20261105/tcp-benchmark.json`), a otimização de `SendBatch` do pgx reduziu o tempo interno da API para uma mediana de p95 de **136,96 ms** (com concorrência de 5 workers e 25 agentes).

Restava medir o comportamento em um **caminho de rede representativo de produção**, incluindo a camada TLS e a travessia real de internet transcontinental (Brasil ↔ Europa).

---

## 2. Medições Físicas Realizadas (Brasil ↔ Europa)

As medições foram executadas diretamente do host real do agente (`frank-note2`) até a central ativa (`configsentinel-dev.franklem.uk`), sob TLS 1.3:

### 2.1 Conexão Fria (Cold Start com Handshake TLS Completo)
- Resolução de DNS (`namelookup`): **4,92 ms**
- Handshake TCP inicial (`connect`): **211,74 ms** (RTT geográfico real da fibra óptica transcontinental)
- Negociação TLS 1.3 (`appconnect`): **442,69 ms**
- Processamento e resposta da API (`starttransfer` / `total`): **654,40 ms**

### 2.2 Conexão Reutilizada (HTTP Keep-Alive / Conexão Quente)
O agente Go implementa pool de conexões persistentes via `http.Transport` padrão, mantendo conexões ativas entre ciclos:
- Requisição com conexão reutilizada: **211,58 ms**
- Tempo de ida e volta (1 RTT de rede pura): ~211 ms
- Overhead adicional do servidor: < 5 ms

---

## 3. Definição Formal de SLOs para Produção

Com base nas evidências coletadas, estabelece-se os seguintes níveis de serviço:

| Indicador | Alvo (SLO) | Observação |
|---|---|---|
| **Tempo de Serviço Interno da API (Lote 100 eventos)** | **p95 < 200 ms** (tolerância máxima 300 ms) | Medido em 136,96 ms sob concorrência de 5 lotes |
| **Ingestão de Ponta a Ponta com Keep-Alive (Brasil ↔ Europa)** | **p95 < 450 ms** | 1 RTT físico (~211 ms) + processamento interno (~140 ms) |
| **Primeira Conexão (com Handshake TLS 1.3)** | **p95 < 800 ms** | Inclui DNS, TCP handshake e negociação TLS |
| **Disponibilidade da Central (Readiness)** | **99,5% mensal** | Monitorada a cada 60s via Uptime Kuma |

---

## 4. Conclusão

A meta indicativa do projeto (p95 interno da API < 300 ms) foi integralmente superada (alcançando 136,96 ms). A latência adicional observada em conexões transcontinentais decorre exclusivamente do limite físico da velocidade da luz na fibra transatlântica (~210 ms de RTT), que é mitigada eficazmente pelo mecanismo de conexão persistente e envio desacoplado do agente Go.
