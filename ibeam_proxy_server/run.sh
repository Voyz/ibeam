if [ $# -ne 1 ]; then
    echo "usage: proxy.sh start|config"
    exit 1
fi

action=$1

if [ "$action" = "start" ]; then
    uwsgi -w src.proxy_server:server --processes 4 --http ${IBEAM_PROXY_SERVER_HTTP:="0.0.0.0:8080"} --master --enable-threads --http-timeout ${IBEAM_PROXY_SERVER_HTTP_TIMEOUT:=120} --socket-timeout ${IBEAM_PROXY_SERVER_SOCKET_TIMEOUT:=120}
fi

if [ "$action" = "config" ]; then
    python src/proxy_server_config.py 
fi
