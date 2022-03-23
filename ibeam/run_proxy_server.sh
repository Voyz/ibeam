#!/bin/sh
#no daemon for docker entrypoint override
uwsgi -w src.proxy_server:server --processes 4 --http $IBEAM_PROXY_SERVER_HTTP --master --enable-threads --http-timeout 120 --socket-timeout 120