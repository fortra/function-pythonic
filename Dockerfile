FROM python:3.13-slim-trixie AS image

COPY dist/*.whl /root
WORKDIR /
RUN \
  set -eux && \
  pip install --root-user-action ignore --no-build-isolation /root/*.whl && \
  rm -rf /root/*.whl /root/.cache && \
  groupadd --gid 2000 pythonic && \
  useradd --uid 2000 --gid pythonic --home-dir /opt/pythonic --create-home --shell /usr/sbin/nologin pythonic

USER pythonic:pythonic
WORKDIR /opt/pythonic
EXPOSE 9443
ENTRYPOINT ["function-pythonic"]
