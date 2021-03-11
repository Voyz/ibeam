FROM python:3.7.7-slim-buster

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p /usr/share/man/man1

RUN apt-get update && \
    apt-get install -y default-jre && \
    apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf && \
    rm -rf /var/lib/apt/lists/*


# Setup JAVA_HOME -- useful for docker commandline
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/
RUN export JAVA_HOME

WORKDIR /srv
RUN apt-get update && \
    apt-get install -y wget && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get purge -y --auto-remove wget && \
    apt install -y /srv/google-chrome-stable_current_amd64.deb && \
    rm -rf /srv/google-chrome-stable_current_amd64.deb



RUN apt-get install -y nano && \
    apt -y install curl && \
    apt-get -y install iputils-ping


RUN apt-get install -y gcc && \
    pip install psutil==5.* && \
    apt-get purge -y --auto-remove gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt

RUN chmod 744 /opt/venv/bin/activate

ENV GROUP_ID=1000 \
    USER_ID=1000 \
    USER_NAME=basic_user \
    GROUP_NAME=basic_group \
    SRC_ROOT=/srv/ibeam \
    OUTPUTS_DIR=/srv/outputs

ENV IBEAM_GATEWAY_DIR='/srv/clientportal.gw'
ENV IBEAM_CHROME_DRIVER_PATH='/srv/chrome_driver/chromedriver'
ENV IBEAM_CHROME_DRIVER_DIR='/srv/chrome_driver'

# we run as a separate user for security purposes
RUN addgroup -gid $GROUP_ID $GROUP_NAME
RUN adduser -disabled-password -u $USER_ID -gid $GROUP_ID $USER_NAME -shell /bin/sh

RUN mkdir -p $SRC_ROOT
RUN chown -R $USER_NAME:$GROUP_NAME $SRC_ROOT

RUN mkdir -p $OUTPUTS_DIR
RUN chown -R $USER_NAME:$GROUP_NAME $OUTPUTS_DIR

RUN mkdir -p $IBEAM_GATEWAY_DIR
RUN mkdir -p $IBEAM_CHROME_DRIVER_DIR

COPY copy_cache/clientportal.gw $IBEAM_GATEWAY_DIR
COPY copy_cache/chrome_driver $IBEAM_CHROME_DRIVER_DIR

RUN chown -R $USER_NAME:$GROUP_NAME $IBEAM_GATEWAY_DIR
RUN chown -R $USER_NAME:$GROUP_NAME $IBEAM_CHROME_DRIVER_DIR

ENV PYTHONPATH "${PYTHONPATH}:/srv/:/srv/ibeam"

#venv activation alias - not necessary but helps
RUN echo "/opt/venv/bin/activate" >> $SRC_ROOT/activate.sh

COPY ibeam $SRC_ROOT

WORKDIR $SRC_ROOT

USER $USER_NAME

#CMD python ./ibeam_starter.py
ENTRYPOINT ["/srv/ibeam/run.sh"]
#ENTRYPOINT ["bash"]
#CMD ["/bin/sh", "/srv/ibeam/run.sh"]
