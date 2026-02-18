SQL_PARCOURS_TEMPLATE = """
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

        CASE
            WHEN SUM(CASE WHEN re.NOT_SUB_ELP IS NOT NULL THEN 1 ELSE 0 END) > 0
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
        ({IDENT_FILTER})
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
    annee_universitaire AS ANNEE,
    COD_ELP,
    LIB_ELP,
    'S' || num_semestre AS SEMESTRE,
    note_affichee,
    cod_tre
FROM ModulesAvecSemestre
ORDER BY
    annee_universitaire,
    num_semestre,
    COD_ELP
"""

SQL_INSCRIPTION_TEMPLATE = """
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
    ({IDENT_FILTER})
    AND iae.ETA_IAE = 'E'
    AND (:annee IS NULL OR iae.COD_ANU = :annee)
ORDER BY ANNEE_INSCRIPTION DESC
"""

SQL_ABI_TEMPLATE = """
SELECT DISTINCT
    ind.COD_ETU AS CODE_APOGEE,
    ind.CIN_IND AS CIN,
    ind.LIB_NOM_PAT_IND AS NOM,
    ind.LIB_PR1_IND AS PRENOM,
    re.COD_ELP,
    ep.LIB_ELP,
    re.COD_ANU AS ANNEE,
    re.NOT_SUB_ELP AS ABSENCE,
    re.COD_TRE
FROM RESULTAT_ELP re
JOIN INDIVIDU ind ON re.COD_IND = ind.COD_IND
JOIN ELEMENT_PEDAGOGI ep ON re.COD_ELP = ep.COD_ELP
WHERE
    re.NOT_SUB_ELP LIKE 'AB%'
    {IDENT_EXTRA}
    {MODULE_EXTRA}
ORDER BY ind.COD_ETU, re.COD_ELP
"""
SQL_ARCHIVE_TEMPLATE = """
SELECT DISTINCT
  ind.COD_IND                           AS COD_IND,
  ind.COD_ETU                           AS APOGEE,
  ind.COD_NNE_IND                       AS CNE,
  ind.CIN_IND                           AS CIN,
  ind.LIB_NOM_PAT_IND                   AS NOM,
  ind.LIB_PR1_IND                       AS PRENOM,
  ind.DATE_NAI_IND                      AS DATE_NAISSANCE,

  iae.COD_DIP                           AS DIPLOME,
  d.LIB_DIP                             AS LIB_DIPLOME,
  iae.COD_ETP                           AS ETAPE,

  re.COD_ELP                            AS COD_ELP,
  REGEXP_REPLACE(ep.LIB_ELP, '[[:cntrl:]]', ' ') AS LIB_ELP,
  ep.COD_NEL                            AS COD_NEL,

  re.COD_ANU                            AS ANNEE_DE_VALIDATION,
  ep.NBR_PNT_ECT_ELP                    AS CREDITS,

  NVL(TO_CHAR(re.NOT_ELP), '')          AS NOT_ELP,
  re.COD_TRE                            AS COD_TRE,
  MAX(re.COD_SES)                       AS COD_SES_MAX

FROM INDIVIDU ind
JOIN INS_ADM_ETP iae       ON ind.COD_IND = iae.COD_IND
JOIN DIPLOME d             ON d.COD_DIP = iae.COD_DIP
JOIN RESULTAT_ELP re       ON re.COD_IND = iae.COD_IND AND re.COD_ANU = iae.COD_ANU
JOIN ELEMENT_PEDAGOGI ep   ON ep.COD_ELP = re.COD_ELP

WHERE
  iae.ETA_IAE = 'E'
  AND ep.COD_ELP LIKE :filiere

  -- identifiant optionnel (apogee ou cin)
  AND (
        :ident IS NULL
        OR TO_CHAR(ind.COD_ETU) = :ident
        OR UPPER(ind.CIN_IND) = :ident
      )

  AND re.NOT_ELP IS NOT NULL
  AND re.COD_TRE IS NOT NULL

GROUP BY
  ind.COD_IND, ind.COD_ETU, ind.COD_NNE_IND, ind.CIN_IND,
  ind.LIB_NOM_PAT_IND, ind.LIB_PR1_IND, ind.DATE_NAI_IND,
  iae.COD_DIP, d.LIB_DIP, iae.COD_ETP,
  re.COD_ELP, ep.LIB_ELP, ep.COD_NEL, re.COD_ANU,
  ep.NBR_PNT_ECT_ELP, re.NOT_ELP, re.COD_TRE

ORDER BY
  ind.COD_ETU, re.COD_ANU, re.COD_ELP
"""
SQL_EXPORT_APOGEE_LIKE = """
SELECT
    ind.COD_ETU                                AS NUMERO,
    ind.LIB_NOM_PAT_IND                        AS NOM,
    ind.LIB_PR1_IND                            AS PRENOM,
    TO_CHAR(ind.DATE_NAI_IND,'DD/MM/YYYY')     AS NAISSANCE,

    re.COD_ELP                                 AS COD_ELP,
    REGEXP_REPLACE(ep.LIB_ELP, '[[:cntrl:]]', ' ') AS LIB_ELP,

    CASE
        WHEN re.NOT_SUB_ELP IS NOT NULL THEN re.NOT_SUB_ELP
        ELSE TO_CHAR(re.NOT_ELP)
    END                                        AS NOTE,

    20                                         AS BAREME,   -- comme ton export (si tu as une vraie colonne bareme, remplace ici)
    re.COD_TRE                                 AS RESULTAT

FROM RESULTAT_ELP re
JOIN INDIVIDU ind            ON ind.COD_IND = re.COD_IND
JOIN ELEMENT_PEDAGOGI ep     ON ep.COD_ELP = re.COD_ELP
JOIN INS_ADM_ETP iae         ON iae.COD_IND = re.COD_IND AND iae.COD_ANU = re.COD_ANU

WHERE
    iae.ETA_IAE = 'E'
    AND re.COD_ANU = :p_annee
    AND ep.COD_NEL LIKE 'MO%'                 -- modules
    AND re.COD_ELP LIKE :p_filiere            -- ex: FLPC%

    AND (
        :p_ident IS NULL
        OR TO_CHAR(ind.COD_ETU) = :p_ident
        OR UPPER(ind.CIN_IND) = :p_ident
    )

    AND (
        :p_ses IS NULL OR re.COD_SES = :p_ses
    )

ORDER BY ind.COD_ETU, re.COD_ELP
"""
SQL_SEMESTRES_MODULES_CREDITS = """
SELECT DISTINCT
    'S' || SUBSTR(ep.COD_ELP, 5, 1)                 AS SEMESTRE,
    ep.COD_ELP                                      AS COD_ELP,
    REGEXP_REPLACE(ep.LIB_ELP, '[[:cntrl:]]', ' ')  AS LIB_ELP,
    ep.NBR_PNT_ECT_ELP                              AS CREDITS
FROM ELEMENT_PEDAGOGI ep
WHERE
    ep.COD_NEL LIKE 'MO%'
    AND ep.COD_ELP LIKE :p_filiere
ORDER BY
    SEMESTRE, COD_ELP
"""

SQL_UPDATE_CREDIT_MODULE = """
UPDATE ELEMENT_PEDAGOGI
SET NBR_PNT_ECT_ELP = :p_credits
WHERE COD_ELP = :p_cod_elp
"""

SQL_INSERT_MODULE_MINI = """
INSERT INTO ELEMENT_PEDAGOGI (COD_ELP, LIB_ELP, COD_NEL, NBR_PNT_ECT_ELP)
VALUES (:p_cod_elp, :p_lib_elp, 'MO', :p_credits)
"""

SQL_DELETE_MODULE = """
DELETE FROM ELEMENT_PEDAGOGI
WHERE COD_ELP = :p_cod_elp
"""



