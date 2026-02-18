import base64
import streamlit as st
from datetime import datetime

def load_file_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""

def ensure_state():
    # Thème par défaut = Sombre
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Sombre"

    if "stats" not in st.session_state:
        st.session_state["stats"] = {
            "parcours": 0,
            "inscription": 0,
            "abi": 0,
            "last_action": "—",
            "last_time": "—",
        }

def is_dark() -> bool:
    return st.session_state.get("theme_mode") == "Clair"

def apply_css(css_path: str, logo_b64: str):
    """
    Charge base.css (séparé), puis injecte seulement les variables du thème.
    """
    with open(css_path, "r", encoding="utf-8") as f:
        base_css = f.read()

    theme = "dark" if is_dark() else "light"

    if theme == "dark":
        vars_css = """
        :root{
          --bg:#0b0f14; --bg2:#0f1620;
          --card:rgba(20,28,40,0.78);
          --card2:rgba(20,28,40,0.62);
          --text:rgba(255,255,255,0.92);
          --muted:rgba(255,255,255,0.62);
          --border:rgba(255,255,255,0.10);
          --accent:rgba(255,70,70,0.92);
          --accentBorder:rgba(255,70,70,0.25);
          --shadow:0 18px 55px rgba(0,0,0,0.55);
          --logoOpacity:0.02;
          --surface:rgba(15,22,32,0.70);
          --surface2:rgba(15,22,32,0.62);
          --inputBg:rgba(10,14,20,0.35);
        }
        """
    else:
        vars_css = """
        :root{
          --bg:#ffffff; --bg2:#f6f6f6;
          --card:rgba(255,255,255,0.92);
          --card2:rgba(255,255,255,0.78);
          --text:rgba(0,0,0,0.92);
          --muted:rgba(0,0,0,0.62);
          --border:rgba(0,0,0,0.06);
          --accent:rgba(255,0,0,0.88);
          --accentBorder:rgba(255,0,0,0.25);
          --shadow:0 14px 45px rgba(0,0,0,0.06);
          --logoOpacity:0.03;
          --surface:rgba(255,255,255,0.82);
          --surface2:rgba(255,255,255,0.72);
          --inputBg:#ffffff;
        }
        """

    st.markdown(
        f"""
<style>
{vars_css}
{base_css}
[data-testid="stAppViewContainer"]::before{{
  background-image:url("data:image/jpg;base64,{logo_b64}");
  opacity:var(--logoOpacity);
}}
</style>
""",
        unsafe_allow_html=True
    )

def navbar(is_logged_in: bool, oracle_user: str, on_logout):
    st.markdown(
        f"""
<div class="navbar">
  <div class="navbar-inner">
    <div>
      <div class="brand">🎓 Service Scolarité FSAC</div>
      <div class="brand-sub">Application interne</div>
    </div>
    <div>
      {f"<div class='user-pill'><span class='user-dot'></span><b>{oracle_user}</b></div>" if is_logged_in else ""}
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True
    )

    # Bouton Streamlit fixé en haut
    st.markdown('<div class="nav-actions">', unsafe_allow_html=True)
    if is_logged_in:
        if st.button("🚪 Déconnexion", type="primary"):
            on_logout()
    else:
        st.button("🔐 Connexion")
    st.markdown("</div>", unsafe_allow_html=True)

def sidebar(is_logged_in: bool, oracle_user: str):
    with st.sidebar:
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)

        st.markdown("### 🌗 Thème")
        st.radio(
            "Mode",
            ["Sombre", "Clair"],
            horizontal=True,
            label_visibility="collapsed",
            key="theme_mode"
        )

        st.markdown("---")
        st.markdown("### 🎛️ Navigation")
        st.caption("Accès rapide aux modules")

        if is_logged_in:
            menu = ["🏠 Accueil", "📊 Dashboard", "🧾 Parcours Étudiant", "🚫 Étudiants ABI", "📋 Inscription Actuelle","🗂️ Archive Apogée", "🧾 Export Notes","📚 Crédits Modules"]
        else:
            menu = ["🏠 Accueil"]

        selected = st.radio("Menu", menu, key="nav_menu")

        st.markdown("---")
        if is_logged_in:
            st.markdown(f"**Connecté :** `{oracle_user}`")

        st.markdown('</div>', unsafe_allow_html=True)

    page = selected.split(" ", 1)[1] if " " in selected else selected
    return page

def touch_stats(action_name: str):
    st.session_state["stats"]["last_action"] = action_name
    st.session_state["stats"]["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
