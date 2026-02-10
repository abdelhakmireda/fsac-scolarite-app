import streamlit as st
import pandas as pd
import oracledb
import base64

# ==============================
# CONFIG ORACLE
# ==============================
HOST = "172.16.1.104"
PORT = 15211
SERVICE = "PROD"

oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_21_19")

# ==============================
# REQUÊTES SQL
# ==============================
QUERIES = {
    "Parcours Étudiant": """
WITH ModulesAvecSemestre AS (
    SELECT
        ind.COD_ETU                 AS code_etudiant,
        ind.LIB_NOM_PAT_IND         AS nom_famille,
        ind.LIB_PR1_IND             AS prenom,
        ind.DATE_NAI_IND            AS date_naissance,
        ind.CIN_IND                 AS cin,
        re.COD_ANU                  AS annee_universitaire,
        re.COD_ELP,
        ep.LIB_ELP,
        SUBSTR(re.COD_ELP, 5, 1)    AS num_semestre,

        /* 🔥 PRIORITÉ ABSOLUE ABI / ABJ */
        CASE
            WHEN SUM(
                 CASE
                     WHEN re.NOT_SUB_ELP IS NOT NULL THEN 1
                     ELSE 0
                 END
            ) > 0
            THEN MAX(re.NOT_SUB_ELP)
            ELSE TO_CHAR(MAX(re.NOT_ELP))
        END AS note_affichee,

        MAX(re.COD_TRE) AS cod_tre

    FROM RESULTAT_ELP re
    JOIN ELEMENT_PEDAGOGI ep
        ON re.COD_ELP = ep.COD_ELP
    LEFT JOIN INS_ADM_ETP iae
        ON re.COD_IND = iae.COD_IND
       AND re.COD_ANU = iae.COD_ANU
    JOIN INDIVIDU ind
        ON re.COD_IND = ind.COD_IND
    WHERE
        (
            ind.COD_ETU = CASE
                WHEN REGEXP_LIKE(:valeur, '^[0-9]+$')
                THEN TO_NUMBER(:valeur)
            END
            OR ind.CIN_IND = :valeur
        )
        AND ep.COD_NEL LIKE :cod_nel
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
    code_etudiant,
    nom_famille,
    prenom,
    date_naissance,
    cin,
    annee_universitaire AS annee,
    COD_ELP,
    LIB_ELP,
    'S' || num_semestre AS semestre,
    note_affichee,
    cod_tre
FROM ModulesAvecSemestre
ORDER BY
    annee_universitaire,
    num_semestre,
    COD_ELP
""",

    "Inscription Actuelle": """
SELECT DISTINCT
    i.COD_ETU AS APOGEE,
    i.LIB_NOM_PAT_IND AS NOM,
    i.LIB_PR1_IND AS PRENOM,
    i.CIN_IND AS CIN,
    iae.COD_DIP AS CODE_DIPLOME,
    d.LIB_DIP AS NOM_DIPLOME,
    iae.COD_ETP AS CODE_ETAPE,
    etp.LIB_ETP AS NOM_ETAPE,
    iae.COD_ANU AS ANNEE_INSCRIPTION
FROM
    INDIVIDU i
JOIN INS_ADM_ETP iae ON i.COD_IND = iae.COD_IND
JOIN DIPLOME d ON iae.COD_DIP = d.COD_DIP
JOIN ETAPE etp ON iae.COD_ETP = etp.COD_ETP
WHERE
    (i.COD_ETU = CASE WHEN REGEXP_LIKE(:valeur, '^[0-9]+$') THEN TO_NUMBER(:valeur) END
     OR UPPER(i.CIN_IND) = UPPER(:valeur))
    AND iae.ETA_IAE = 'E'
    AND (:annee IS NULL OR iae.COD_ANU = :annee)
ORDER BY ANNEE_INSCRIPTION DESC
"""
}

