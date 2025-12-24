#!/bin/bash

# Configurer le chemin Oracle si besoin
export LD_LIBRARY_PATH=$(pwd)/instantclient_21_19:$LD_LIBRARY_PATH
export PATH=$(pwd)/instantclient_21_19:$PATH

# Lancer Streamlit
streamlit run app.py