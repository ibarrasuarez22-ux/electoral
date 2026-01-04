import pandas as pd
import geopandas as gpd
import os
import numpy as np

# CONFIGURACIÓN
PATH_SHP_URB = "data/mapas/30m.shp"
PATH_SHP_RUR = "data/mapas/30l.shp"
PATH_SHP_POL = "data/mapas/SECCION.shp"
PATH_CENSO_URB = "data/tablas/conjunto_de_datos_ageb_urbana_30_cpv2020.csv"
PATH_CENSO_RUR = "data/tablas/iter_veracruz_2020.csv"
PATH_POL_21 = "data/tablas/Municipal_2021.csv"
PATH_POL_25 = "data/tablas/Municipal_2025.csv"
MUNICIPIO = '032' 

if not os.path.exists("output"): os.makedirs("output")
print("📉 INICIANDO MOTOR ESTADÍSTICO DE PRECISIÓN...")

# --- 1. FUNCIONES DE LECTURA ROBUSTA ---
def leer_inegi(ruta):
    try:
        df = pd.read_csv(ruta, low_memory=False, dtype=str)
        df.columns = df.columns.str.upper().str.strip()
        
        # Mapeo de nombres estandarizados
        renames = {
            'MUN':'CVE_MUN', 'MUNICIPIO':'CVE_MUN', 
            'LOC':'CVE_LOC', 'LOCALIDAD':'CVE_LOC',
            'AGEB':'CVE_AGEB', 
            'MZA':'CVE_MZA', 'MANZANA':'CVE_MZA',
            'ENTIDAD': 'ENTIDAD', 'ENT': 'ENTIDAD'
        }
        df.rename(columns=renames, inplace=True)
        return df
    except Exception as e: 
        print(f"⚠️ Error leyendo CSV {ruta}: {e}")
        return None

# --- 2. PROCESAMIENTO POBREZA (MÉTODO NBI + Z-SCORE) ---
print("   🏠 Calculando Pobreza Multidimensional (Método NBI)...")

def procesar_pobreza(shp_path, csv_path, tipo):
    if not os.path.exists(shp_path) or not os.path.exists(csv_path):
        print(f"⚠️ Faltan archivos para {tipo}")
        return None
        
    shp = gpd.read_file(shp_path)
    df = leer_inegi(csv_path)
    
    if df is None: return None
    
    # Filtros por Municipio
    shp = shp[shp['CVE_MUN'] == MUNICIPIO]
    df = df[df['CVE_MUN'] == MUNICIPIO]
    
    # Limpieza numérica de variables NBI
    vars_nbi = {
        'VIVIENDA': ['VPH_PISOTI', 'VPH_S_ELEC', 'VPH_AGUADV', 'VPH_NODREN'], 
        'ACTIVOS': ['VPH_REFRI', 'VPH_LAVAD', 'VPH_AUTOM'],
        'EDUCACION': ['P15YM_AN'],
        'UNIVERSO': ['TVIVPARHAB', 'POBTOT']
    }
    
    cols_necesarias = [c for lista in vars_nbi.values() for c in lista]
    for c in cols_necesarias:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    df['TVIV'] = df['TVIVPARHAB'].replace(0, 1)
    
    # --- CÁLCULO DE INDICADORES ---
    # 1. Vivienda
    df['INDICE_VIVIENDA'] = (
        (df.get('VPH_PISOTI',0)/df['TVIV']) + 
        (df.get('VPH_NODREN',0)/df['TVIV']) + 
        (df.get('VPH_AGUADV',0)/df['TVIV']) 
    )
    # 2. Patrimonio
    df['INDICE_PATRIMONIAL'] = 1 - ( (df.get('VPH_REFRI',0) + df.get('VPH_LAVAD',0)) / (2*df['TVIV']) )
    # 3. Educación
    if 'P_15YMAS' in df.columns and 'P15YM_AN' in df.columns:
        p15 = pd.to_numeric(df['P_15YMAS'], errors='coerce').replace(0,1)
        df['INDICE_EDUCATIVO'] = df['P15YM_AN'] / p15
    else:
        df['INDICE_EDUCATIVO'] = 0
        
    # --- Z-SCORE (Estadística) ---
    df['RAW_SCORE'] = (df['INDICE_VIVIENDA'] + df['INDICE_PATRIMONIAL'] + df['INDICE_EDUCATIVO']) / 3
    media = df['RAW_SCORE'].mean()
    std = df['RAW_SCORE'].std()
    if std == 0: std = 1 # Evitar div/0
    df['NBI_ZSCORE'] = (df['RAW_SCORE'] - media) / std
    
    # Clasificación
    conditions = [
        (df['NBI_ZSCORE'] >= 2),
        (df['NBI_ZSCORE'] >= 1) & (df['NBI_ZSCORE'] < 2),
        (df['NBI_ZSCORE'] >= 0) & (df['NBI_ZSCORE'] < 1),
        (df['NBI_ZSCORE'] < 0)
    ]
    choices = ['POBREZA EXTREMA CRÍTICA', 'POBREZA ALTA', 'POBREZA MODERADA', 'SIN POBREZA MARCADA']
    df['CLASIFICACION_POBREZA'] = np.select(conditions, choices, default='SIN DATO')
    
    # Proyección 2025
    df['POB_2025'] = df['POBTOT'] * (1.01 ** 5)
    
    # --- GENERACIÓN DE CLAVE GEO ---
    if tipo == 'URBANO':
        df['CVEGEO'] = df['ENTIDAD'] + df['CVE_MUN'] + df['CVE_LOC'] + df['CVE_AGEB'] + df['CVE_MZA']
        df['ETIQUETA'] = "AGEB " + df['CVE_AGEB'].astype(str)
    else:
        df['CVEGEO'] = df['ENTIDAD'] + df['CVE_MUN'] + df['CVE_LOC']
        df['ETIQUETA'] = df.get('NOM_LOC', 'LOC ' + df['CVE_LOC'])
        
    return shp.merge(df, on='CVEGEO', how='inner')

