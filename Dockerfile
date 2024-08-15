FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python                                                                                                                       
                                                                                                                                                                           
LABEL org.opencontainers.image.source = "https://github.com/jvde-github/ais2adsb"                                                                                          

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY rootfs/ /

COPY ais2adsb.py /usr/local/bin/

RUN set -x && \
apt-get update -y && apt-get install -q -o Dpkg::Options::="--force-confnew" -y --no-install-recommends --no-install-suggests git python3-bitarray && \
pip3 install --break-system-packages --no-cache-dir pyais && \
#
# Add Container Version
pushd /tmp && \
    branch="##BRANCH##" && \
    [[ "${branch:0:1}" == "#" ]] && branch="main" || true && \
    git clone --depth=1 -b $branch https://github.com/jvde-github/ais2adsb.git && \
    cd ais2adsb && \
    echo "$(TZ=UTC date +%Y%m%d-%H%M%S)_$(git rev-parse --short HEAD)_$(git branch --show-current)" > /.CONTAINER_VERSION && \
popd && \
apt-get remove -y git && \
apt-get autoremove -y && \
rm -rf /tmp/*
