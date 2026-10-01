#!/usr/bin/env bash
# exit on error
set -o errexit

# Actualizar e instalar Graphviz en Render
apt-get update && apt-get install -y graphviz

# Instalar las librerías de Python
pip install -r requirements.txt