urb = procesar_pobreza(PATH_SHP_URB, PATH_CENSO_URB, 'URBANO')
rur = procesar_pobreza(PATH_SHP_RUR, PATH_CENSO_RUR, 'RURAL')

if urb is not None: urb.to_crs(epsg=4326).to_file("output/pobreza_nbi_urb.geojson", driver='GeoJSON')
if rur is not None: rur.to_crs(epsg=4326).to_file("output/pobreza_nbi_rur.geojson", driver='GeoJSON')
print("   ✅ Pobreza calculada correctamente.")


# --- 3. PROCESAMIENTO ELECTORAL ---
print("   🗳️ Calculando Métricas Electorales...")

def limpiar_sec(x): 
    try: return int(float(str(x)))
    except: return 0

def procesar_eleccion(path, anio):
    if not os.path.exists(path): return None
    df = pd.read_csv(path)
    col_sec = next((c for c in df.columns if 'SECCION' in c.upper()), None)
    if not col_sec: return None
    df['SEC'] = df[col_sec].apply(limpiar_sec)
    
    # Lógica agnóstica de suma
    def sumar_bando(row, keys):
        total = 0
        for col in df.columns:
            if col.upper() == 'SEC': continue
            try:
                # Si la columna contiene alguna de las llaves
                if any(k in col.upper() for k in keys):
                    total += float(row[col])
            except: pass
        return total

    g = df.groupby('SEC').sum(numeric_only=True).reset_index()
    
    g[f'VOTO_4T_{anio}'] = g.apply(lambda x: sumar_bando(x, ['MORENA','PT','VERDE']), axis=1)
    g[f'VOTO_OPO_{anio}'] = g.apply(lambda x: sumar_bando(x, ['PAN','PRI','PRD','ALIANZA']), axis=1)
    g[f'VOTO_MC_{anio}'] = g.apply(lambda x: sumar_bando(x, ['MC','MOVIMIENTO']), axis=1)
    
    return g

e21 = procesar_eleccion(PATH_POL_21, '21')
e25 = procesar_eleccion(PATH_POL_25, '25')

if e25 is not None:
    shp_pol = gpd.read_file(PATH_SHP_POL)
    col_sec_shp = next((c for c in shp_pol.columns if 'SECCION' in c.upper()), None)
    shp_pol['SEC'] = shp_pol[col_sec_shp].astype(int)

    # AQUÍ ESTABA EL ERROR: Variable corregida a 'shp_pol'
    final_pol = shp_pol.merge(e25, on='SEC', how='inner')
    
    if e21 is not None:
        final_pol = final_pol.merge(e21[['SEC', 'VOTO_4T_21', 'VOTO_OPO_21', 'VOTO_MC_21']], on='SEC', how='left')

    def get_winner(r, anio):
        v4t = r.get(f'VOTO_4T_{anio}', 0)
        vopo = r.get(f'VOTO_OPO_{anio}', 0)
        vmc = r.get(f'VOTO_MC_{anio}', 0)
        if v4t > vopo and v4t > vmc: return '4T'
        if vopo > v4t and vopo > vmc: return 'OPOSICION'
        if vmc > v4t and vmc > vopo: return 'MC'
        return 'EMPATE'

    final_pol['GANADOR_21'] = final_pol.apply(lambda x: get_winner(x, '21'), axis=1)
    final_pol['GANADOR_25'] = final_pol.apply(lambda x: get_winner(x, '25'), axis=1)

    final_pol.to_crs(epsg=4326).to_file("output/analisis_politico_real.geojson", driver='GeoJSON')
    print("   ✅ Análisis Político generado.")
