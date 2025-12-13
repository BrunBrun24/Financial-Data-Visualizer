import os
import sqlite3

import pandas as pd

class Bdd:
    """
    Cette classe fournit une interface de base pour interagir avec une base de données SQLite.
    Elle gère la création automatique du dossier de la base, l'insertion de données depuis des DataFrames,
    la vérification de l'existence de lignes, et la récupération des données sous forme de pandas DataFrame.

    Attributs :
        _db_path (str) : Chemin vers le fichier SQLite.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        
        folder = os.path.dirname(self._db_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)


    def _ajouter_donnees(self, df: pd.DataFrame, table_name: str):
        """
        Ajoute les données d'un DataFrame dans une table SQLite en respectant les colonnes obligatoires
        et en ignorant les colonnes auto-incrémentées.

        Args:
            df (pd.DataFrame) : Le DataFrame contenant les données à insérer.
            table_name (str) : Le nom de la table SQLite.
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Obtenir info colonnes
        cursor.execute(f"PRAGMA table_info({table_name});")
        table_info = cursor.fetchall()

        # Colonnes obligatoires = celles SANS default + SANS autoincrement
        mandatory_columns = []
        for cid, name, col_type, notnull, default_value, pk in table_info:
            if pk == 1:  # clé primaire → ignore
                continue
            if default_value is not None:  # valeur par défaut → ignore
                continue
            mandatory_columns.append(name)

        # Vérification simple
        if sorted(df.columns) != sorted(mandatory_columns):
            print(f"Erreur : colonnes inattendues pour la table '{table_name}'.")
            print(f"Colonnes du DataFrame : {list(df.columns)}")
            print(f"Colonnes obligatoires attendues : {mandatory_columns}")
            raise ValueError("Colonnes incompatibles.")
        
        # Conversion des Timestamp en strings (SQLite ne supporte pas pandas.Timestamp)
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                df[col] = df[col].dt.strftime('%Y-%m-%d')

        # Insertion des données
        for row in df.itertuples(index=False, name=None):
            cursor.execute(
                f"INSERT INTO {table_name} ({', '.join(df.columns)}) "
                f"VALUES ({', '.join(['?'] * len(df.columns))})",
                row
            )

        conn.commit()
        conn.close()

    def _ligne_existe(self, table_name: str, conditions: dict) -> bool:
        """
        Vérifie si au moins une ligne existe dans une table SQLite selon des conditions données.

        Args:
            table_name (str) : Nom de la table à interroger.
            conditions (dict) : Dictionnaire {colonne: valeur} représentant les conditions.

        Returns:
            bool : True si une ligne existe, False sinon.
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Construction dynamique du WHERE
        where_clause = " AND ".join([f"{col} = ?" for col in conditions.keys()])
        values = list(conditions.values())

        query = f"SELECT 1 FROM {table_name} WHERE {where_clause} LIMIT 1"
        cursor.execute(query, values)
        
        result = cursor.fetchone()
        
        conn.close()
        
        return result is not None

    def _get_all_tables_data(self) -> dict:
        """
        Récupère toutes les données de toutes les tables SQLite et les retourne sous forme de dictionnaire.

        Returns:
            dict : Clés = noms de tables, valeurs = DataFrames contenant les données.
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        # Exécuter la requête pour récupérer les tables dans la base de données
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Créer un dictionnaire pour stocker les données
        all_tables_data = {}
        
        # Pour chaque table, récupérer les données dans un DataFrame
        for table in tables:
            table_name = table[0]
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql_query(query, conn)
            
            # Ajouter le DataFrame au dictionnaire avec le nom de la table comme clé
            all_tables_data[table_name] = df
        
        conn.close()
        
        return all_tables_data
    
    def _get_db(self, nom_table: str) -> pd.DataFrame:
        """
        Lit le contenu complet d'une table SQLite et le retourne sous forme de DataFrame.

        Args:
            nom_table (str) : Nom de la table à lire.

        Returns:
            pd.DataFrame : Contenu de la table.
        """
        assert isinstance(nom_table, str), "Le nom de la table doit être une chaîne de caractères."

        try:
            connection = sqlite3.connect(self._db_path)
            dataframe = pd.read_sql_query(f"SELECT * FROM {nom_table}", connection)
            connection.close()
            return dataframe
        except Exception as e:
            raise RuntimeError(f"Erreur lors de la lecture de la table '{nom_table}': {e}")
