Voici le fichier **README.md** complet et prêt à l'emploi pour votre projet `fsac-scolarite-app`.  
Il est clair, structuré et guide parfaitement toute personne qui souhaite installer et utiliser l'application chez elle.

```markdown
# fsac-scolarite-app

**Application interne Streamlit** pour le **Service Scolarité** de la **Faculté des Sciences Aïn Chock (FSAC)**.

Permet de consulter facilement le parcours académique des étudiants : notes par module, validation des semestres (Validé / Partiel / Non validé), avec filtres par année universitaire et statut.

### Fonctionnalités principales
- Recherche d’étudiant par **CIN** ou **Code Apogée**
- Affichage du parcours détaillé (année, semestre, modules, notes, statut de validation)
- Filtres dynamiques : par année(s) et par statut de semestre
- Connexion sécurisée à la base de données Oracle
- Interface personnalisée avec fond d'écran FSAC et bouton de déconnexion
- Version portable via Docker

### Technologies
- **Python** 3.10+
- **Streamlit**
- **Pandas**
- **oracledb** + Oracle Instant Client 21.19
- **Docker** (optionnel, pour déploiement portable)

---

## Prérequis

| Composant                  | Description / Lien                                                                 |
|----------------------------|-------------------------------------------------------------------------------------|
| Python                     | 3.10 ou supérieur                                                                   |
| Docker                     | Optionnel – fortement recommandé pour portabilité (https://www.docker.com/)        |
| Oracle Instant Client      | Version **21.19 Basic Package** – [Télécharger ici](https://www.oracle.com/database/technologies/instant-client/downloads.html) |
| Accès à la base Oracle FSAC| Hôte, port, service, utilisateur et mot de passe                                    |

---

## Structure du projet


fsac-scolarite-app/
├── app.py                  # Code principal de l'application Streamlit
├── requirements.txt        # Dépendances Python
├── Dockerfile              # Pour construire l'image Docker
├── setup.sh                # Script d'installation locale
├── run.sh                  # Script pour lancer l'application localement
├── instantclient_21_19/    # Dossier contenant Oracle Instant Client (à copier ici)
│   ├── libclntsh.so*
│   ├── adrci
│   └── ... (tous les fichiers du client Oracle)
├── README.md               # Ce fichier
└── .gitignore


---

## Installation et lancement

### Méthode 1 : Lancement local (développement / test)

1. **Télécharger ou cloner le projet**
   ```bash
   git clone <URL-du-repo>
   cd fsac-scolarite-app
   ```

2. **Ajouter Oracle Instant Client**
   - Téléchargez et dézippez **Oracle Instant Client Basic 21.19** pour votre système
   - Placez le dossier dézippé (nommé `instantclient_21_19`) à la racine du projet

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

   ou avec le script :
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

4. **Lancer l’application**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

   → L’application s’ouvre dans votre navigateur :  
   `http://localhost:8501`

### Méthode 2 : Lancement avec Docker (portable, recommandé pour production)

1. **Construire l’image**
   ```bash
   docker build -t fsac-scolarite-app .
   ```

2. **Lancer le conteneur**
   ```bash
   docker run -p 8501:8501 fsac-scolarite-app
   ```

3. **Accéder à l’application**  
   `http://localhost:8501`

**Note** : Le Dockerfile télécharge automatiquement le client Oracle pour Linux. Si vous êtes sur Windows/Mac, modifiez le Dockerfile pour copier votre dossier local `instantclient_21_19`.

---

## Alias recommandés (facultatif)

Ajoutez à votre `~/.bashrc` ou `~/.zshrc` :

```bash
alias lancer_app='cd /chemin/vers/fsac-scolarite-app && ./run.sh'
alias build_fsac='docker build -t fsac-scolarite-app .'
alias run_fsac='docker run -p 8501:8501 fsac-scolarite-app'
```

Rechargez le shell :
```bash
source ~/.bashrc   # ou ~/.zshrc
```

Utilisation :
```bash
lancer_app
```

---

## Dépannage courant

| Problème                              | Solution                                                                 |
|---------------------------------------|--------------------------------------------------------------------------|
| `oracledb` ne trouve pas le client    | Vérifiez que `instantclient_21_19` est à la racine et chemin correct dans `app.py` |
| Erreur `libclntsh.so` (Linux)         | `export LD_LIBRARY_PATH=$PWD/instantclient_21_19:$LD_LIBRARY_PATH`       |
| Erreur de connexion Oracle            | Vérifiez HOST, PORT, SERVICE, utilisateur/mot de passe dans `app.py`     |
| Image FSAC_LOGO.jpg introuvable       | Assurez-vous qu’elle est bien dans `instantclient_21_19/`                |
| Docker échoue sur téléchargement      | Copiez manuellement `instantclient_21_19` dans l’image via Dockerfile    |

---

## Sécurité et utilisation

- **Usage strictement interne** : Ne partagez jamais cet outil publiquement.
- **Données sensibles** : La base Oracle contient des informations personnelles des étudiants.
- **Recommandation** : Utilisez un fichier `.env` ou des variables d’environnement pour les identifiants en production.

---

© 2025 – Service Scolarité  (AbdelhakmiReda)
Faculté des Sciences Aïn Chock  
Application interne – Tous droits réservés
```
