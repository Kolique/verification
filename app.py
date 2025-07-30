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

# Option pour le séparateur CSV
csv_separator = st.selectbox(
    "Quel est le séparateur de colonnes dans votre fichier CSV ?",
    options=[",", ";", "\t", "|"], # Virgule, Point-virgule, Tabulation, Pipe
    format_func=lambda x: f"Virgule (,)" if x == "," else (f"Point-virgule (;)" if x == ";" else (f"Tabulation (\\t)" if x == "\t" else "Pipe (|)"))
)
st.info(f"Le séparateur sélectionné est : **'{csv_separator}'**.")


df = None # Initialise df à None

if uploaded_file is not None:
    try:
        # Tente de lire le fichier avec le séparateur choisi
        df = pd.read_csv(uploaded_file, sep=csv_separator)
        st.success("Fichier chargé avec succès !")

        # Afficher des infos de debug utiles
        st.write("Type de l'objet chargé :", type(df))
        if isinstance(df, pd.DataFrame):
            st.write(f"Nombre de lignes : **{len(df)}**")
            st.write(f"Nombre de colonnes : **{len(df.columns)}**")
            st.write("Colonnes détectées :", df.columns.tolist())
            st.write("Aperçu des 5 premières lignes de votre fichier :")
            st.dataframe(df.head())
        else:
            st.error("Le fichier n'a pas pu être lu comme un DataFrame Pandas. Vérifiez le séparateur ou le format du fichier.")
            df = None # S'assurer que df est None si la lecture échoue

    except pd.errors.EmptyDataError:
        st.error("Le fichier CSV est vide.")
        df = None
    except pd.errors.ParserError as e:
        st.error(f"Erreur de lecture du CSV. Le fichier est peut-être mal formé ou le séparateur est incorrect. Erreur: {e}")
        st.info("Essayez de changer le séparateur ci-dessus ou de vérifier l'intégrité de votre fichier CSV.")
        df = None
    except Exception as e:
        st.error(f"Une erreur inattendue est survenue lors du chargement du fichier : {e}")
        st.info("Veuillez vous assurer que le fichier est un CSV valide et bien formaté.")
        df = None

# Le reste de l'application s'exécutera SEULEMENT si un DataFrame df a été créé
if df is not None:
    st.markdown("---") # Séparateur visuel
    st.header("2. Sélectionner les colonnes")

    # Si le DataFrame est vide après lecture (e.g. seulement les en-têtes)
    if df.empty:
        st.warning("Le fichier a été chargé, mais il semble vide (pas de données après les en-têtes). Impossible de sélectionner des colonnes.")
    elif len(df.columns) == 0:
        st.warning("Aucune colonne n'a été détectée dans votre fichier CSV. Veuillez vérifier l'intégrité du fichier et le séparateur.")
    else:
        # Sélecteurs de colonnes (s'affichent seulement si df est valide et a des colonnes)
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
                expected_commune = str(row[col_commune]).lower().strip()

                try:
                    location = geolocator.geocode(address_to_geocode, timeout=10)

                    if location:
                        df.loc[index, 'Latitude'] = location.latitude
                        df.loc[index, 'Longitude'] = location.longitude

                        geocoded_address_components = location.raw.get('address', {})
                        found_commune = None

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
            @st.cache_data
            def convert_df_to_csv(df):
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
