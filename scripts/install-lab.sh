#!/usr/bin/env bash
# Run in the dedicated frank-note2 staging directory after provisioning a synthetic identity.
set -euo pipefail
lab_image='alpine:3.23@sha256:ff7f0c727dd796aa36787bfcd9a64bf35a6ce72a73451b3359fde849b6703d63'
docker pull "$lab_image" >/dev/null
docker run --rm --mount type=bind,src="$PWD",dst=/install,readonly \
 --mount type=volume,src=configsentinel-lab-config,dst=/config \
 --mount type=volume,src=configsentinel-lab-state,dst=/state \
 --mount type=volume,src=configsentinel-lab-fixtures,dst=/fixtures \
 "$lab_image" sh -ec '
 test -f /etc/ssl/cert.pem
 cp /install/agent.yaml /config/agent.yaml
 cp /install/agent.token /config/agent.token
 cp /install/demo.conf /fixtures/demo.conf
 chmod 600 /config/agent.token
 chmod 644 /config/agent.yaml /fixtures/demo.conf
 chown -R 10001:10001 /config /state
 '
docker run -d --name configsentinel-agent-lab --restart unless-stopped \
 --user 10001:10001 --read-only --cap-drop ALL --security-opt no-new-privileges:true \
 --memory 160m --cpus 0.15 --pids-limit 64 \
 --mount type=bind,src="$PWD/configsentinel-agent-linux-amd64",dst=/usr/local/bin/configsentinel-agent,readonly \
 --mount type=volume,src=configsentinel-lab-config,dst=/config,readonly \
 --mount type=volume,src=configsentinel-lab-state,dst=/state \
 --mount type=volume,src=configsentinel-lab-fixtures,dst=/fixtures,readonly \
 --entrypoint /usr/local/bin/configsentinel-agent \
 "$lab_image" -config /config/agent.yaml
