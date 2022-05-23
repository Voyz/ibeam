FROM python:3.7.7-slim-buster

<<<<<<< HEAD
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p /usr/share/man/man1

RUN apt-get update && \
    apt-get install -y default-jre && \
    apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf && \
    rm -rf /var/lib/apt/lists/*

# uwsgi, adapted from https://github.com/docker-library/python.git
RUN set -ex \
    && buildDeps=' \
        gcc \
        libbz2-dev \
        libc6-dev \
        libgdbm-dev \
        liblzma-dev \
        libncurses-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        libpcre3-dev \
        make \
        tcl-dev \
        tk-dev \
        wget \
        xz-utils \
        zlib1g-dev \
    ' \
    && deps=' \
        libexpat1 \
    ' \
    && apt-get update && apt-get install -y $buildDeps $deps --no-install-recommends  && rm -rf /var/lib/apt/lists/* \
    && pip install uwsgi \
    && apt-get purge -y --auto-remove $buildDeps \
    && find /usr/local -depth \
    \( \
        \( -type d -a -name test -o -name tests \) \
        -o \
        \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
    \) -exec rm -rf '{}' +

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
=======
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
>>>>>>> upstream/master

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

COPY copy_cache/clientportal.gw $IBEAM_GATEWAY_DIR
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
