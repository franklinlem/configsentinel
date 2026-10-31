# ADR 0003 — Piloto isolado em frank-note2

31/10/2026. SSH funciona, mas sudo não permite execução sem senha. Para validar o agente sem alterar usuários, systemd ou configurações do host, o laboratório usa container com UID/GID 10001, sem grupos adicionais/capacidades, no-new-privileges, root filesystem somente leitura, sem portas publicadas, sem socket Docker e com mounts limitados à fixture sintética, configuração local/token e fila.

Somente o operador utiliza Docker para iniciar o laboratório. O processo agente não recebe credenciais ou socket do Docker. Configuração e fixture ficam read-only no agente; volume de estado fica gravável. Nenhum arquivo operacional do frank-note2 é monitorado. É adaptação de laboratório, não suporte geral a agentes containerizados no MVP. A unidade systemd continua sendo o pacote indicado para instalação Linux futura por administrador autorizado.
