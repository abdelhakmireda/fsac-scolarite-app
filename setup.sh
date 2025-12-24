#!/bin/bash

echo "Installation des dépendances Python..."
pip install -r requirements.txt

echo "Configuration du client Oracle..."
# Ajoutez le chemin du client Oracle à LD_LIBRARY_PATH (pour exécution locale)
export LD_LIBRARY_PATH=$(pwd)/instantclient_21_19:$LD_LIBRARY_PATH
export PATH=$(pwd)/instantclient_21_19:$PATH

echo "Installation terminée. Utilisez './run.sh' pour lancer l'app."