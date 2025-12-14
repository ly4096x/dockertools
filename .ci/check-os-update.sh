#!/bin/sh
set -e

OS_ID=`egrep '^ID=' /etc/os-release |cut -f2 -d'='`
echo Detected OS $OS_ID

case $OS_ID in
    alpine)
        apk update
        apk -u list

        [ "$(apk -u list |wc -l)" == "0" ]
        ;;
    *)
        echo Unknown OS $OS_ID
        exit 1
        ;;
esac
