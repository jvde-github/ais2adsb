FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python

LABEL org.opencontainers.image.source = "https://github.com/jvde-github/ais2adsb"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY rootfs/ /

COPY ais2adsb.py /usr/local/bin

RUN set -x && \
    pip install pyais && \
    chmod a+x /usr/local/bin/ais2adsb.py



# Add Container Version
RUN set -x && \
pushd /tmp && \
    branch="##BRANCH##" && \
    [[ "${branch:0:1}" == "#" ]] && branch="main" || true && \
    git clone --depth=1 -b $branch https://github.com/jvde-github/ais2adsb.git && \
    cd docker-vesselalert && \
    echo "$(TZ=UTC date +%Y%m%d-%H%M%S)_$(git rev-parse --short HEAD)_$(git branch --show-current)" > /.CONTAINER_VERSION && \
popd && \
rm -rf /tmp/*


# Add healthcheck
# HEALTHCHECK --start-period=60s --interval=600s --timeout=60s CMD /healthcheck/healthcheck.sh
