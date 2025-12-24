import streamlit as st
import pandas as pd
import oracledb
import base64
import os

# ==============================
# CONFIG ORACLE
# ==============================
HOST = "172.16.1.104"
PORT = 15211
SERVICE = "PROD"

lib_dir = os.path.join(os.path.dirname(__file__), 'instantclient_21_19')
oracledb.init_oracle_client(lib_dir=lib_dir)

# ==============================
# REQUÊTE SQL (Mise à jour pour Parcours Étudiant avec gestion de :valeur)
# ==============================
QUERIES = {
    "Parcours Étudiant": """
WITH ModulesAvecSemestre AS (
    SELECT
        -- 🔹 Informations étudiant (INDIVIDU)
        ind.COD_ETU,
        ind.LIB_NOM_PAT_IND AS nom_famille,
        ind.LIB_PR1_IND AS prenom,
        ind.DATE_NAI_IND AS date_naissance,
        ind.CIN_IND AS cin,
        -- 🔹 Informations pédagogiques
        re.COD_ANU AS annee_universitaire,
        re.COD_ELP,
        ep.LIB_ELP,
        SUBSTR(re.COD_ELP, 5, 1) AS num_semestre,
        MAX(re.NOT_ELP) AS note_module_finale,
        MAX(re.COD_TRE) AS cod_tre
    FROM RESULTAT_ELP re
    JOIN ELEMENT_PEDAGOGI ep
        ON re.COD_ELP = ep.COD_ELP
    JOIN INS_ADM_ETP iae
        ON re.COD_IND = iae.COD_IND
       AND re.COD_ANU = iae.COD_ANU
    JOIN INDIVIDU ind
        ON re.COD_IND = ind.COD_IND
    WHERE
        (ind.COD_ETU = CASE WHEN REGEXP_LIKE(:valeur, '^[0-9]+$') THEN TO_NUMBER(:valeur) END
         OR ind.CIN_IND = :valeur)
        AND ep.COD_NEL LIKE 'SM%'
        AND iae.ETA_IAE = 'E'
    GROUP BY
        ind.COD_ETU,
        ind.LIB_NOM_PAT_IND,
        ind.LIB_PR1_IND,
        ind.DATE_NAI_IND,
        ind.CIN_IND,
        re.COD_ANU,
        re.COD_ELP,
        ep.LIB_ELP
)
SELECT
    -- 🔹 Étudiant
    COD_ETU AS code_etudiant,
    nom_famille,
    prenom,
    date_naissance,
    cin,
    -- 🔹 Résultats pédagogiques
    annee_universitaire AS annee,
    COD_ELP,
    LIB_ELP,
    'S' || num_semestre AS semestre,
    note_module_finale,
    cod_tre
FROM ModulesAvecSemestre
ORDER BY
    annee_universitaire,
    num_semestre,
    COD_ELP
""",
    # Ajoutez d'autres requêtes ici, par exemple :
    # "Autre Action": """SELECT ...""",
}

# ==============================
# UI STREAMLIT
# ==============================
st.set_page_config(
    page_title="Service Scolarité FSAC",
    page_icon="🎓",
    layout="wide"
)

# Load background image
image_path = os.path.join(os.path.dirname(__file__), 'instantclient_21_19', 'FSAC_LOGO.jpg')
try:
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
except FileNotFoundError:
    base64_image = ""  # Fallback if image not found
    st.warning("Image de fond non trouvée.")

