FROM alpine:latest AS build

RUN apk add unzip wget
RUN wget https://download2.interactivebrokers.com/portal/clientportal.gw.zip
RUN echo "2f2d380b2f9424520ff5f9c11fe45e82ef39459329ac056258a3274bea6f76f9 clientportal.gw.zip" | sha256sum -c  # check validity of the package
RUN unzip clientportal.gw.zip -d /tmp/ib-cpapi
RUN sed -i 's/131\.216\.\*/172\.\*/g' /tmp/ib-cpapi/root/conf.yaml  # add Docker private network addresses to whitelisted IPs



FROM python:3.11.3-slim-bullseye

ENV PATH="/opt/venv/bin:$PATH" \
    JAVA_HOME="/usr/lib/jvm/default-java" \
    USER_ID="1000" \
    GROUP_ID="1000" \
    USER_NAME="basic_user" \
    GROUP_NAME="basic_group" \
    SRC_ROOT="/srv/ibeam" \
    OUTPUTS_DIR="/srv/outputs" \
    IBEAM_GATEWAY_DIR="/srv/clientportal.gw" \
    IBEAM_CHROME_DRIVER_PATH="/usr/bin/chromedriver" \
    PYTHONPATH="${PYTHONPATH}:/srv:/srv/ibeam"

COPY requirements.txt /srv/requirements.txt

RUN \
    # Create python virtual environment and required directories
    python -m venv /opt/venv && \
    mkdir -p /usr/share/man/man1 $OUTPUTS_DIR $IBEAM_GATEWAY_DIR $SRC_ROOT && \
    # Create basic user
    addgroup --gid $GROUP_ID $GROUP_NAME && \
    adduser --disabled-password --gecos "" --uid $USER_ID --gid $GROUP_ID --shell /bin/bash $USER_NAME && \
    # Install apt packages
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y default-jre dbus-x11 xfonts-base xfonts-100dpi \
        xfonts-75dpi xfonts-cyrillic xfonts-scalable xorg xvfb gtk2-engines-pixbuf nano curl iputils-ping \
        chromium chromium-driver build-essential && \
    # Install python packages
    pip install --upgrade pip setuptools wheel && \
    pip install -r /srv/requirements.txt && \
    # Remove packages and package lists
    apt-get purge -y --auto-remove build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /tmp/ib-cpapi $IBEAM_GATEWAY_DIR
COPY ibeam $SRC_ROOT

RUN \
    # Create environment activation script
    echo "/opt/venv/bin/activate" >> $SRC_ROOT/activate.sh && \
    # Update file ownership and permissions
    chown -R $USER_NAME:$GROUP_NAME $SRC_ROOT $OUTPUTS_DIR $IBEAM_GATEWAY_DIR && \
    chmod 744 /opt/venv/bin/activate /srv/ibeam/run.sh $SRC_ROOT/activate.sh    

WORKDIR $SRC_ROOT

USER $USER_NAME

#CMD python ./ibeam_starter.py
#ENTRYPOINT ["/srv/ibeam/run.sh"]
#ENTRYPOINT ["bash"]
CMD ["/srv/ibeam/run.sh"]
