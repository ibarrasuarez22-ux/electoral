import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import os

st.set_page_config(layout="wide", page_title="SITS: Estrategia Real", page_icon="📈")

# --- CARGA DATOS ---
@st.cache_data
def load():
    u = gpd.read_file("output/pobreza_nbi_urb.geojson")
    r = gpd.read_file("output/pobreza_nbi_rur.geojson")
    p = gpd.read_file("output/analisis_politico_real.geojson")
    return u, r, p

try:
    gdf_u, gdf_r, gdf_p = load()
except:
    st.error("⚠️ Ejecuta primero 'python 1_motor_estadistico.py'")
    st.stop()

# --- CONFIGURACIÓN DE BANDO ---
with st.sidebar:
    st.title("⚙️ Configuración")
    st.info("Define tu posición para ajustar el análisis.")
    MI_BANDO = st.radio("¿Quiénes somos nosotros?", ["OPOSICION (PAN/PRI)", "MOVIMIENTO CIUDADANO (MC)", "OFICIALISMO (4T)"])
    
    st.divider()
    st.header("Filtros Territoriales")
    zona = st.selectbox("Zona:", ["URBANA", "RURAL"])

# --- PREPARAR DATOS SEGÚN BANDO ---
# Recalculamos etiquetas dinámicamente según quién sea "Nosotros"
def interpretar_politica(row):
    ganador = row['GANADOR_25']
    pasado = row['GANADOR_21']
    
    # Mapeo de input usuario a claves de datos
    clave_mi_bando = 'OPOSICION'
    if 'MC' in MI_BANDO: clave_mi_bando = 'MC'
    if '4T' in MI_BANDO: clave_mi_bando = '4T'
    
    if ganador == clave_mi_bando:
        return "NUESTRO BASTION" if pasado == clave_mi_bando else "CONQUISTA RECIENTE"
    else:
        # Si no ganamos, ¿quién ganó?
        return f"PERDIDO (Gana {ganador})"

gdf_p['DIAGNOSTICO_PERSONALIZADO'] = gdf_p.apply(interpretar_politica, axis=1)

# --- DASHBOARD ---
st.title(f"📊 Tablero Estratégico: {MI_BANDO}")
st.markdown("Análisis basado en **Estadística NBI (Necesidades Básicas Insatisfechas)** y **Z-Scores**.")

t1, t2, t3 = st.tabs(["🗺️ MAPA DE POBREZA REAL", "🗳️ MAPA DE PODER", "🎯 OBJETIVOS PRIORITARIOS"])

# TAB 1: POBREZA CIENTÍFICA
with t1:
    col1, col2 = st.columns([1,3])
    with col1:
        st.subheader("Análisis NBI")
        st.write("Filtro estadístico basado en Desviación Estándar (Z-Score).")
        
        filtro_pob = st.select_slider(
            "Severidad de Pobreza:",
            options=["TODOS", "POBREZA MODERADA", "POBREZA ALTA", "POBREZA EXTREMA CRÍTICA"],
            value="POBREZA ALTA"
        )
        
        df_mapa = gdf_u if zona == 'URBANA' else gdf_r
        if filtro_pob != "TODOS":
            df_mapa = df_mapa[df_mapa['CLASIFICACION_POBREZA'] == filtro_pob]
            
        st.metric("Zonas Detectadas", len(df_mapa))
        st.metric("Población Estimada", f"{int(df_mapa['POB_2025'].sum()):,}")
        
    with col2:
        m = folium.Map(location=[18.42, -95.11], zoom_start=13)
        if not df_mapa.empty:
            folium.Choropleth(
                geo_data=df_mapa,
                data=df_mapa,
                columns=['CVEGEO', 'NBI_ZSCORE'],
                key_on='feature.properties.CVEGEO',
                fill_color='Reds',
                legend_name='Intensidad de Pobreza (Z-Score)'
            ).add_to(m)
            folium.GeoJson(df_mapa, tooltip=folium.GeoJsonTooltip(fields=['ETIQUETA', 'CLASIFICACION_POBREZA'])).add_to(m)
        st_folium(m, height=500, use_container_width=True)

# TAB 2: POLÍTICA DINÁMICA
with t2:
    st.subheader(f"Situación Política para: {MI_BANDO}")
    
    c1, c2 = st.columns([1, 3])
    with c1:
        conteos = gdf_p['DIAGNOSTICO_PERSONALIZADO'].value_counts()
        st.dataframe(conteos, use_container_width=True)
        
    with c2:
        m2 = folium.Map(location=[18.42, -95.11], zoom_start=12)
        
        def color_dinamico(x):
            diag = x['properties']['DIAGNOSTICO_PERSONALIZADO']
            if "NUESTRO" in diag: return '#2ecc71' # Verde (Bien)
            if "CONQUISTA" in diag: return '#27ae60' # Verde fuerte
            if "MC" in diag and "MC" not in MI_BANDO: return '#ff8300' # Naranja enemigo
            if "4T" in diag and "4T" not in MI_BANDO: return '#800000' # Rojo enemigo
            return '#95a5a6' # Gris (Otros)

        folium.GeoJson(
            gdf_p,
            style_function=lambda x: {'fillColor': color_dinamico(x), 'color':'black', 'weight':1, 'fillOpacity':0.6},
            tooltip=folium.GeoJsonTooltip(fields=['SEC', 'DIAGNOSTICO_PERSONALIZADO', 'GANADOR_25'])
        ).add_to(m2)
        st_folium(m2, height=500, use_container_width=True)

# TAB 3: CRUCE DE OPORTUNIDAD
with t3:
    st.header("📍 Zonas de Oportunidad Estratégica")
    st.info(f"Buscando zonas de **Alta Pobreza** donde **{MI_BANDO}** necesita recuperar o consolidar votos.")
    
    # CRUCE EN VIVO
    # 1. Tomamos zonas pobres (Z-Score > 1)
    pobres = gdf_u[gdf_u['NBI_ZSCORE'] > 1].copy() # Alta pobreza
    pobres['geometry'] = pobres.geometry.centroid
    
    # 2. Cruzamos con Secciones
    cruce = gpd.sjoin(pobres, gdf_p[['DIAGNOSTICO_PERSONALIZADO', 'GANADOR_25', 'geometry']], predicate='within')
    
    opcion = st.radio("Objetivo:", ["RECUPERAR TERRENO (Donde perdimos)", "CONSOLIDAR (Donde ganamos)"])
    
    if "RECUPERAR" in opcion:
        target = cruce[cruce['DIAGNOSTICO_PERSONALIZADO'].str.contains("PERDIDO")]
        st.warning(f"Zonas de Alta Pobreza en manos del rival ({len(target)} manzanas). Oportunidad de crítica constructiva o propuesta de mejora.")
    else:
        target = cruce[cruce['DIAGNOSTICO_PERSONALIZADO'].str.contains("NUESTRO|CONQUISTA")]
        st.success(f"Zonas de Alta Pobreza bajo nuestro control ({len(target)} manzanas). Prioridad de atención social urgente.")
        
    if not target.empty:
        st.dataframe(
            target[['ETIQUETA', 'CLASIFICACION_POBREZA', 'DIAGNOSTICO_PERSONALIZADO', 'POB_2025']]
            .sort_values('POB_2025', ascending=False),
            use_container_width=True
        )
    else:
        st.write("No se encontraron zonas con esos criterios específicos.")
