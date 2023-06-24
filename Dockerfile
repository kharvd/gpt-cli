FROM python:3.9.17-bullseye
WORKDIR /app

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY requirements_docker.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements_docker.txt

COPY . .

RUN mkdir -p /mnt/output

RUN adduser --disabled-password gpt
USER gpt
RUN mkdir -p $HOME/.config/gpt-cli
RUN cp /app/gpt.yml $HOME/.config/gpt-cli/gpt.yml


WORKDIR /mnt/output

ENV GPTCLI_ALLOW_CODE_EXECUTION=1
ENTRYPOINT ["python", "/app/gpt.py"]
