import os
import sqlite3

import pandas as pd


class BaseDatabase:
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
        Récupère le contenu d'une table en résolvant les pointeurs si nécessaire.

        Si la table demandée est 'categorized_operations', une jointure est effectuée
        pour transformer les IDs en valeurs lisibles.

        Args:
            - table_name (str) : Nom de la table à interroger.

        Returns:
            - pd.DataFrame : DataFrame contenant les données (résolues ou brutes).
        """
        assert isinstance(table_name, str), "Le nom de la table doit être une chaîne."

        # Définition des requêtes spécifiques pour résoudre les pointeurs
        # On utilise des alias (AS) pour éviter les collisions de noms
        queries = {
            "categorized_operations": """
                SELECT 
                    co.id AS entry_id,
                    c.name AS category_name,
                    sc.name AS sub_category_name,
                    r.operation_date,
                    r.short_label,
                    r.operation_type,
                    r.full_label,
                    r.amount,
                    r.id AS raw_id
                FROM categorized_operations co
                JOIN categories c ON co.category_id = c.id
                JOIN sub_categories sc ON co.sub_category_id = sc.id
                JOIN raw_data r ON co.raw_data_id = r.id
            """,
            "sub_categories": """
                SELECT 
                    sc.id,
                    c.name AS parent_category,
                    sc.name AS sub_category_name
                FROM sub_categories sc
                JOIN categories c ON sc.category_id = c.id
            """
        }

        # On choisit la requête : soit une requête complexe définie au-dessus, 
        # soit un SELECT * classique par défaut.
        sql_query = queries.get(table_name, f"SELECT * FROM {table_name}")

        try:
            connection = sqlite3.connect(self._db_path)
            dataframe = pd.read_sql_query(sql_query, connection)
            connection.close()
            
            return dataframe
        
        except Exception as error:
            print(f"Erreur lors de la lecture de la table {table_name}: {error}")
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
