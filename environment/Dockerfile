# hash:sha256:774892405570ccf78e4c515317e7a662db533f7a5d9fd029137fa53d10a4b8fe
# Base image as configured in the capsule's Environment panel. Change it there
# rather than here -- the panel rewrites this line AND the hash header on line 1
# together. If you do edit it by hand, run `make capsule-fix` or the change will
# not deploy.
FROM registry.codeocean.com/codeocean/py-r:python3.12.8-R4.4.2-JupyterLab4.3.5-RStudiorstudio-server-2024.12.1-563-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

# No git credential helper here on purpose. The only git-sourced dependency is
# aiweb-common (github.com/UABGH-Emerging-Technologies/llm_utils), which is a
# public repo and clones anonymously. A `COPY git-askpass /` fails the build
# outright when Code Ocean does not place that file in the build context:
#   COPY git-askpass /: "/git-askpass": not found
# If a private git dependency is ever added, re-add ARG GIT_ASKPASS /
# ARG GIT_ACCESS_TOKEN and configure a git credential in Code Ocean first.

# All apt and pip installation lives in postInstall, which also embeds a
# verbatim copy of code/requirements.txt (/code is not mounted at build time).
# postInstall-sha256: 048f59cabab9f536d86fb6dc5b994319bb6c034598d2aad623e2fded1c899d08  (managed by tools/co_env_hash.sh)
COPY postInstall /
RUN /postInstall

# postInstall pre-downloads tiktoken's "gpt2" encoding here; the variable must
# stay set at runtime or tiktoken falls back to a temp dir and re-downloads.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
