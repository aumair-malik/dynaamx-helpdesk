# Dynaamx build of Libredesk (built by .github/workflows/dynaamx-image.yml).
# Same as upstream's Dockerfile except the base image, passed in by the workflow: upstream's
# alpine:3.18 has been end of life since May 2025. The binary is static (CGO off), so the base
# only supplies CA certificates, the time zone data and the shell the compose file runs.
ARG ALPINE
FROM ${ALPINE}

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /libredesk

COPY libredesk .
COPY config.sample.toml config.toml

EXPOSE 9000

CMD ["./libredesk"]
