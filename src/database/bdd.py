import os
import sqlite3
import pandas as pd

class Bdd:
    """
    Fournit une interface de base pour interagir avec une base de données SQLite.
    
    Cette classe gère la création automatique du répertoire de stockage, 
    l'insertion de données à partir de DataFrames Pandas, et la récupération 
    d'informations structurelles ou transactionnelles.
    """

    def __init__(self, db_path: str):
        """
        Initialise la connexion et crée le dossier parent si nécessaire.

        Args:
        - db_path (str) : Chemin complet vers le fichier de base de données .db
        """
        self._db_path = db_path
        
        # Création automatique du dossier si inexistant
        folder = os.path.dirname(self._db_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)


    # --- [ Manipulation des Données ] ---
    def _add_data(self, df: pd.DataFrame, table_name: str):
        """
        Insère les données d'un DataFrame dans une table SQLite.

        Filtre automatiquement les colonnes pour ne garder que celles présentes 
        dans la définition de la table SQL et ignore les champs auto-incrémentés.

        Args:
        - df (pd.DataFrame) : Le jeu de données à insérer.
        - table_name (str) : Nom de la table cible.
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        # Récupération des informations sur les colonnes de la table
        cursor.execute(f"PRAGMA table_info({table_name});")
        table_info = cursor.fetchall()
        
        # Identification des colonnes existantes (nom, type, obligatoire, etc.)
        # On exclut généralement l'ID auto-incrémenté si nécessaire
        column_names = [info[1] for info in table_info]
        
        # Filtrage du DataFrame pour ne garder que les colonnes valides
        valid_columns = [col for col in df.columns if col in column_names]
        df_filtered = df[valid_columns]

        # Insertion via Pandas pour plus d'efficacité
        df_filtered.to_sql(table_name, connection, if_exists='append', index=False)
        
        connection.close()

    def _get_table_data(self, table_name: str) -> pd.DataFrame:
        """
        Récupère l'intégralité du contenu d'une table.

        Args:
        - table_name (str) : Nom de la table à interroger.

        Returns:
        - pd.DataFrame : Un DataFrame contenant toutes les lignes de la table.
        """
        assert isinstance(table_name, str), "Le nom de la table doit être une chaîne."

        try:
            connection = sqlite3.connect(self._db_path)
            # Lecture directe de la table vers un DataFrame
            dataframe = pd.read_sql_query(f"SELECT * FROM {table_name}", connection)
            connection.close()
            return dataframe
        except Exception as e:
            print(f"Erreur lors de la lecture de la table {table_name}: {e}")
            return pd.DataFrame()


    # --- [ Inspection de la Base ] ---
    def _get_all_tables_content(self) -> dict:
        """
        Récupère les données de toutes les tables présentes dans la base.

        Scanne les métadonnées SQLite pour lister les tables et exporte 
        chacune d'elles dans un dictionnaire de DataFrames.

        Returns:
            dict : Dictionnaire au format { 'nom_table': DataFrame }
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        # Requête pour lister toutes les tables utilisateur
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        all_tables_data = {}
        
        for table in tables:
            name = table[0]
            # Utilisation de la méthode interne pour charger le DataFrame
            all_tables_data[name] = pd.read_sql_query(f"SELECT * FROM {name}", connection)
        
        connection.close()
        return all_tables_data

    def _generate_unique_id(self, row: pd.Series) -> str:
        """
        Génère un identifiant unique basé sur le contenu d'une ligne.

        Utilise un hashage ou une concaténation des valeurs clés pour identifier
        de manière unique une transaction et éviter les doublons.

        Args:
        - row (pd.Series) : Une ligne de transaction.

        Returns:
            str : Un hash unique représentant la ligne.
        """
        import hashlib
        # Concaténation des valeurs clés pour créer une empreinte unique
        raw_string = f"{row.get('date_operation', '')}{row.get('libelle_operation', '')}{row.get('montant', '')}"
        return hashlib.md5(raw_string.encode()).hexdigest()