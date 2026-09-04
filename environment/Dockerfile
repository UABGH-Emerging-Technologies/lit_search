# hash:sha256:f4fac895501ee6cd20b61678a2957bef9fc35e9a066d6217cd8f30df82d7e62b
# Base image as configured in the capsule's Environment panel. Change it there
# rather than here -- the panel rewrites this line AND the hash header on line 1
# together. If you do edit it by hand, run `make capsule-fix` or the change will
# not deploy.
FROM registry.codeocean.com/codeocean/py-r:python3.12.8-R4.4.2-JupyterLab4.3.5-RStudiorstudio-server-2024.12.1-563-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

# Code Ocean injects these for pip dependencies fetched over git. Leave them in
# place: the git-askpass helper is supplied by Code Ocean at build time and is
# not a file in this repository.
ARG GIT_ASKPASS
ARG GIT_ACCESS_TOKEN
COPY git-askpass /

# All apt and pip installation lives in postInstall, which also embeds a
# verbatim copy of code/requirements.txt (/code is not mounted at build time).
# postInstall-sha256: cfea399b9a791eaa026c7702882a7e0247f1d754750856a20c93254353c2763d  (managed by tools/co_env_hash.sh)
COPY postInstall /
RUN /postInstall

# postInstall pre-downloads tiktoken's "gpt2" encoding here; the variable must
# stay set at runtime or tiktoken falls back to a temp dir and re-downloads.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
