# ADR 0001 — Monólito modular, tenancy e metadados mínimos

Aceito, 31/10/2026. API Go/Chi e PostgreSQL, agente Go independente com SQLite e frontend React/TypeScript/Vite. Organização, projeto e ambiente fazem parte da autorização desde o início. Cada consulta administrativa deriva o tenant da sessão e de joins; tokens de agente autorizam apenas ingestão do seu agente.

Somente aliases e hashes/metadados permitidos são transmitidos. Paths ficam no host. Não existe API de comandos ou distribuição de políticas. Token de agente aparece uma vez. Sessão opaca e revogável em cookie seguro, CSRF separado, senha Argon2id. nginx publica SPA e encaminha /api; banco e métricas ficam privados.

Homologação e produção têm redes, volumes, segredos e recursos separados. Promoção não automática. Não oferecer garantia forense contra root.
