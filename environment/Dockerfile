# hash:sha256:6a9b524f804545bff31f03de31005b19e2c89fb3cf3ff4a1973bff3a4e5a0730
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
# postInstall-sha256: b0e80c5b7a067f98e4930384931680319b3995f44920ef8646b2603a48ae18a0  (managed by tools/co_env_hash.sh)
COPY postInstall /
RUN /postInstall
