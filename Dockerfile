FROM python:3.9.17-alpine
WORKDIR /app

RUN apk add build-base linux-headers clang 
COPY requirements.txt requirements_docker.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements_docker.txt

COPY . .

RUN adduser -D gpt
USER gpt
RUN mkdir -p $HOME/.config/gpt-cli
RUN cp /app/gpt.yml $HOME/.config/gpt-cli/gpt.yml

ENV GPTCLI_ALLOW_CODE_EXECUTION=1
ENTRYPOINT ["python", "gpt.py"]
