#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar graphviz a nivel de sistema si apt-get está disponible
apt-get update && apt-get install -y graphviz

# Instalar paquetes de Python
pip install -r requirements.txt