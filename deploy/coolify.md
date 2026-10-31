# Homologação no Coolify

Recurso dedicado ConfigSentinel / homologacao; domínio configsentinel-dev.franklem.uk. Deploy manual, Docker Compose Raw, arquivo `/deploy/compose.coolify.yml`. Apenas web participa da rede externa coolify e possui labels Traefik. API somente app/database; PostgreSQL somente database (internal), sem portas do host.

Segredos exclusivos em variáveis de execução do Coolify: POSTGRES_PASSWORD (hex), ADMIN_EMAIL, ADMIN_PASSWORD. Não reutilizar banco, tokens ou volumes de outras aplicações. Não habilitar auto deploy.

As imagens da aplicação são construídas a partir de commit Git fixado pelo deploy Coolify; registrar IDs/digests locais na evidência. PostgreSQL fixado por digest. CI gera binários; publicação de imagens em registry e promoção por digest serão necessárias antes de produção.

Health: `/api/health/live`, `/api/health/ready` (estado agregado sem detalhes), `/healthz`. `/metrics` retorna 404 publicamente. Métricas Go apenas em porta 9090 na rede interna, sem labels de alta cardinalidade. Readiness pública agregada é decisão explícita para monitoramento externo; nenhum diagnóstico do banco é publicado.

Não promover para configsentinel.franklem.uk sem aceite, revisão dos gates e política de backup externo. Ver runbooks e docs/validation.md.
