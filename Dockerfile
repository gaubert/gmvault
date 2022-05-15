FROM python:2

WORKDIR /usr/src/app
COPY . ./
RUN python setup.py install

ENTRYPOINT ["gmvault"]
