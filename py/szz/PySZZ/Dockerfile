FROM python:3.7-slim-buster

RUN echo "deb http://deb.debian.org/debian buster-backports main" >> /etc/apt/sources.list && \ 
  apt-get update && apt-get upgrade -y --no-install-recommends && \
  apt-get -y install openjdk-11-jre-headless && \
  apt-get install -y --no-install-recommends wget libarchive13 libcurl4 libxml2 python-magic && \
  apt-get -t buster-backports install -y --no-install-recommends git && \
  rm -rf /var/lib/apt/lists/*

RUN wget http://131.123.42.38/lmcrs/v1.0.0/srcml_1.0.0-1_ubuntu18.04.deb && \
    dpkg -i srcml_1.0.0-1_ubuntu18.04.deb

RUN adduser --home /home/szz/ --disabled-password  --uid 1000 szz

WORKDIR /home/szz/

USER szz

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY szz szz
COPY --chown=szz:szz tools tools
COPY main.py .
COPY options.py .

RUN chmod +x tools/RefactoringMiner-2.0/bin/RefactoringMiner

CMD ["bash"]
