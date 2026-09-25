# syntax=docker/dockerfile:1
# Reproducible fast RTL/formal workbench. This is not the CMOS5L tapeout flow.
FROM python@sha256:a36c24f9cbdf4fd0f52d67f0823eeac19c2028c637cecc392d97f980d4fec56b

ARG OSS_CAD_SUITE_VERSION=2026-07-29
ARG OSS_CAD_SUITE_ARCHIVE=oss-cad-suite-linux-x64-20260729.tgz
ARG OSS_CAD_SUITE_SHA256=89ea1152ea84bc600f18cc685f721d534d1f018e09831662787865a3d79ce4aa
ARG VERIBLE_VERSION=v0.0-4296-g0f262651
ARG VERIBLE_ARCHIVE=verible-v0.0-4296-g0f262651-linux-static-x86_64.tar.gz
ARG VERIBLE_SHA256=8569defb891d2316067613ea00442af28a7a09d405d95b54c0c91f9942d26635
ARG REQUIREMENTS_SHA256=32c07d0d07b642fb69c44948e7a3b8754109c4d801ea2803bf720a84c5a6747a

LABEL org.opencontainers.image.title="Protocol Emulator ASIC verification workbench" \
      org.opencontainers.image.source="https://github.com/KG-khangelani/protocol-emulator-asic" \
      org.opencontainers.image.licenses="Apache-2.0" \
      io.protocol-emulator-asic.oss-cad-suite="${OSS_CAD_SUITE_VERSION}"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONNOUSERSITE=1 \
    PROTOCOL_EMULATOR_LOCKED_WORKBENCH=1 \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/verible/bin:/opt/oss-cad-suite/bin"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates=20250419~deb12u1 \
        curl=7.88.1-10+deb12u15 \
        git=1:2.39.5-0+deb12u3 \
        make=4.3-4.1 \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,id=protocol-emulator-oss-cad-2026-07-29,target=/var/cache/oss-cad \
    test -f "/var/cache/oss-cad/${OSS_CAD_SUITE_ARCHIVE}" \
    || curl --fail --location --show-error \
        "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${OSS_CAD_SUITE_VERSION}/${OSS_CAD_SUITE_ARCHIVE}" \
        --output "/var/cache/oss-cad/${OSS_CAD_SUITE_ARCHIVE}"

RUN --mount=type=cache,id=protocol-emulator-oss-cad-2026-07-29,target=/var/cache/oss-cad \
    echo "${OSS_CAD_SUITE_SHA256}  /var/cache/oss-cad/${OSS_CAD_SUITE_ARCHIVE}" | sha256sum --check --strict \
    && tar -xzf "/var/cache/oss-cad/${OSS_CAD_SUITE_ARCHIVE}" -C /opt \
    && test -x /opt/oss-cad-suite/bin/yosys \
    && test -x /opt/oss-cad-suite/bin/sby

RUN --mount=type=cache,id=protocol-emulator-verible-v0.0-4296,target=/var/cache/verible \
    test -f "/var/cache/verible/${VERIBLE_ARCHIVE}" \
    || curl --fail --location --show-error \
        "https://github.com/chipsalliance/verible/releases/download/${VERIBLE_VERSION}/${VERIBLE_ARCHIVE}" \
        --output "/var/cache/verible/${VERIBLE_ARCHIVE}"

RUN --mount=type=cache,id=protocol-emulator-verible-v0.0-4296,target=/var/cache/verible \
    echo "${VERIBLE_SHA256}  /var/cache/verible/${VERIBLE_ARCHIVE}" | sha256sum --check --strict \
    && mkdir -p /opt/verible \
    && tar -xzf "/var/cache/verible/${VERIBLE_ARCHIVE}" --strip-components=1 -C /opt/verible \
    && test -x /opt/verible/bin/verible-verilog-lint

# Keep Icarus and vvp in one directory for cocotb's supported auto-detection.
# The custom vvp wrapper selects this project's locked Python/cocotb.
COPY iverilog-suite /usr/local/bin/iverilog
COPY vvp-system-python /usr/local/bin/vvp
RUN chmod 0755 /usr/local/bin/iverilog /usr/local/bin/vvp

COPY requirements.lock /tmp/workbench-requirements.lock
RUN echo "${REQUIREMENTS_SHA256}  /tmp/workbench-requirements.lock" | sha256sum --check --strict \
    && python -m pip install --no-cache-dir --require-hashes -r /tmp/workbench-requirements.lock \
    && rm /tmp/workbench-requirements.lock

WORKDIR /workspace
CMD ["make", "doctor"]
