FROM python:3.12-alpine3.20 AS builder

ENV VIRTUAL_ENV="/opt/swirlc"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY ./pyproject.toml ./MANIFEST.in ./LICENSE ./README.md /build/
COPY ./requirements.txt           \
     ./bandit-requirements.txt    \
     ./lint-requirements.txt      \
     ./test-requirements.txt      \
     /build/
COPY swirlc /build/swirlc

RUN cd build \
    && python -m venv ${VIRTUAL_ENV} \
    && pip install .


FROM python:3.12-alpine3.20
LABEL maintainer="Iacopo Colonnelli <iacopo.colonnelli@unito.it>"
LABEL maintainer="Doriana Medić <doriana.medic@unito.it>"
LABEL maintainer="Alberto Mulone <alberto.mulone@unito.it>"

ENV VIRTUAL_ENV="/opt/swirlc"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

CMD ["/bin/sh"]