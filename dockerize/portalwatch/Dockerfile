FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    software-properties-common
RUN add-apt-repository universe
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python-pip \
    libpq-dev \
    python-dev \
    python-tk \
    cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* /var/tmp/*

RUN pip install flask
RUN pip install flask-cache
RUN pip install git+git://github.com/sebneu/anycsv.git
RUN pip install git+git://github.com/ODInfoBiz/pyyacp.git

ENV INSTALL_PATH /adequate-portalharvester
ENV LOGS /logs
ENV DATADIR /datadir
RUN mkdir -p $INSTALL_PATH $LOGS $DATADIR

WORKDIR $INSTALL_PATH
RUN git clone https://github.com/thlor/portalmonitor.git
ENV ADEQUATE $INSTALL_PATH/portalmonitor
WORKDIR $ADEQUATE

ADD portalmonitor.conf   $ADEQUATE/portalmonitor.conf

RUN echo "update"
RUN git pull; pip install -r requirements.txt; python setup.py install

ENTRYPOINT ["/bin/bash", "-c", "odpw -c $ADEQUATE/portalmonitor.conf ${*}", "--"]
