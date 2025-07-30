import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="Géocodeur d'Adresses",
    page_icon="🗺️",
    layout="wide"
)

# --- Titre de l'application ---
st.title("🗺️ Application de Géocodage d'Adresses")
st.markdown("Cette application vous permet de géocoder des adresses depuis un fichier CSV et de vérifier la cohérence avec une colonne de commune.")

# --- Section d'upload de fichier ---
st.header("1. Importer votre fichier de données")
uploaded_file = st.file_uploader("Choisissez un fichier CSV", type="csv")

df = None # Initialise df à None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("Fichier chargé avec succès !")
        st.write("Aperçu des 5 premières lignes de votre fichier :")
        st.dataframe(df.head())

    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier : {e}")
        st.info("Veuillez vous assurer que le fichier est un CSV valide et bien formaté.")

# --- Section de sélection des colonnes (si un fichier est chargé) ---
if df is not None:
    st.header("2. Sélectionner les colonnes")

    col_adresse = st.selectbox(
        "Choisissez la colonne contenant les adresses à géocoder :",
        options=df.columns
    )

    col_commune = st.selectbox(
        "Choisissez la colonne contenant la commune pour la vérification :",
        options=df.columns
    )

    st.info(f"Vous avez choisi la colonne **'{col_adresse}'** pour les adresses et **'{col_commune}'** pour la vérification de la commune.")

    # --- Section de géocodage et affichage des résultats ---
    st.header("3. Lancer le géocodage")
    if st.button("Lancer le géocodage et la vérification"):
        st.write("Géocodage en cours... Cela peut prendre un certain temps pour 1200 lignes.")

        # Initialisation du géocodeur Nominatim
        # Il est important de fournir un user_agent unique pour respecter les politiques d'utilisation de Nominatim
        geolocator = Nominatim(user_agent="geocoding_streamlit_app_v1")

        # Préparation des nouvelles colonnes
        df['Latitude'] = None
        df['Longitude'] = None
        df['Commune_Geocoded'] = None
        df['Verifie_Commune'] = "Non vérifié" # Colonne pour le statut de vérification

        progress_bar = st.progress(0)
        total_rows = len(df)

        for index, row in df.iterrows():
            address_to_geocode = str(row[col_adresse])
            expected_commune = str(row[col_commune]).lower().strip() # Pour une comparaison insensible à la casse

            try:
                location = geolocator.geocode(address_to_geocode, timeout=10) # Augmente le timeout si nécessaire

                if location:
                    df.loc[index, 'Latitude'] = location.latitude
                    df.loc[index, 'Longitude'] = location.longitude

                    # Tentative d'extraction de la ville/commune depuis l'adresse géocodée
                    # Les adresses retournées par Nominatim ont une structure dictionary dans 'raw'
                    # On cherche dans les clés courantes comme 'city', 'town', 'village', 'county'
                    geocoded_address_components = location.raw.get('address', {})
                    found_commune = None

                    # Liste des clés potentielles pour la commune, par ordre de préférence
                    commune_keys = ['city', 'town', 'village', 'county', 'municipality']
                    for key in commune_keys:
                        if key in geocoded_address_components:
                            found_commune = geocoded_address_components[key]
                            break

                    if found_commune:
                        df.loc[index, 'Commune_Geocoded'] = found_commune
                        if found_commune.lower().strip() == expected_commune:
                            df.loc[index, 'Verifie_Commune'] = "OK"
                        else:
                            df.loc[index, 'Verifie_Commune'] = f"Différent ({found_commune})"
                    else:
                        df.loc[index, 'Commune_Geocoded'] = "Non trouvée"
                        df.loc[index, 'Verifie_Commune'] = "Commune géocodée introuvable"

                else:
                    df.loc[index, 'Latitude'] = "Non trouvée"
                    df.loc[index, 'Longitude'] = "Non trouvée"
                    df.loc[index, 'Commune_Geocoded'] = "Non trouvée"
                    df.loc[index, 'Verifie_Commune'] = "Adresse non géocodée"

            except GeocoderTimedOut:
                df.loc[index, 'Latitude'] = "Erreur Timeout"
                df.loc[index, 'Longitude'] = "Erreur Timeout"
                df.loc[index, 'Commune_Geocoded'] = "Erreur Timeout"
                df.loc[index, 'Verifie_Commune'] = "Erreur réseau (Timeout)"
            except GeocoderServiceError as e:
                df.loc[index, 'Latitude'] = "Erreur Service"
                df.loc[index, 'Longitude'] = "Erreur Service"
                df.loc[index, 'Commune_Geocoded'] = "Erreur Service"
                df.loc[index, 'Verifie_Commune'] = f"Erreur service ({e})"
            except Exception as e:
                df.loc[index, 'Latitude'] = "Erreur Inconnue"
                df.loc[index, 'Longitude'] = "Erreur Inconnue"
                df.loc[index, 'Commune_Geocoded'] = "Erreur Inconnue"
                df.loc[index, 'Verifie_Commune'] = f"Erreur inattendue ({e})"

            progress_bar.progress((index + 1) / total_rows)

        st.success("Géocodage terminé !")
        st.subheader("Résultats du Géocodage et de la Vérification")
        st.dataframe(df)

        # --- Section d'exportation ---
        st.header("4. Exporter les résultats")
        @st.cache_data # Mise en cache pour éviter de re-générer le CSV à chaque interaction
        def convert_df_to_csv(df):
            # IMPORTANT: Cache the conversion to prevent computation on every rerun
            return df.to_csv(index=False).encode('utf-8')

        csv_data = convert_df_to_csv(df)

        st.download_button(
            label="Télécharger les résultats en CSV",
            data=csv_data,
            file_name="adresses_geocoded_verified.csv",
            mime="text/csv",
        )
        st.info("Le fichier CSV téléchargé inclura les colonnes Latitude, Longitude, Commune_Geocoded et Verifie_Commune.")

else:
    st.info("Veuillez d'abord télécharger un fichier CSV pour commencer.")

st.markdown("---")
st.markdown("Développé avec ❤️ par votre Partenaire de Code.")
