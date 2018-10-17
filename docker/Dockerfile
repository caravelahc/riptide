FROM python:alpine

RUN apk update && \
    apk add --no-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ dockerize postgresql-libs tini && \
    apk add --no-cache --virtual build-deps gcc libxml2-dev libxslt-dev musl-dev postgresql-dev && \
    pip install cagrex ipython pony psycopg2 && \
    apk del build-deps

COPY data.txt metadata.py riptide.py start.sh ./

ENTRYPOINT ["/sbin/tini", "--"]
