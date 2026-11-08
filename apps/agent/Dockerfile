# Laboratory packaging only; production Linux deployment uses the systemd unit.
FROM golang:1.27.3-alpine@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb AS build
WORKDIR /src
COPY apps/agent/go.* ./
RUN go mod download
COPY apps/agent/ ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/agent ./cmd/configsentinel-agent
FROM alpine:3.23@sha256:ff7f0c727dd796aa36787bfcd9a64bf35a6ce72a73451b3359fde849b6703d63
RUN apk add --no-cache ca-certificates zlib=1.4-r0 && addgroup -g 10001 configsentinel && adduser -D -u 10001 -G configsentinel configsentinel
COPY --from=build /out/agent /usr/local/bin/configsentinel-agent
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/configsentinel-agent"]
CMD ["-config", "/config/agent.yaml"]
