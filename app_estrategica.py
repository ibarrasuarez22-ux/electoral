import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SITS: Tablero MC", page_icon="🍊")

# --- ESTILOS VISUALES PREMIUM ---
st.markdown("""
<style>
    .orange-box { 
        background-color: #fff5e6; padding: 20px; border-radius: 10px; 
        border-left: 6px solid #FF8300; margin-bottom: 20px;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .method-box {
        background-color: #f8f9fa; padding: 15px; border-radius: 8px;
        border: 1px solid #ddd; margin-bottom: 10px;
        font-size: 14px;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #F8F9F9; color: #555; text-align: center;
        padding: 10px; font-size: 12px; border-top: 1px solid #ddd;
    }
    .signature {
        font-weight: bold; color: #FF8300;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. CARGA DE DATOS ---
@st.cache_data
def load():
    path_u = "output/pobreza_nbi_urb.geojson" 
    path_p = "output/analisis_politico_real.geojson"
    if not os.path.exists(path_u): path_u = "data/tablas/SITS_Pobreza_Urbana.geojson"
    u = gpd.read_file(path_u) if os.path.exists(path_u) else None
    p = gpd.read_file(path_p) if os.path.exists(path_p) else None
    return u, p

try:
    gdf_u, gdf_p = load()
    if gdf_p is None: raise Exception("Faltan datos políticos")
    if gdf_u is None: raise Exception("Faltan datos de pobreza")
except:
    st.error("⚠️ Error Crítico: Ejecuta 'python 1_motor_estadistico.py' para generar los datos.")
    st.stop()

# --- 2. LÓGICA DE NEGOCIO ---
# Cálculo de márgenes si no existen
if 'MARGEN_VICTORIA' not in gdf_p.columns:
    def calc_margen(r):
        v = sorted([r.get('VOTO_4T_25',0), r.get('VOTO_OPO_25',0), r.get('VOTO_MC_25',0)], reverse=True)
        tot = sum(v)
        return ((v[0]-v[1])/tot)*100 if tot>0 else 0
    gdf_p['MARGEN_VICTORIA'] = gdf_p.apply(calc_margen, axis=1)

# --- SIDEBAR: FIRMA INSTITUCIONAL ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Movimiento_Ciudadano_Logo.svg/1200px-Movimiento_Ciudadano_Logo.svg.png", width=120)
    st.markdown("## Tablero de Control")
    st.markdown("---")
    st.info("**Usuario:** Estrategia MC")
    st.markdown("---")
    st.markdown("**Propiedad Intelectual:**")
    st.markdown("© **CCPI** | Consultoría en Comunicación Política Integral")
    st.markdown("**Autor:** Mtro. Roberto Ibarra Suárez")
    st.markdown(f"**Versión:** 2026.1.0 | {datetime.date.today()}")

# --- ENCABEZADO PRINCIPAL ---
c1, c2 = st.columns([1, 8])
with c1: st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Movimiento_Ciudadano_Logo.svg/1200px-Movimiento_Ciudadano_Logo.svg.png", width=90)
with c2: 
    st.title("🍊 Sistema de Inteligencia Territorial (SITS)")
    st.markdown("**Estrategia basada en Datos Reales | Cobertura Municipal**")

# --- MENÚ DE PESTAÑAS ---
t1, t2, t3, t4 = st.tabs(["📊 KPI's", "🗺️ Mapa Político", "🎯 Oportunidades (Pobreza)", "📚 Metodología"])

# ==========================================
# PESTAÑA 1: KPI'S (RESUMEN)
# ==========================================
with t1:
    st.subheader("Estado de Fuerza Actual")
    
    secciones_mc = len(gdf_p[gdf_p['GANADOR_25'] == 'MC'])
    votos_mc = gdf_p['VOTO_MC_25'].sum() if 'VOTO_MC_25' in gdf_p.columns else 0
    total_secciones = len(gdf_p)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Territorio Gobernado (MC)", f"{secciones_mc} Secciones", help="Total de secciones donde ganamos en 2025")
    k2.metric("Voto Duro (MC)", f"{int(votos_mc):,}", help="Suma total de votos naranjas")
    k3.metric("Cobertura Territorial", f"{(secciones_mc/total_secciones)*100:.1f}%", help="Porcentaje del municipio pintado de naranja")
    
    st.markdown("""
    <div class="orange-box">
        <b>💡 Interpretación Rápida:</b><br>
        Estos números nos dicen qué tan fuertes somos hoy. Si la "Cobertura Territorial" es baja, significa que necesitamos crecer geográficamente, aunque tengamos muchos votos concentrados.
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# PESTAÑA 2: MAPA POLÍTICO
# ==========================================
with t2:
    st.subheader("Geografía del Poder")
    
    c_map, c_leg = st.columns([3,1])
    with c_map:
        m = folium.Map(location=[18.42, -95.11], zoom_start=12, tiles='CartoDB positron')
        def color_ganador(g):
            if g == 'MC': return '#FF8300' 
            if g == '4T': return '#800000' 
            return '#2980b9' 
            
        folium.GeoJson(
            gdf_p,
            style_function=lambda x: {
                'fillColor': color_ganador(x['properties']['GANADOR_25']), 
                'color': 'white', 'weight': 0.5, 'fillOpacity': 0.7
            },
            tooltip=folium.GeoJsonTooltip(fields=['GANADOR_25'], aliases=['Ganó:'])
        ).add_to(m)
        st_folium(m, height=500, use_container_width=True)

    with c_leg:
        st.markdown("**¿Quién manda dónde?**")
        st.info("🟧 **Naranja (MC):** Zonas ganadas.")
        st.error("🟥 **Guinda (4T):** Zonas del oficialismo.")
        st.info("🟦 **Azul (Oposición):** Zonas del PRIAN.")

# ==========================================
# PESTAÑA 3: OPORTUNIDADES (TABLA MAESTRA)
# ==========================================
with t3:
    st.subheader("🎯 Zonas de Ataque Estratégico")
    
    st.markdown("""
    <div class="orange-box">
        <b>¿Cómo leer esta tabla?</b><br>
        Aquí están las colonias que <b>NO gobernamos</b> pero que tienen muchas necesidades.<br>
        Los números no son "Sí/No", son <b>BRECHAS (%)</b>:
        <ul>
            <li>Un <b>10%</b> significa que les falta poco.</li>
            <li>Un <b>90%</b> significa que les falta casi todo (Urgencia Máxima).</li>
        </ul>
        <i>Usa esto para definir qué proponer: ¿Obra pública (Servicios) o Despensas (Alimento)?</i>
    </div>
    """, unsafe_allow_html=True)

    # --- MOTOR DE CÁLCULO CIENTÍFICO ---
    def limpiar_dato(df, col): return pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    # Preparación espacial
    pobres = gdf_u.copy()
    pobres['centro'] = pobres.geometry.centroid
    cruce = gpd.sjoin(pobres.set_geometry('centro'), gdf_p[['GANADOR_25', 'geometry']], predicate='within')
    oportunidades = cruce[cruce['GANADOR_25'] != 'MC'].copy() # Solo territorio rival

    # VARIABLES DENOMINADORAS
    tviv = limpiar_dato(oportunidades, 'TVIVPARHAB').replace(0, 1)
    pob_tot = limpiar_dato(oportunidades, 'POBTOT').replace(0, 1)

    # 1. BRECHA DE RIQUEZA (Ingreso/Activos)
    # Promedio de carencia de 4 bienes clave
    sin_auto = tviv - limpiar_dato(oportunidades, 'VPH_AUTOM')
    sin_pc = tviv - limpiar_dato(oportunidades, 'VPH_PC')
    sin_lavad = tviv - limpiar_dato(oportunidades, 'VPH_LAVAD')
    sin_internet = tviv - limpiar_dato(oportunidades, 'VPH_INTER')
    oportunidades['Brecha Riqueza'] = (((sin_auto + sin_pc + sin_lavad + sin_internet) / 4 / tviv) * 100).clip(0, 100)

    # 2. SALUD (Sin Derechohabiencia)
    con_salud = limpiar_dato(oportunidades, 'PDER_SS')
    oportunidades['Falta Salud'] = ((1 - (con_salud / pob_tot)) * 100).clip(0, 100)

    # 3. VIVIENDA COMPUESTA (Max de carencias)
    piso_tierra = limpiar_dato(oportunidades, 'VPH_PISOTI')
    sin_drenaje = limpiar_dato(oportunidades, 'VPH_NODREN')
    hacinamiento = limpiar_dato(oportunidades, 'VPH_1CUART')
    
    pct_piso = (piso_tierra / tviv) * 100
    pct_dren = (sin_drenaje / tviv) * 100
    pct_hac = (hacinamiento / tviv) * 100
    oportunidades['Mala Vivienda'] = pd.concat([pct_piso, pct_dren, pct_hac], axis=1).max(axis=1).clip(0, 100)

    # 4. SERVICIOS (Agua/Luz)
    sin_agua = tviv - limpiar_dato(oportunidades, 'VPH_AGUADV')
    sin_luz = limpiar_dato(oportunidades, 'VPH_S_ELEC')
    oportunidades['Falta Servicios'] = (((sin_agua + sin_luz) / 2 / tviv) * 100).clip(0, 100)

    # 5. EDUCACIÓN
    p15 = limpiar_dato(oportunidades, 'P_15YMAS').replace(0, 1)
    rezago = limpiar_dato(oportunidades, 'P15YM_AN') + limpiar_dato(oportunidades, 'P15YM_SE')
    oportunidades['Rezago Edu'] = ((rezago / p15) * 100).clip(0, 100)

    # 6. ALIMENTACIÓN
    sin_refri = tviv - limpiar_dato(oportunidades, 'VPH_REFRI')
    oportunidades['Riesgo Alim'] = ((sin_refri / tviv) * 100).clip(0, 100)

    # TABLA FINAL
    col_id = next((c for c in ['ETIQUETA', 'ETIQUETA_MAPA', 'CVEGEO'] if c in oportunidades.columns), 'Ubicación')
    oportunidades['Población'] = pob_tot.astype(int)

    df_final = oportunidades[[
        col_id, 'GANADOR_25', 'Población', 
        'Brecha Riqueza', 'Falta Salud', 'Mala Vivienda', 'Falta Servicios', 'Rezago Edu', 'Riesgo Alim'
    ]].copy()

    df_final.columns = [
        '📍 Ubicación', '🗳️ Votaron Por', '👥 Población', 
        '📉 Brecha Riqueza', '🏥 Sin Salud', '🏠 Mala Vivienda', '🚰 Sin Servicios', '🎓 Rezago Edu', '🍲 Sin Alimento'
    ]

    df_final = df_final.sort_values('📉 Brecha Riqueza', ascending=False).head(50)
    cols_num = ['📉 Brecha Riqueza', '🏥 Sin Salud', '🏠 Mala Vivienda', '🚰 Sin Servicios', '🎓 Rezago Edu', '🍲 Sin Alimento']
    df_final[cols_num] = df_final[cols_num].round(1)

    if not df_final.empty:
        st.dataframe(
            df_final.style.background_gradient(cmap='Reds', subset=cols_num),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay zonas de oportunidad detectadas con los filtros actuales.")

# ==========================================
# PESTAÑA 4: METODOLOGÍA (NUEVA)
# ==========================================
with t4:
    st.subheader("📚 Nota Metodológica y Fuentes")
    
    st.markdown("""
    <div class="method-box">
        <h4>1. Fuente de Datos</h4>
        <ul>
            <li><b>Datos Sociales:</b> Censo de Población y Vivienda 2020 (INEGI), a nivel Manzana Urbana (AGEB) y Localidad Rural.</li>
            <li><b>Datos Electorales:</b> Resultados oficiales de Cómputos Municipales 2021 y 2025 (OPLE/INE).</li>
        </ul>
    </div>

    <div class="method-box">
        <h4>2. Modelo Estadístico: Análisis de Brechas (Gap Analysis)</h4>
        Este sistema no utiliza promedios simples. Se basa en una adaptación del <b>Método Alkire-Foster</b> para medición de pobreza multidimensional.
        <br><br>
        <b>¿Por qué Brechas?</b><br>
        En lugar de clasificar binariamente (Pobre/No Pobre), calculamos la <b>intensidad de la carencia</b>.
        <br>
        <i>Fórmula:</i> <code>Brecha = (Necesidad Insatisfecha / Universo Total) * 100</code>
        <br><br>
        <b>Variables Compuestas:</b>
        <ul>
            <li><b>Brecha de Riqueza (Patrimonio):</b> Índice compuesto por falta de Automóvil, Computadora, Lavadora e Internet. Sirve como proxy de ingreso líquido.</li>
            <li><b>Vivienda Digna:</b> Se toma el valor MÁXIMO de carencia entre: Piso de Tierra, Falta de Drenaje o Hacinamiento (más de 2.5 personas por cuarto). Esto evita sesgos donde una casa tiene buen piso pero viven hacinados.</li>
            <li><b>Salud:</b> Porcentaje directo de población sin afiliación a servicios de salud (IMSS, ISSSTE, etc.).</li>
        </ul>
    </div>
    
    <div class="method-box">
        <h4>3. Proyección Demográfica</h4>
        Se aplica una tasa de crecimiento geométrica conservadora del <b>1% anual</b> para estimar la población objetivo al año 2026, basada en tendencias históricas del municipio.
    </div>
    """, unsafe_allow_html=True)

    st.info("Este sistema y su metodología son propiedad de **CCPI**. Su uso es exclusivo para fines de estrategia territorial.")

# --- FOOTER ---
st.markdown("""
<div class="footer">
    Sistema Desarrollado por <b>CCPI (Consultoría en Comunicación Política Integral)</b><br>
    Propiedad Intelectual del <span class="signature">Mtro. Roberto Ibarra Suárez</span><br>
    Versión 2026.1.0 | Todos los derechos reservados.
</div>
""", unsafe_allow_html=True)
