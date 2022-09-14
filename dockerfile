# Dockerfile
FROM python:3.9-alpine
ENV PYTHONUNBUFFERED 1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="${PATH}:/root/.poetry/bin"
EXPOSE 8000/tcp
RUN mkdir /app
WORKDIR /app/

# Установка пакетов python и зависимостей необходимых для их сборки
RUN apk add --no-cache --virtual build-deps \
    curl `# для установки poetry` \
    make gcc g++ `# для сборки пакетов`


# Зависимости необходимые для работы
RUN apk add --no-cache

COPY poetry.lock pyproject.toml /app/
RUN pip install --upgrade pip
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi
RUN apk del --no-cache build-deps
COPY / /app/