# ==============================
# UI STREAMLIT
# ==============================
st.set_page_config(
    page_title="Service Scolarité FSAC",
    page_icon="🎓",
    layout="wide"
)

# ==============================
# BACKGROUND
# ==============================
try:
    with open(r"C:\oracle\instantclient_21_19\FSAC_LOGO.jpg", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
except FileNotFoundError:
    base64_image = ""

st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        position: relative;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: absolute;
        inset: 0;
        background-image: url("data:image/jpg;base64,{base64_image}");
        background-size: cover;
        opacity: 0.3;
        z-index: -1;
    }}
    div.stButton > button {{
        background-color: red;
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================
# SIDEBAR
# ==============================
with st.sidebar:
    st.title("Service Scolarité FSAC")
    st.markdown("---")

    if "conn" in st.session_state:
        selected_action = st.selectbox(
            "Actions",
            ["Accueil", "Dashboard", "Parcours Étudiant", "Inscription Actuelle"]
        )
    else:
        st.info("Veuillez vous connecter pour accéder au menu.")
        selected_action = "Accueil"

# ==============================
# HEADER
# ==============================
st.title("🎓 Service Scolarité FSAC")
st.markdown("---")

if "conn" in st.session_state:
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("🚪 Déconnexion", type="primary"):
            del st.session_state["conn"]
            st.rerun()

# ==============================
# ACCUEIL
# ==============================
if selected_action == "Accueil":
    if "conn" not in st.session_state:
        col1, col2, col3 = st.columns(3)
        with col2:
            st.subheader("🔐 Connexion Oracle")
            user = st.text_input("👤 Utilisateur Oracle")
            password = st.text_input("🔒 Mot de passe", type="password")

            if st.button("Connexion"):
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")
            st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Bienvenue sur l'Application Service Scolarité FSAC")
    st.markdown("""
    **Fonctionnalités disponibles :**
    - Parcours académique détaillé
    - Inscription actuelle et historique (filière, étape, années)
    - Dashboard (en développement)
    """)
# ==============================
# PARCOURS ÉTUDIANT
# ==============================
elif selected_action == "Parcours Étudiant":

    st.subheader("🔎 Recherche Parcours Étudiant")

    col1, col2 = st.columns([3, 1])
    valeur = col1.text_input("CIN ou Code Apogée").strip().upper()

    type_affichage = st.radio(
        "Type d’affichage",
        ["Modules", "Semestres"],
        horizontal=True
    )

    cod_nel = "MO%" if type_affichage == "Modules" else "SM%"

    if col2.button("Afficher le parcours"):
        if valeur:
            cur = st.session_state["conn"].cursor()
            cur.execute(
                QUERIES["Parcours Étudiant"],
                valeur=valeur,
                cod_nel=cod_nel
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]

            if rows:
                st.session_state["df_parcours"] = pd.DataFrame(rows, columns=cols)
                st.success(f"{len(rows)} éléments trouvés")
            else:
                st.info("Aucun résultat trouvé")

    if "df_parcours" in st.session_state:
        df = st.session_state["df_parcours"]

        # ==============================
        # LOGIQUE STATUT APOGÉE (OFFICIELLE)
        # ==============================
        VALID_CODES = ["V", "VE", "AC", "VT", "VAR"]
        INVALID_CODES = ["ABI", "ABJ", "RAT"]
        IGNORED_CODES = ["NCR"]

        # Exclure NCR
        df = df[~df["COD_TRE"].isin(IGNORED_CODES)]

        # Validation
        df["MODULE_VALIDE"] = df["COD_TRE"].isin(VALID_CODES)

        grouped = df.groupby(["ANNEE", "SEMESTRE"]).agg(
            NB_MODULES=("COD_ELP", "count"),
            MODULES_VALIDES=("MODULE_VALIDE", "sum")
        ).reset_index()

        def statut_semestre(row):
            if row["NB_MODULES"] == row["MODULES_VALIDES"]:
                return "Validé"
            elif row["MODULES_VALIDES"] > 0:
                return "Partiel"
            else:
                return "Non validé"

        grouped["STATUT"] = grouped.apply(statut_semestre, axis=1)

        st.markdown("### Filtres")
        f1, f2 = st.columns(2)

        selected_annees = f1.multiselect(
            "Année(s)",
            sorted(df["ANNEE"].unique()),
            default=sorted(df["ANNEE"].unique())
        )

        selected_statuts = f2.multiselect(
            "Statut",
            ["Validé", "Partiel", "Non validé"],
            default=["Validé", "Partiel", "Non validé"]
        )

        filtered = grouped[
            grouped["ANNEE"].isin(selected_annees)
            & grouped["STATUT"].isin(selected_statuts)
        ]

        filtered_df = df.merge(
            filtered[["ANNEE", "SEMESTRE"]],
            on=["ANNEE", "SEMESTRE"]
        )

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            height=600
        )

# ------------------------------
# INSCRIPTION ACTUELLE
# ------------------------------
elif selected_action == "Inscription Actuelle":
    st.subheader("📋 Inscription(s) de l’étudiant (Filière & Étape)")

    col1, col2, col3 = st.columns([3, 1.5, 1])
    valeur = col1.text_input("CIN ou Code Apogée", key="inscription_input")
    valeur = valeur.strip().upper()

    annee_str = col2.text_input("Année universitaire (ex: 2024, vide = toutes)", key="annee_input")
    annee = int(annee_str) if annee_str.strip().isdigit() else None

    if col3.button("Rechercher", key="btn_inscription"):
        if not valeur:
            st.warning("Veuillez saisir un CIN ou Code Apogée")
        else:
            try:
                sql = QUERIES["Inscription Actuelle"]
                cur = st.session_state["conn"].cursor()
                cur.execute(sql, {'valeur': valeur, 'annee': annee})
                rows = cur.fetchall()
                cols = [c[0] for c in cur.description]

                if not rows:
                    st.info("Aucune inscription trouvée.")
                else:
                    df = pd.DataFrame(rows, columns=cols)
                    st.session_state["df_inscription"] = df
                    st.success(f"{len(df)} inscription(s) trouvée(s)")
            except Exception as e:
                st.error(f"Erreur lors de la requête : {e}")

    if "df_inscription" in st.session_state:
        df = st.session_state["df_inscription"]

        # Tableau récapitulatif avec colonnes en MAJUSCULES
        st.markdown("### Résultats")
        st.dataframe(
            df[['APOGEE', 'NOM', 'PRENOM', 'NOM_DIPLOME', 'NOM_ETAPE', 'ANNEE_INSCRIPTION']],
            column_config={
                'APOGEE': 'Code Apogée',
                'NOM': 'Nom',
                'PRENOM': 'Prénom',
                'NOM_DIPLOME': 'Filière / Diplôme',
                'NOM_ETAPE': 'Étape',
                'ANNEE_INSCRIPTION': 'Année'
            },
            hide_index=True,
            use_container_width=True
        )

        # Détails dans des expanders
        st.markdown("### Détails")
        for _, row in df.iterrows():
            with st.expander(f"{row['ANNEE_INSCRIPTION']} - {row['NOM']} {row['PRENOM']}"):
                st.markdown(f"**Code Apogée** : {row['APOGEE']}")
                st.markdown(f"**CIN** : {row['CIN'] if pd.notna(row['CIN']) else '—'}")
                st.markdown(f"**Filière / Diplôme** : {row['NOM_DIPLOME']} ({row['CODE_DIPLOME']})")
                st.markdown(f"**Étape** : {row['NOM_ETAPE']} ({row['CODE_ETAPE']})")

# Footer
st.markdown("---")
st.caption("© Faculté des Sciences Aïn Chock – Service Scolarité FSAC – Application interne")
