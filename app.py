import streamlit as st
import pandas as pd
import io
import csv
import math

from src.db import init_oracle_client, create_pool, close_pool, run_query_df, run_exec, build_ident_filter
from src.ui import ensure_state, load_file_b64, apply_css, navbar, sidebar, touch_stats
from src.queries import SQL_PARCOURS_TEMPLATE, SQL_INSCRIPTION_TEMPLATE, SQL_ABI_TEMPLATE,SQL_ARCHIVE_TEMPLATE, SQL_EXPORT_APOGEE_LIKE,SQL_SEMESTRES_MODULES_CREDITS,SQL_UPDATE_CREDIT_MODULE
from src.config import LOGO_PATH

# ==============================
# STREAMLIT CONFIG
# ==============================
st.set_page_config(
    page_title="Service Scolarité FSAC",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# INIT
# ==============================
init_oracle_client()
ensure_state()

logo_b64 = load_file_b64(LOGO_PATH)

# ==============================
# AUTH STATE
# ==============================
def is_logged_in():
    return "pool" in st.session_state and st.session_state.get("oracle_user")

def do_logout():
    if "pool" in st.session_state:
        close_pool(st.session_state["pool"])
    for k in ["pool", "oracle_user", "df_parcours", "df_inscription", "df_abi", "last_student"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

logged = is_logged_in()
oracle_user = st.session_state.get("oracle_user", "")

# ==============================
# NAVBAR + SIDEBAR (theme choice happens in sidebar)
# ==============================
navbar(logged, oracle_user, do_logout)
page = sidebar(logged, oracle_user)

# ==============================
# APPLY CSS AFTER SIDEBAR (so theme is already chosen)
# ==============================
apply_css("styles/base.css", logo_b64)

# ==============================
# PAGES
# ==============================
if page == "Accueil":
    st.markdown("## 👋 Bienvenue")

    if not logged:
        st.markdown('<div style="max-width:560px;margin:0 auto;">', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<div class='card-title'>🔐 Connexion Oracle</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-sub'>Saisis tes identifiants Oracle</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            user = st.text_input("👤 Utilisateur Oracle")
            password = st.text_input("🔒 Mot de passe", type="password")
            ok = st.form_submit_button("Connexion", use_container_width=True)

        if ok:
            try:
                pool = create_pool(user, password)
                st.session_state["pool"] = pool
                st.session_state["oracle_user"] = user
                touch_stats("Connexion")
                st.success("Connexion réussie ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur de connexion : {e}")

        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        """
**Fonctionnalités :**
- 🧾 Parcours académique détaillé (Modules / Semestres)
- 📋 Inscriptions (filière, étape, année)
- 🚫 Étudiants ABI / ABJ (filtrable)
- 📊 Dashboard (cartes + stats d’usage)
"""
    )

elif page == "Dashboard":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        s = st.session_state["stats"]
        last_student = st.session_state.get("last_student", "—")

        st.markdown("## 📊 Dashboard")
        c1, c2, c3, c4 = st.columns(4)

        def kpi(col, title, value, sub):
            col.markdown(
                f"""
<div class="card">
  <div class="card-title">{title}</div>
  <div style="font-size:1.6rem;font-weight:900;margin-top:.25rem;">{value}</div>
  <div class="card-sub">{sub}</div>
</div>
""",
                unsafe_allow_html=True
            )

        kpi(c1, "🧾 Parcours", s["parcours"], "Requêtes exécutées")
        kpi(c2, "📋 Inscriptions", s["inscription"], "Requêtes exécutées")
        kpi(c3, "🚫 ABI/ABJ", s["abi"], "Requêtes exécutées")
        kpi(c4, "👤 Dernier", last_student, f"Dernière action: {s['last_action']}")

elif page == "Parcours Étudiant":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        st.markdown("## 🧾 Parcours Étudiant")
        col1, col2 = st.columns([3, 2])

        valeur = col1.text_input("CIN ou Code Apogée", key="parcours_valeur").strip().upper()
        type_aff = col2.radio("Type d’affichage", ["Modules", "Semestres"], horizontal=True)
        cod_nel = "MO%" if type_aff == "Modules" else "SM%"

        if st.button("Afficher le parcours", type="primary"):
            if not valeur:
                st.warning("Veuillez saisir un CIN ou Code Apogée.")
            else:
                ident_filter, binds = build_ident_filter(valeur, "ind")
                if not ident_filter:
                    st.warning("Identifiant invalide.")
                else:
                    sql = SQL_PARCOURS_TEMPLATE.replace("{IDENT_FILTER}", ident_filter)
                    binds["cod_nel"] = cod_nel

                    try:
                        df = run_query_df(st.session_state["pool"], sql, binds)
                        if df.empty:
                            st.info("Aucun résultat trouvé.")
                        else:
                            st.session_state["df_parcours"] = df
                            st.session_state["stats"]["parcours"] += 1
                            touch_stats("Parcours")
                            st.session_state["last_student"] = str(df.iloc[0].get("CODE_ETUDIANT", valeur))
                            st.success(f"{len(df)} éléments trouvés ✅")
                    except Exception as e:
                        st.error(f"Erreur Oracle : {e}")

        if "df_parcours" in st.session_state:
            df = st.session_state["df_parcours"].copy()

            VALID_CODES = ["V", "VE", "AC", "VT", "VAR"]
            IGNORED_CODES = ["NCR"]

            df = df[~df["COD_TRE"].isin(IGNORED_CODES)]
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
                return "Non validé"

            grouped["STATUT"] = grouped.apply(statut_semestre, axis=1)

            st.markdown("### 🎚️ Filtres")
            f1, f2 = st.columns(2)

            selected_annees = f1.multiselect(
                "Année(s)",
                sorted(grouped["ANNEE"].unique()),
                default=sorted(grouped["ANNEE"].unique())
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

            filtered_df = df.merge(filtered[["ANNEE", "SEMESTRE"]], on=["ANNEE", "SEMESTRE"])
            st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=600)

elif page == "Inscription Actuelle":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        st.markdown("## 📋 Inscription(s) de l’étudiant")

        c1, c2, c3 = st.columns([3, 2, 1])
        valeur = c1.text_input("CIN ou Code Apogée", key="insc_valeur").strip().upper()
        annee_str = c2.text_input("Année universitaire (ex: 2024, vide = toutes)", key="insc_annee")
        annee = int(annee_str) if annee_str.strip().isdigit() else None

        if c3.button("Rechercher", type="primary"):
            if not valeur:
                st.warning("Veuillez saisir un CIN ou Code Apogée")
            else:
                ident_filter, binds = build_ident_filter(valeur, "i")
                if not ident_filter:
                    st.warning("Identifiant invalide.")
                else:
                    sql = SQL_INSCRIPTION_TEMPLATE.replace("{IDENT_FILTER}", ident_filter)
                    binds["annee"] = annee

                    try:
                        df = run_query_df(st.session_state["pool"], sql, binds)
                        if df.empty:
                            st.info("Aucune inscription trouvée.")
                            if "df_inscription" in st.session_state:
                                del st.session_state["df_inscription"]
                        else:
                            st.session_state["df_inscription"] = df
                            st.session_state["stats"]["inscription"] += 1
                            touch_stats("Inscription")
                            st.session_state["last_student"] = str(df.iloc[0].get("APOGEE", valeur))
                            st.success(f"{len(df)} inscription(s) trouvée(s) ✅")
                    except Exception as e:
                        st.error(f"Erreur lors de la requête : {e}")

        if "df_inscription" in st.session_state:
            df = st.session_state["df_inscription"]

            # ==============================
            # 1) TABLEAU RÉSUMÉ (comme avant)
            # ==============================
            st.markdown("### 📌 Résultats")
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

            # ==============================
            # 2) DÉTAILS (expanders) (comme avant)
            # ==============================
            st.markdown("### 🔎 Détails")
            for _, row in df.iterrows():
                titre = f"{row['ANNEE_INSCRIPTION']} — {row['NOM']} {row['PRENOM']}"
                with st.expander(titre):
                    st.markdown(f"**Code Apogée** : {row['APOGEE']}")
                    st.markdown(f"**CIN** : {row['CIN'] if pd.notna(row['CIN']) else '—'}")

                    st.markdown(
                        f"**Filière / Diplôme** : {row['NOM_DIPLOME']} "
                        f"(**{row['CODE_DIPLOME']}**)"
                    )

                    st.markdown(
                        f"**Étape** : {row['NOM_ETAPE']} "
                        f"(**{row['CODE_ETAPE']}**)"
                    )

                    st.markdown(f"**Année inscription** : {row['ANNEE_INSCRIPTION']}")

elif page == "Étudiants ABI":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        st.markdown("## 🚫 Étudiants avec ABI / ABJ")

        col1, col2, col3 = st.columns([3, 2, 1])
        valeur = col1.text_input("Code Apogée ou CIN (optionnel)", key="abi_valeur").strip().upper()
        module = col2.text_input("Code module (ex: FL%, MA%, SM%)", key="abi_module").strip().upper()

        if col3.button("Rechercher", type="primary"):
            try:
                binds = {}
                ident_extra = ""
                module_extra = ""

                if valeur:
                    ident_filter, b = build_ident_filter(valeur, "ind")
                    if ident_filter:
                        ident_extra = f" AND ({ident_filter})"
                        binds.update(b)

                if module:
                    module_extra = " AND re.COD_ELP LIKE :module"
                    binds["module"] = module

                sql = SQL_ABI_TEMPLATE.format(
                    IDENT_EXTRA=ident_extra,
                    MODULE_EXTRA=module_extra
                )

                df = run_query_df(st.session_state["pool"], sql, binds)

                if df.empty:
                    st.info("Aucun étudiant avec ABI / ABJ trouvé.")
                else:
                    st.session_state["df_abi"] = df
                    st.session_state["stats"]["abi"] += 1
                    touch_stats("ABI/ABJ")
                    st.success(f"{len(df)} étudiant(s) trouvé(s) ✅")
                    st.dataframe(df, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Erreur Oracle : {e}")
elif page == "Archive Apogée":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        st.markdown("## 🗂️ Archive Apogée (CSV / Oracle)")

        # --------------------------
        # Helpers
        # --------------------------
        def parse_mixed_date(s):
            """Parse YYYY-MM-DD OR DD/MM/YY OR DD/MM/YYYY. Return Timestamp or NaT."""
            if pd.isna(s) or str(s).strip() == "":
                return pd.NaT
            s = str(s).strip()

            # 1) ISO YYYY-MM-DD
            dt = pd.to_datetime(s, errors="coerce", format="%Y-%m-%d")
            if not pd.isna(dt):
                return dt

            # 2) FR formats (DD/MM/YY or DD/MM/YYYY) + autres variantes
            return pd.to_datetime(s, errors="coerce", dayfirst=True)

        # --------------------------
        # Inputs
        # --------------------------
        t1, t2, t3 = st.columns([2, 2, 1])

        ident = t1.text_input("Apogée ou CIN (optionnel)", key="arch_ident").strip().upper()

        filiere = t2.text_input("Filière (LIKE) (vide => FL%)", key="arch_filiere").strip().upper()
        if not filiere:
            filiere = "FL%"

        max_rows = t3.number_input("Max lignes (0 = illimité)", min_value=0, value=50000, step=1000)

        c1, c2 = st.columns([1, 1])

        # --------------------------
        # 1) Recherche Oracle
        # --------------------------
        if c1.button("🔎 Charger depuis Oracle", type="primary"):
            binds = {
                "ident": ident if ident else None,
                "filiere": filiere
            }

            try:
                df = run_query_df(st.session_state["pool"], SQL_ARCHIVE_TEMPLATE, binds)

                # Convertir DATE_NAISSANCE si elle existe (Oracle peut renvoyer date, str, etc.)
                if "DATE_NAISSANCE" in df.columns:
                    df["DATE_NAISSANCE"] = df["DATE_NAISSANCE"].apply(parse_mixed_date)

                # Limitation côté app (si on ne veut pas toucher SQL)
                if max_rows and len(df) > int(max_rows):
                    df = df.head(int(max_rows))
                    st.info(f"Affichage limité à {int(max_rows)} lignes (sur un total plus grand).")

                if df.empty:
                    st.info("Aucun résultat.")
                    if "df_archive" in st.session_state:
                        del st.session_state["df_archive"]
                else:
                    st.session_state["df_archive"] = df
                    st.success(f"{len(df)} lignes affichées ✅")

            except Exception as e:
                st.error(f"Erreur Oracle : {e}")

        # --------------------------
        # 2) Import CSV UTF-8
        # --------------------------
        uploaded = c2.file_uploader("📥 Importer un CSV (UTF-8)", type=["csv"])
        if uploaded is not None:
            try:
                # Astuce : certains CSV Excel ont besoin de utf-8-sig
                try:
                    df_csv = pd.read_csv(
                        uploaded,
                        sep=";",
                        encoding="utf-8",
                        dtype=str,
                        keep_default_na=False
                    )
                except UnicodeDecodeError:
                    uploaded.seek(0)
                    df_csv = pd.read_csv(
                        uploaded,
                        sep=";",
                        encoding="utf-8-sig",
                        dtype=str,
                        keep_default_na=False
                    )

                # Convertir DATE_NAISSANCE si elle existe (CSV = string)
                if "DATE_NAISSANCE" in df_csv.columns:
                    df_csv["DATE_NAISSANCE"] = df_csv["DATE_NAISSANCE"].apply(parse_mixed_date)

                st.session_state["df_archive"] = df_csv
                st.success(f"CSV importé : {len(df_csv)} lignes ✅")

            except Exception as e:
                st.error(f"Erreur lecture CSV : {e}")

        # --------------------------
        # Affichage + filtres locaux + export
        # --------------------------
        if "df_archive" in st.session_state:
            df = st.session_state["df_archive"].copy()

            # Filtre local ident (utile même pour CSV)
            if ident:
                cols = {c.upper(): c for c in df.columns}
                ap_col = cols.get("APOGEE")
                cin_col = cols.get("CIN")

                if ap_col and cin_col:
                    df = df[
                        (df[ap_col].astype(str).str.upper() == ident)
                        | (df[cin_col].astype(str).str.upper() == ident)
                    ]
                elif ap_col:
                    df = df[df[ap_col].astype(str).str.upper() == ident]
                elif cin_col:
                    df = df[df[cin_col].astype(str).str.upper() == ident]
                else:
                    st.warning("Le fichier/jeu de données ne contient pas les colonnes APOGEE ou CIN pour filtrer.")

            # Affichage date en string propre (optionnel)
            if "DATE_NAISSANCE" in df.columns:
                # Timestamp -> string YYYY-MM-DD (laisse vide si NaT)
                df["DATE_NAISSANCE"] = df["DATE_NAISSANCE"].dt.strftime("%Y-%m-%d")

            st.markdown("### 📌 Résultats")
            st.dataframe(df, use_container_width=True, hide_index=True, height=600)

            # Export CSV propre (UTF-8 + quoting + line terminator)
            st.markdown("### ⬇️ Export")
            buf = io.StringIO()
            df.to_csv(
                buf,
                index=False,
                sep=";",
                encoding="utf-8",
                na_rep="",
                quoting=csv.QUOTE_ALL,
                lineterminator="\n"
            )
            st.download_button(
                "Télécharger CSV (UTF-8)",
                data=buf.getvalue().encode("utf-8"),
                file_name="archive_apogee.csv",
                mime="text/csv"
            )
elif page == "Export Notes":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        st.markdown("## 📤 Export Apogée — format (Numéro + modules en triplets Note/Barème/Résultat)")

        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])

        annee = c1.text_input("Année (ex: 2025)", key="exp_annee").strip()
        ident = c2.text_input("Apogée ou CIN (optionnel)", key="exp_ident").strip().upper()
        filiere = c3.text_input("Filière (LIKE) ex: FLPC% (vide => FL%)", key="exp_filiere").strip().upper()
        session = c4.selectbox("Session", ["Toutes", "1", "2"], index=0)

        if not filiere:
            filiere = "FL%"

        p_ses = None if session == "Toutes" else int(session)

        if st.button("🔎 Générer export", type="primary"):
            if not annee.isdigit():
                st.warning("Année invalide.")
            else:
                binds = {
                    "p_annee": int(annee),
                    "p_filiere": filiere,
                    "p_ident": ident if ident else None,
                    "p_ses": p_ses
                }

                try:
                    df_long = run_query_df(st.session_state["pool"], SQL_EXPORT_APOGEE_LIKE, binds)

                    if df_long.empty:
                        st.info("Aucun résultat.")
                        st.session_state.pop("df_export_apogee", None)
                    else:
                        # ---- pivot comme export Apogée (triplets)
                        base_cols = ["NUMERO", "NOM", "PRENOM", "NAISSANCE"]

                        # On crée une colonne “clé module” (comme dans ton fichier : code module)
                        df_long["MODULE"] = df_long["COD_ELP"].astype(str)

                        # Pivot NOTE
                        p_note = df_long.pivot_table(
                            index=base_cols, columns="MODULE", values="NOTE", aggfunc="first"
                        )
                        p_note.columns = [f"{m} NOTE" for m in p_note.columns]

                        # Pivot BAREME
                        p_bar = df_long.pivot_table(
                            index=base_cols, columns="MODULE", values="BAREME", aggfunc="first"
                        )
                        p_bar.columns = [f"{m} BAREME" for m in p_bar.columns]

                        # Pivot RESULTAT
                        p_res = df_long.pivot_table(
                            index=base_cols, columns="MODULE", values="RESULTAT", aggfunc="first"
                        )
                        p_res.columns = [f"{m} RESULTAT" for m in p_res.columns]

                        df_wide = pd.concat([p_note, p_bar, p_res], axis=1).reset_index()

                        # ---- IMPORTANT : ordre des colonnes = Note/Barème/Résultat par module
                        # On reconstruit l'ordre : pour chaque module : NOTE, BAREME, RESULTAT
                        modules = sorted(df_long["MODULE"].unique().tolist())
                        ordered_cols = base_cols.copy()
                        for m in modules:
                            ordered_cols += [f"{m} NOTE", f"{m} BAREME", f"{m} RESULTAT"]

                        # Certaines colonnes peuvent manquer si module absent => on garde celles existantes
                        ordered_cols = [c for c in ordered_cols if c in df_wide.columns]
                        df_wide = df_wide[ordered_cols]

                        st.session_state["df_export_apogee"] = df_wide
                        st.success(f"Export prêt ✅ ({len(df_wide)} étudiants)")

                except Exception as e:
                    st.error(f"Erreur Oracle : {e}")

        if "df_export_apogee" in st.session_state:
            df = st.session_state["df_export_apogee"].copy()

            st.markdown("### 📌 Aperçu (format Apogée)")
            st.dataframe(df, use_container_width=True, hide_index=True, height=600)

            st.markdown("### ⬇️ Télécharger")
            buf = io.StringIO()
            df.to_csv(
                buf,
                index=False,
                sep=";",
                encoding="utf-8",
                na_rep="",
                quoting=csv.QUOTE_ALL,
                lineterminator="\n"
            )

            st.download_button(
                "⬇️ Télécharger CSV UTF-8",
                data=buf.getvalue().encode("utf-8"),
                file_name=f"export_apogee_like_{annee}_{filiere.replace('%','')}.csv",
                mime="text/csv"
            )
elif page == "Crédits Modules":
    if not logged:
        st.warning("Veuillez vous connecter.")
    else:
        st.markdown("## 📚 Semestres → Modules → Crédits (édition)")

        # ==========================
        # État
        # ==========================
        if "df_credits_modules" not in st.session_state:
            st.session_state["df_credits_modules"] = None
        if "open_add_modal" not in st.session_state:
            st.session_state["open_add_modal"] = False

        # ==========================
        # Helpers
        # ==========================
        def norm_credit(x):
            """Retourne float ou None (gère None/NaN/''/'3,5')."""
            if x is None:
                return None
            try:
                # NaN pandas
                if pd.isna(x):
                    return None
            except Exception:
                pass

            s = str(x).strip()
            if s == "" or s.lower() in ("nan", "none"):
                return None
            s = s.replace(",", ".")
            try:
                return float(s)
            except Exception:
                return None

        def compute_semestre_from_cod(cod_elp: str) -> str:
            """
            Semestre à partir du code module (ex: FLPC S1 -> caractère position 5)
            Adapte si ton format diffère.
            """
            cod_elp = (cod_elp or "").strip().upper()
            if len(cod_elp) >= 5 and cod_elp[4].isdigit():
                return "S" + cod_elp[4]
            return "S?"

        # ==========================
        # Inputs
        # ==========================
        c1, c2, c3 = st.columns([2, 1, 1])
        filiere = c1.text_input("Filière (LIKE) ex: FLPC% (vide => FL%)", key="cred_filiere").strip().upper()
        if not filiere:
            filiere = "FL%"

        mode = c2.selectbox("Mode", ["Oracle (sauvegarde)", "Local (sans sauvegarde)"], index=0)
        editable = c3.checkbox("Activer édition", value=True)

        # ==========================
        # Charger depuis Oracle
        # ==========================
        if st.button("🔎 Charger modules/crédits", type="primary"):
            try:
                df = run_query_df(
                    st.session_state["pool"],
                    SQL_SEMESTRES_MODULES_CREDITS,
                    {"p_filiere": filiere}
                )
                if df.empty:
                    st.session_state["df_credits_modules"] = None
                    st.info("Aucun module trouvé.")
                else:
                    # normaliser types
                    if "CREDITS" in df.columns:
                        df["CREDITS"] = df["CREDITS"].apply(norm_credit)
                    st.session_state["df_credits_modules"] = df
                    st.success(f"{len(df)} module(s) chargés ✅")
            except Exception as e:
                st.error(f"Erreur Oracle : {e}")

        df0 = st.session_state.get("df_credits_modules")

        # ==========================
        # Zone d'ajout (popup modal)
        # ==========================
        if df0 is not None:
            st.markdown("---")
            colA, colB = st.columns([1, 4])
            if colA.button("➕ Ajouter un module"):
                st.session_state["open_add_modal"] = True

            if st.session_state.get("open_add_modal"):
                with st.modal("➕ Ajouter un module (MO)"):
                    cod = st.text_input("COD_ELP (ex: FLPC...)", key="add_cod_elp").strip().upper()
                    lib = st.text_input("LIB_ELP (nom du module)", key="add_lib_elp").strip()

                    # ✅ popup crédits (choix rapide)
                    p1, p2 = st.columns([2, 2])
                    credits_preset = p1.selectbox(
                        "Crédits (valeurs rapides)",
                        [0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0],
                        index=6
                    )
                    credits = p2.number_input("Ou saisir manuellement", min_value=0.0, value=float(credits_preset), step=0.5)

                    c1m, c2m = st.columns(2)
                    if c1m.button("✅ Enregistrer"):
                        if not cod or not lib:
                            st.warning("COD_ELP et LIB_ELP sont obligatoires.")
                        else:
                            sem = compute_semestre_from_cod(cod)

                            if mode.startswith("Oracle"):
                                try:
                                    run_exec(
                                        st.session_state["pool"],
                                        SQL_INSERT_MODULE_MINI,
                                        {
                                            "p_cod_elp": cod,
                                            "p_lib_elp": lib,
                                            "p_credits": float(credits),
                                            # si ton insert a besoin du semestre, ajoute le bind ici
                                        }
                                    )
                                    st.success("Module ajouté ✅")
                                except Exception as e:
                                    st.error(f"Erreur Oracle (insert) : {e}")
                                    st.stop()

                                # reload oracle
                                df = run_query_df(
                                    st.session_state["pool"],
                                    SQL_SEMESTRES_MODULES_CREDITS,
                                    {"p_filiere": filiere}
                                )
                                if "CREDITS" in df.columns:
                                    df["CREDITS"] = df["CREDITS"].apply(norm_credit)
                                st.session_state["df_credits_modules"] = df
                            else:
                                # local add
                                df = st.session_state["df_credits_modules"].copy()
                                df.loc[len(df)] = [sem, cod, lib, float(credits)]
                                st.session_state["df_credits_modules"] = df

                            st.session_state["open_add_modal"] = False
                            st.rerun()

                    if c2m.button("❌ Fermer"):
                        st.session_state["open_add_modal"] = False
                        st.rerun()

        # ==========================
        # Affichage + édition (grid)
        # ==========================
        if df0 is not None:
            df = df0.copy()

            st.markdown("### ✏️ Édition des crédits")
            st.caption("Modifie la colonne **CREDITS** puis clique sur **Sauvegarder**.")

            # ✅ grid: CREDITS required => évite None
            edited = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                disabled=not editable,
                column_config={
                    "SEMESTRE": st.column_config.TextColumn("Semestre", disabled=True),
                    "COD_ELP": st.column_config.TextColumn("Code module", disabled=True),
                    "LIB_ELP": st.column_config.TextColumn("Nom module", disabled=True),
                    "CREDITS": st.column_config.NumberColumn("Crédits", min_value=0.0, step=0.5, required=False),
                },
                key="grid_credits"
            )

            # normaliser après édition (si user vide une cellule)
            if "CREDITS" in edited.columns:
                edited["CREDITS"] = edited["CREDITS"].apply(norm_credit)

            # ==========================
            # Suppression
            # ==========================
            st.markdown("### 🗑️ Supprimer un module")
            cod_to_delete = st.text_input("COD_ELP à supprimer (optionnel)", key="del_cod").strip().upper()

            if st.button("🗑️ Supprimer", disabled=(not cod_to_delete)):
                if mode.startswith("Oracle"):
                    try:
                        run_exec(
                            st.session_state["pool"],
                            SQL_DELETE_MODULE,
                            {"p_cod_elp": cod_to_delete}
                        )
                        st.success("Supprimé ✅")
                    except Exception as e:
                        st.error(f"Erreur Oracle (delete) : {e}")
                        st.stop()

                    df_reload = run_query_df(
                        st.session_state["pool"],
                        SQL_SEMESTRES_MODULES_CREDITS,
                        {"p_filiere": filiere}
                    )
                    if "CREDITS" in df_reload.columns:
                        df_reload["CREDITS"] = df_reload["CREDITS"].apply(norm_credit)
                    st.session_state["df_credits_modules"] = df_reload
                    st.rerun()
                else:
                    df_local = edited[edited["COD_ELP"].astype(str).str.upper() != cod_to_delete].copy()
                    st.session_state["df_credits_modules"] = df_local
                    st.success("Supprimé (local) ✅")
                    st.rerun()

            # ==========================
            # Sauvegarde Oracle (diff only) — FIX NoneType
            # ==========================
            st.markdown("### 💾 Sauvegarde")
            null_policy = st.selectbox(
                "Si la cellule Crédits est vide…",
                ["Ignorer (ne rien changer)", "Mettre à 0"],
                index=0
            )

            if st.button("💾 Sauvegarder les crédits"):
                if mode.startswith("Oracle"):
                    try:
                        base = df0.copy()
                        new = edited.copy()

                        base["CREDITS"] = base["CREDITS"].apply(norm_credit)
                        new["CREDITS"] = new["CREDITS"].apply(norm_credit)

                        base_map = {str(r["COD_ELP"]): r["CREDITS"] for _, r in base.iterrows()}

                        changes = []
                        for _, r in new.iterrows():
                            cod = str(r["COD_ELP"])
                            new_val = r["CREDITS"]
                            old_val = base_map.get(cod)

                            # politique sur valeurs vides
                            if new_val is None:
                                if null_policy == "Mettre à 0":
                                    new_val = 0.0
                                else:
                                    continue  # ignorer

                            if new_val != old_val:
                                changes.append((cod, float(new_val)))

                        if not changes:
                            st.info("Aucune modification détectée.")
                        else:
                            for cod, cred in changes:
                                run_exec(
                                    st.session_state["pool"],
                                    SQL_UPDATE_CREDIT_MODULE,
                                    {"p_cod_elp": cod, "p_credits": cred}
                                )

                            df_reload = run_query_df(
                                st.session_state["pool"],
                                SQL_SEMESTRES_MODULES_CREDITS,
                                {"p_filiere": filiere}
                            )
                            if "CREDITS" in df_reload.columns:
                                df_reload["CREDITS"] = df_reload["CREDITS"].apply(norm_credit)

                            st.session_state["df_credits_modules"] = df_reload
                            st.success(f"{len(changes)} module(s) mis à jour ✅")
                            st.rerun()

                    except Exception as e:
                        st.error(f"Erreur Oracle (update) : {e}")
                else:
                    st.session_state["df_credits_modules"] = edited
                    st.success("Sauvegardé en local ✅")

            # ==========================
            # Export CSV
            # ==========================
            st.markdown("### ⬇️ Export CSV")
            buf = io.StringIO()
            edited.to_csv(buf, index=False, sep=";", encoding="utf-8", quoting=csv.QUOTE_ALL, lineterminator="\n")
            st.download_button(
                "⬇️ Télécharger crédits_modules.csv",
                data=buf.getvalue().encode("utf-8"),
                file_name=f"credits_modules_{filiere.replace('%','')}.csv",
                mime="text/csv"
            )

        else:
            st.info("Clique sur **Charger modules/crédits** pour afficher la grille.")

st.markdown("---")
st.caption("© Faculté des Sciences Aïn Chock – Service Scolarité FSAC – Application interne")
