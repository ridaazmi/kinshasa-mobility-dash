import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import numpy as np

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Kinshasa Mobility Dashboard", page_icon="🚌")

# --- CUSTOM CSS FOR "DECISION-MAKER" DESIGN ---
st.markdown("""
<style>
/* Style the metric cards */
div[data-testid="metric-container"] {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1);
}
/* Title style adjustments */
h1, h2, h3 {
    color: #1E3A8A;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
</style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES (Mise en cache pour la rapidité) ---
@st.cache_data
def load_data():
    try:
        df_trips = pd.read_csv("data/Trips_0_20251128.csv")
        df_stops = pd.read_csv("data/Stops_0_20251128.csv")
        df_pax = pd.read_csv("data/Passengers_0_20251128.csv")
        
        df_trips['Trip ID'] = df_trips['Trip ID'].astype(str)
        df_stops['Trip ID'] = df_stops['Trip ID'].astype(str)
        
        if 'Route Description' in df_trips.columns:
            route_map = df_trips.set_index('Trip ID')['Route Description'].to_dict()
            df_stops['Route'] = df_stops['Trip ID'].map(route_map)
        
        return df_trips, df_stops, df_pax
    except FileNotFoundError as e:
        st.error(f"Erreur : Fichier manquant. {e}")
        return None, None, None

df_trips, df_stops, df_pax = load_data()

# --- GENERATION DE DONNEES SYNTHETIQUES (SI MANQUANTES) ---
if df_pax is not None and df_pax.empty and df_trips is not None:
    total_pax = df_trips['Total Passengers'].sum() if 'Total Passengers' in df_trips.columns else 1000
    genders = np.random.choice(['Homme', 'Femme'], size=int(total_pax), p=[0.55, 0.45])
    ages = np.random.choice(['0-18', '19-35', '36-50', '50+'], size=int(total_pax), p=[0.1, 0.4, 0.3, 0.2])
    df_pax = pd.DataFrame({'Gender': genders, 'Age Group': ages})
    st.toast("⚠️ Données démographiques simulées (Fichier source vide)", icon="ℹ️")

if df_trips is not None:
    # --- IDENTITÉ VISUELLE ---
    st.sidebar.image("logo/logo_FDCO.png", use_container_width=True)
    
    # --- BARRE LATÉRALE (FILTRES & EXPORT) ---
    st.sidebar.title("🎛️ Tableau de Bord", help="Menu principal pour contrôler l'affichage du tableau de bord.")
    
    # Filtres
    st.sidebar.subheader("📍 Filtres Lignes", help="Section pour filtrer les données par ligne de transport.")
    all_routes = df_trips['Route Description'].unique().tolist() if 'Route Description' in df_trips.columns else ["Toutes"]
    selected_routes = st.sidebar.multiselect("Choisir les Lignes", all_routes, default=all_routes[:min(3, len(all_routes))], help="Sélectionnez une ou plusieurs lignes pour analyser leurs performances spécifiques.")
    
    trips_filtered = df_trips[df_trips['Route Description'].isin(selected_routes)] if 'Route Description' in df_trips.columns else df_trips
    trip_ids_filtered = trips_filtered['Trip ID'].unique()
    stops_filtered = df_stops[df_stops['Trip ID'].isin(trip_ids_filtered)]

    # Export Report
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Exportation Décideur", help="Outils d'exportation de données pour rapports et réunions.")
    st.sidebar.caption("Téléchargez les statistiques de la sélection pour les réunions.")
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')
    csv_data = convert_df(trips_filtered)
    st.sidebar.download_button(
        label="📊 Télécharger Rapport (CSV)",
        data=csv_data,
        file_name='rapport_kinshasa_mobilite.csv',
        mime='text/csv',
        help="Génère un fichier CSV contenant les trajets filtrés, idéal pour une analyse externe sur Excel."
    )

    # --- EN-TÊTE PRINCIPAL ---
    st.title("🚇 UK support to high-impact infrastructure and urban projects in DRC - Phase 2", help="Tableau de bord de suivi de la performance et de l'intermodalité des transports à Kinshasa.")
    st.markdown("Interface stratégique pour décideurs : Suivi de la performance et de l'intermodalité.")

    # --- TABS (ONGLETS) ---
    tab1, tab2, tab3 = st.tabs(["🗺️ Carte Stratégique", "📊 Performances & Revenus", "🕒 Analyse Temporelle & Détails"])

    # --- ONGLET 1 : CARTE INTERACTIVE (FOLIUM) ---
    with tab1:
        st.markdown(f"**Cartographie des lignes :** {', '.join(selected_routes)}")
        
        if not stops_filtered.empty and 'Stop Lat' in stops_filtered.columns:
            center_lat = stops_filtered['Stop Lat'].mean()
            center_lon = stops_filtered['Stop Lon'].mean()
        else:
            center_lat, center_lon = -4.322447, 15.307045 # Default Kinshasa center
            
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB positron") # Cleaner tiles for decision makers
        
        # Points of interest for Intermodality
        pois = {
            "Gare Centrale": [-4.3065, 15.3146],
            "Marché Central": [-4.3168, 15.3129],
            "Aéroport de N'djili": [-4.3856, 15.4442],
            "Pompage": [-4.3323, 15.2366]
        }
        for name, coords in pois.items():
            folium.Marker(
                location=coords,
                popup=f"<b>⭐ {name}</b><br>Hub Intermodal Stratégique",
                icon=folium.Icon(color="orange", icon="star"),
            ).add_to(m)

        for route in selected_routes:
            try:
                example_trip = trips_filtered[trips_filtered['Route Description'] == route].iloc[0]['Trip ID']
                route_stops = stops_filtered[stops_filtered['Trip ID'] == example_trip].sort_values('Sequence')
                points = route_stops[['Stop Lat', 'Stop Lon']].dropna().values.tolist()
                folium.PolyLine(points, color="#1E3A8A", weight=5, opacity=0.8, tooltip=route).add_to(m)
                
                for _, stop in route_stops.iterrows():
                    activity = stop.get('Pax On', 0) + stop.get('Pax Off', 0)
                    radius = 4 + (activity * 0.3)
                    folium.CircleMarker(
                        location=[stop['Stop Lat'], stop['Stop Lon']],
                        radius=radius,
                        popup=f"<b>{stop.get('Name','Arrêt')}</b><br>Activité: {activity}",
                        color="#E11D48",
                        fill=True,
                        fill_opacity=0.8
                    ).add_to(m)
            except Exception as e:
                pass

        st_folium(m, width="100%", height=600, returned_objects=[])

    # --- ONGLET 2 : ANALYSE RÉSEAU (MACRO & REVENUS) ---
    with tab2:
        # KPI Optimisation des Revenus
        st.markdown("### 💰 Indicateurs Financiers et Opérationnels")
        
        total_revenue = trips_filtered['Revenue'].sum() if 'Revenue' in trips_filtered.columns else 0
        total_pax = trips_filtered['Total Passengers'].sum() if 'Total Passengers' in trips_filtered.columns else 0
        
        potential_revenue = total_pax * 1000 # Tarif fixe théorique 1000 FC
        revenue_leakage = potential_revenue - total_revenue
        leakage_perc = (revenue_leakage / potential_revenue * 100) if potential_revenue > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenus Actuels (FC)", f"{total_revenue:,.0f} FC", "Recettes déclarées", delta_color="off", help="Somme totale des revenus (Revenue) générés sur les trajets sélectionnés.")
        c2.metric("Revenus Potentiels", f"{potential_revenue:,.0f} FC", "Basé sur 1000 FC / Pax", delta_color="normal", help="Estimation du revenu idéal basé sur le nombre total de passagers multiplié par un tarif fixe (1000 FC).")
        c3.metric("🚨 Fuite Estimée (Manque à gagner)", f"{revenue_leakage:,.0f} FC", f"-{leakage_perc:.1f}% Perte potentielle", delta_color="inverse", help="Différence entre le revenu potentiel et le revenu actuel déclaré (Fuite de revenus potentielle).")
        c4.metric("👥 Passagers Transportés", f"{total_pax:,.0f}", help="Total cumulé du nombre de passagers (Total Passengers) transportés sur ces lignes.")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Performance Financière par Ligne", help="Ce graphique (Bar Chart) compare les revenus réels cumulés par chaque ligne. La couleur indique le volume de passagers transportés.")
            if 'Route Description' in trips_filtered.columns and not trips_filtered.empty:
                perf_by_route = trips_filtered.groupby('Route Description')[['Revenue', 'Total Passengers']].sum().reset_index()
                fig_perf = px.bar(perf_by_route, x='Route Description', y='Revenue', 
                                  color='Total Passengers', 
                                  color_continuous_scale="Viridis",
                                  title="Revenus réels vs Volume Passagers",
                                  labels={'Revenue': 'Revenus (FC)', 'Route Description': 'Ligne'},
                                  template="plotly_white")
                st.plotly_chart(fig_perf, use_container_width=True)
            
        with col2:
            st.subheader("Profil Démographique", help="Ce graphique (Pie Chart) illustre la répartition homme/femme des passagers selon l'échantillon ou les données générées.")
            if not df_pax.empty and 'Gender' in df_pax.columns:
                gender_counts = df_pax['Gender'].value_counts().reset_index()
                gender_counts.columns = ['Genre', 'Nombre']
                fig_pie = px.pie(gender_counts, values='Nombre', names='Genre', 
                                 title="Répartition par Genre", 
                                 hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel,
                                 template="plotly_white")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Données démographiques indisponibles.")

    # --- ONGLET 3 : ANALYSE TEMPORELLE & DÉTAIL ---
    with tab3:
        st.subheader("🕒 Analyse Temporelle (Affluence par tranche horaire)", help="Ce graphique agrège l'activité totale de passagers (montées et descentes concentrées) réparties par grandes périodes horaires.")
        
        stops_analysis = df_stops[df_stops['Trip ID'].isin(trip_ids_filtered)].copy()
        if 'Arrival Time' in stops_analysis.columns:
            def get_time_slot(hour):
                if pd.isna(hour): return "Inconnu"
                if 6 <= hour < 9: return "1. Matin (06:00 - 08:59)"
                elif 12 <= hour < 14: return "2. Midi (12:00 - 13:59)"
                elif 16 <= hour < 19: return "3. Soir (16:00 - 18:59)"
                else: return "4. Heures Creuses"
                
            stops_analysis['Hour'] = pd.to_datetime(stops_analysis['Arrival Time'], format='%H:%M:%S', errors='coerce').dt.hour
            stops_analysis['Tranche Horaire'] = stops_analysis['Hour'].apply(get_time_slot)
            
            stops_analysis['Total Activity'] = stops_analysis.get('Pax On', 0) + stops_analysis.get('Pax Off', 0)
            
            time_stats = stops_analysis.groupby('Tranche Horaire')['Total Activity'].sum().reset_index()
            time_stats = time_stats[time_stats['Tranche Horaire'] != "Inconnu"].sort_values('Tranche Horaire')
            
            if not time_stats.empty:
                fig_time = px.bar(time_stats, x='Tranche Horaire', y='Total Activity',
                                  text='Total Activity',
                                  title="Charge réseau par tranche horaire (Heures de pointe)",
                                  color='Tranche Horaire',
                                  color_discrete_sequence=px.colors.qualitative.Set2,
                                  labels={'Total Activity': 'Flux Passagers (Montées+Descentes)'},
                                  template="plotly_white")
                fig_time.update_traces(texttemplate='%{text:.2s}', textposition='outside')
                st.plotly_chart(fig_time, use_container_width=True)
            else:
                st.info("Format d'heure non reconnu ou données manquantes.")
        else:
            st.info("La colonne 'Arrival Time' est manquante pour l'analyse temporelle.")

        st.markdown("---")
        st.subheader("🔬 Zoom Micro : Profil de Charge", help="Cette section permet d'analyser en détail l'évolution du remplissage du bus pour un trajet (Trip ID) spécifique.")
        
        if len(trip_ids_filtered) > 0:
            selected_trip_id = st.selectbox("Sélectionner un Trajet pour Analyse Détaillée (ID)", trip_ids_filtered, help="Choisissez l'identifiant d'un trajet précis pour retracer l'occupation séquence par séquence.")
            single_trip_data = stops_analysis[stops_analysis['Trip ID'] == selected_trip_id].sort_values('Sequence')
            trip_info = trips_filtered[trips_filtered['Trip ID'] == selected_trip_id].iloc[0]
            
            single_trip_data['Stop Label'] = single_trip_data.apply(
                lambda x: f"Arrêt {x.get('Sequence', 0)}" if x.get('Name', 'Inconnu') == 'Inconnu' else f"{x.get('Name', '')} ({x.get('Sequence', 0)})", axis=1
            )
            
            st.info(f"**Ligne :** {trip_info.get('Route Description', 'N/A')} | **Véhicule :** {trip_info.get('Vehicle Reg No', 'N/A')} | **Revenu :** {trip_info.get('Revenue', 0)} FC")
            
            if 'Occupancy' in single_trip_data.columns:
                fig_load = px.area(single_trip_data, x='Stop Label', y='Occupancy', 
                                   title=f"Profil de Charge Embarquée",
                                   labels={'Stop Label': 'Séquence des Arrêts', 'Occupancy': 'Passagers à bord'},
                                   template="plotly_white")
                st.plotly_chart(fig_load, use_container_width=True)

    # --- NOUVEL ONGLET : ANALYSE APPROFONDIE ---
    with st.expander("📈 Analyse Approfondie (Beta)", expanded=False):
        st.markdown("## 🧠 Insights Mobilité")
        
        tab_deep1, tab_deep2, tab_deep3 = st.tabs(["🚀 Vitesse Commerciale", "⏱️ Temps d'Arrêt", "👥 Densité de Passagers"])
        
        with tab_deep1:
            st.subheader("Vitesse Commerciale par Ligne", help="Graphique en barres affichant la vitesse commerciale moyenne estimée pour chaque ligne (Distance totale du trajet divisée par le temps total estimé).")
            route_speeds = []
            for route in selected_routes:
                route_trips = trips_filtered[trips_filtered['Route Description'] == route]
                if route_trips.empty: continue
                avg_distance = route_trips['Distance'].mean()
                trip_ids = route_trips['Trip ID'].unique()
                durations = []
                for tid in trip_ids[:10]:
                    t_stops = stops_filtered[stops_filtered['Trip ID'] == tid].sort_values('Sequence')
                    if len(t_stops) > 1 and 'Arrival Time' in t_stops.columns and 'Departure Time' in t_stops.columns:
                        try:
                            start = pd.to_datetime(t_stops.iloc[0]['Arrival Time'], format='%H:%M:%S', errors='coerce')
                            end = pd.to_datetime(t_stops.iloc[-1]['Departure Time'], format='%H:%M:%S', errors='coerce')
                            duration_h = (end - start).total_seconds() / 3600
                            if duration_h > 0:
                                durations.append(duration_h)
                        except:
                            pass
                if durations:
                    avg_duration = sum(durations) / len(durations)
                    speed = avg_distance / avg_duration if avg_duration > 0 else 0
                    route_speeds.append({'Ligne': route, 'Vitesse (km/h)': speed})
            
            if route_speeds:
                df_speed = pd.DataFrame(route_speeds)
                fig_speed = px.bar(df_speed, x='Ligne', y='Vitesse (km/h)', color='Vitesse (km/h)',
                                   color_continuous_scale='RdYlGn', title="Vitesse Commerciale Moyenne")
                st.plotly_chart(fig_speed, use_container_width=True)
            else:
                st.warning("Données temporelles insuffisantes pour calculer la vitesse.")

        with tab_deep2:
            st.subheader("Temps d'Arrêt (Dwell Time)", help="Affiche le temps d'attente moyen en secondes passé à l'arrêt par véhicule sur la ligne choisie.")
            if 'Dwell Time' in stops_analysis.columns:
                def parse_dwell(t_str):
                    try:
                        parts = str(t_str).split(':')
                        if len(parts) == 3: return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                        return 0
                    except: return 0
                stops_analysis['Dwell Seconds'] = stops_analysis['Dwell Time'].apply(parse_dwell)
                avg_dwell = stops_analysis.groupby('Route')['Dwell Seconds'].mean().reset_index()
                fig_dwell = px.bar(avg_dwell, x='Route', y='Dwell Seconds', 
                                   title="Temps d'attente moyen aux arrêts (secondes)",
                                   color='Dwell Seconds', color_continuous_scale='OrRd')
                st.plotly_chart(fig_dwell, use_container_width=True)
            else:
                st.info("La colonne 'Dwell Time' est manquante.")

        with tab_deep3:
            st.subheader("Densité de Passagers", help="Heatmap illustrant l'occupation moyenne par séquence d'arrêt. Les zones claires/jaunâtres indiquent une forte affluence de passagers à ce moment du trajet.")
            if 'Occupancy' in stops_analysis.columns and 'Sequence' in stops_analysis.columns:
                occupancy_heatmap = stops_analysis.groupby(['Route', 'Sequence'])['Occupancy'].mean().reset_index()
                fig_heat = px.density_heatmap(occupancy_heatmap, x='Sequence', y='Route', z='Occupancy',
                                              title="Heatmap de Charge (Où les bus sont-ils pleins ?)",
                                              color_continuous_scale='Viridis')
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("Colonnes manquantes pour la cartographie de densité.")

else:
    st.warning("Veuillez placer les fichiers CSV dans le dossier et relancer l'application.")