FROM python:3.7.7-slim-buster

# We will install packages to venv and then copy it
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p /usr/share/man/man1

RUN apt-get update && \
    apt-get install -y default-jre && \
    apt-get install -y ant && \
    apt-get clean;

# Setup JAVA_HOME -- useful for docker commandline
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/
RUN export JAVA_HOME

RUN apt-get install -y wget
WORKDIR /srv
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

#COPY copy_cache/google-chrome-stable_current_amd64.deb /srv/google-chrome-stable_current_amd64.deb
RUN apt install -y /srv/google-chrome-stable_current_amd64.deb
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf
RUN apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable

RUN apt-get install -y nano && \
    apt -y install curl && \
    apt-get -y install iputils-ping

COPY requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt

RUN chmod 744 /opt/venv/bin/activate

ENV GROUP_ID=1000 \
    USER_ID=1000 \
    USER_NAME=basic_user \
    GROUP_NAME=basic_group \
    SRC_ROOT=/srv/ibeam

ENV GATEWAY_PATH='/srv/clientportal.gw'
ENV CHROME_DRIVER_PATH='/srv/chrome_driver/chromedriver'
ENV CHROME_DRIVER_DIR='/srv/chrome_driver'

# we run as a separate user for security purposes
RUN addgroup -gid $GROUP_ID $GROUP_NAME
RUN adduser -disabled-password -u $USER_ID -gid $GROUP_ID $USER_NAME -shell /bin/sh

RUN mkdir -p $SRC_ROOT
RUN mkdir -p $GATEWAY_PATH
RUN mkdir -p $CHROME_DRIVER_DIR
RUN chown -R $USER_NAME:$GROUP_NAME $SRC_ROOT

COPY copy_cache/clientportal.gw $GATEWAY_PATH
COPY copy_cache/chrome_driver $CHROME_DRIVER_DIR

RUN chown -R $USER_NAME:$GROUP_NAME $GATEWAY_PATH
RUN chown -R $USER_NAME:$GROUP_NAME $CHROME_DRIVER_DIR

ENV PYTHONPATH "${PYTHONPATH}:/srv/:/srv/ibeam"

#venv activation alias - not necessary but helps
RUN echo "/opt/venv/bin/activate" >> $SRC_ROOT/activate.sh

COPY ibeam $SRC_ROOT

WORKDIR $SRC_ROOT

USER $USER_NAME

#CMD python ./ibeam_starter.py
#ENTRYPOINT ["bash"]
CMD ["/bin/sh", "/srv/ibeam/run.sh"]
