import os
import pandas as pd
import oracledb

from .config import HOST, PORT, SERVICE, ORACLE_CLIENT_LIB_DIR

def init_oracle_client():
    # Ajouter Instant Client au PATH (Windows)
    if ORACLE_CLIENT_LIB_DIR:
        os.environ["PATH"] = ORACLE_CLIENT_LIB_DIR + ";" + os.environ.get("PATH", "")

    try:
        oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB_DIR)
    except Exception as e:
        raise RuntimeError(
            f"Impossible d'initialiser Oracle Client (thick mode). "
            f"Vérifie ORACLE_CLIENT_LIB_DIR={ORACLE_CLIENT_LIB_DIR}. Détail: {e}"
        )

def make_dsn():
    return oracledb.makedsn(HOST, PORT, service_name=SERVICE)

def create_pool(user: str, password: str):
    dsn = make_dsn()
    pool = oracledb.create_pool(
        user=user,
        password=password,
        dsn=dsn,
        min=1,
        max=4,
        increment=1,
        getmode=oracledb.POOL_GETMODE_WAIT
    )
    # test
    with pool.acquire() as _:
        pass
    return pool

def close_pool(pool):
    try:
        pool.close()
    except Exception:
        pass

def run_query_df(pool, sql: str, binds: dict) -> pd.DataFrame:
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.arraysize = 2000
            cur.prefetchrows = 2000
            cur.execute(sql, binds)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description] if cur.description else []
            return pd.DataFrame(rows, columns=cols)
        finally:
            try:
                cur.close()
            except Exception:
                pass

def build_ident_filter(valeur: str, table_alias: str):
    """
    Pas de REGEXP_LIKE => filtre choisi côté Python (plus rapide pour index).
    """
    v = (valeur or "").strip().upper()
    if not v:
        return None, {}

    if v.isdigit():
        return f"{table_alias}.COD_ETU = :code_etu", {"code_etu": int(v)}
    return f"UPPER({table_alias}.CIN_IND) = :cin", {"cin": v}