# Inject CSS for background with opacity and button style
st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        position: relative;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/jpg;base64,{base64_image}");
        background-size: cover;
        opacity: 0.3;
        z-index: -1;
    }}
    div.stButton > button:first-child {{
        background-color: red;
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar pour menu (seulement actions si connecté)
with st.sidebar:
    st.title("Service Scolarité FSAC")
    st.markdown("---")

    if "conn" in st.session_state:
        actions = ["Accueil", "Dashboard", "Parcours Étudiant"]  # Ajoutez d'autres actions ici
        selected_action = st.selectbox("Actions", actions)
    else:
        st.info("Veuillez vous connecter pour accéder au menu.")
        selected_action = "Accueil"  # Par défaut si non connecté

# Contenu principal
st.title("🎓 Service Scolarité FSAC")

st.markdown("---")

# Top bar pour déconnexion si connecté
if "conn" in st.session_state:
    col1, col2 = st.columns([5, 1])
    with col2:
        disconnect_btn = st.button("🚪 Déconnexion", type="primary")
        if disconnect_btn:
            del st.session_state["conn"]
            st.rerun()

if selected_action == "Accueil":
    if "conn" not in st.session_state:
        # Formulaire de connexion centré avec container semi-transparent
        col1, col2, col3 = st.columns(3)
        with col2:
            st.markdown('<div style="background-color: rgba(255,255,255,0.8); padding: 20px; border-radius: 10px;">', unsafe_allow_html=True)
            st.subheader("🔐 Connexion Oracle")
            user = st.text_input("👤 Utilisateur Oracle")
            password = st.text_input("🔒 Mot de passe", type="password")
            connect_btn = st.button("Connexion")
            st.markdown('</div>', unsafe_allow_html=True)

            if connect_btn:
                try:
                    conn = oracledb.connect(
                        user=user,
                        password=password,
                        host=HOST,
                        port=PORT,
                        service_name=SERVICE
                    )
                    st.session_state["conn"] = conn
                    st.success("Connexion réussie ✅")
                    st.rerun()  # Rafraîchir pour masquer le formulaire
                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")

    # Présentation de l'application
    st.subheader("Bienvenue sur l'Application Service Scolarité FSAC")
    st.markdown("""
    Cette application interne est destinée au personnel de la Faculté des Sciences Aïn Chock.
    
    **Fonctionnalités principales :**
    - Consultation des parcours académiques des étudiants.
    - Dashboard de statistiques (en développement).
    - Autres requêtes et actions à venir.
    
    Pour commencer, connectez-vous et sélectionnez une action dans la sidebar.
    """)

elif "conn" not in st.session_state:
    st.info("Veuillez vous connecter pour accéder à cette fonctionnalité.")

elif selected_action == "Dashboard":
    # Dashboard simple affichant le nombre de fonctionnalités
    st.subheader("📊 Dashboard")
    num_functionalities = len(QUERIES) + 1  # Exemple : nombre de requêtes + dashboard
    st.metric("Nombre de fonctionnalités disponibles", num_functionalities)
    st.markdown("""
    Ce dashboard affiche des statistiques globales sur l'application.
    
    - **Fonctionnalités actives :** Parcours Étudiant, etc.
    - Plus de stats à venir (ex: nombre d'étudiants interrogés, etc.).
    """)

elif selected_action == "Parcours Étudiant":
    # Logique pour Parcours Étudiant
    st.subheader("🔎 Recherche Parcours Étudiant")

    col1, col2 = st.columns([3, 1])
    valeur = col1.text_input("CIN ou Code Apogée")

    # 🔹 CIN TOUJOURS EN MAJUSCULE
    valeur = valeur.strip().upper()

    if col2.button("Afficher le parcours"):
        if not valeur:
            st.warning("Veuillez saisir un CIN ou Code Apogée")
        else:
            try:
                sql = QUERIES["Parcours Étudiant"]
                cur = st.session_state["conn"].cursor()
                cur.execute(sql, valeur=valeur)
                rows = cur.fetchall()
                cols = [c[0] for c in cur.description]

                if not rows:
                    st.info("Aucun résultat trouvé pour cet étudiant.")
                else:
                    df = pd.DataFrame(rows, columns=cols)
                    st.session_state["df_parcours"] = df  # Stocker le DF dans session_state pour filtrage
                    st.success(f"Résultats trouvés : {len(df)} lignes")

            except Exception as e:
                st.error(f"Erreur lors de la requête : {e}")

    # Affichage et filtrage si DF existe
    if "df_parcours" in st.session_state:
        df = st.session_state["df_parcours"]

        # Calcul du statut par semestre
        # Assumer que COD_TRE in ('V','AC','VAR','VE') signifie validé pour un module
        df['MODULE_VALIDE'] = df['COD_TRE'].isin(['V', 'AC', 'VAR', 'VE'])

        # Grouper par ANNEE et SEMESTRE pour calculer le statut
        grouped = df.groupby(['ANNEE', 'SEMESTRE']).agg(
            NB_MODULES=('COD_ELP', 'count'),
            MODULES_VALIDES=('MODULE_VALIDE', 'sum')
        ).reset_index()

        grouped['STATUT'] = grouped.apply(
            lambda row: 'Validé' if row['MODULES_VALIDES'] == row['NB_MODULES'] else 
                        'Partiel' if row['MODULES_VALIDES'] > 0 else 
                        'Non validé', 
            axis=1
        )

        # Filtres
        st.markdown("### Filtres")
        col_f1, col_f2 = st.columns(2)

        # Filtre par année
        unique_annees = sorted(df['ANNEE'].unique())
        selected_annees = col_f1.multiselect("Filtrer par année(s)", unique_annees, default=unique_annees)

        # Filtre par statut de semestre
        unique_statuts = ['Validé', 'Partiel', 'Non validé']
        selected_statuts = col_f2.multiselect("Filtrer par statut de semestre", unique_statuts, default=unique_statuts)

        # Appliquer filtres sur grouped pour statuts, puis filtrer df en conséquence
        filtered_grouped = grouped[
            (grouped['ANNEE'].isin(selected_annees)) &
            (grouped['STATUT'].isin(selected_statuts))
        ]

        # Obtenir les combinaisons ANNEE-SEMESTRE filtrées
        filtered_combos = filtered_grouped[['ANNEE', 'SEMESTRE']].drop_duplicates()

        # Filtrer df original basé sur ces combinaisons
        filtered_df = df.merge(filtered_combos, on=['ANNEE', 'SEMESTRE'])

        # Afficher le tableau filtré
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

# Ajoutez d'autres elif pour d'autres actions/requêtes ici
# Exemple :
# elif selected_action == "Autre Action":
#     # Logique similaire avec QUERIES["Autre Action"]

# 📌 FOOTER
st.markdown("---")
st.caption("© Faculté des Sciences Aïn Chock – Service Scolarité FSAC – Application interne")