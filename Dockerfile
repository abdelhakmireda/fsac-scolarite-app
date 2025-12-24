# Utiliser une image de base Python
FROM python:3.12-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers du projet
COPY . /app

# Installer les dépendances système (pour oracledb)
RUN apt-get update && apt-get install -y libaio1 unzip wget && rm -rf /var/lib/apt/lists/*

# Télécharger et installer Oracle Instant Client (ajustez la version si besoin)
RUN wget https://download.oracle.com/otn_software/linux/instantclient/211900/instantclient-basic-linux.x64-21.19.0.0.0dbru.zip && \
    unzip instantclient-basic-linux.x64-21.19.0.0.0dbru.zip && \
    mv instantclient_21_19 /usr/lib/oracle/instantclient && \
    rm instantclient-basic-linux.x64-21.19.0.0.0dbru.zip && \
    echo "/usr/lib/oracle/instantclient" > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port Streamlit par défaut
EXPOSE 8501

# Commande pour lancer l'app (ajustez si besoin)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]