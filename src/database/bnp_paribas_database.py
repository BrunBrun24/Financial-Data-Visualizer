import os
import shutil
import sqlite3

import pandas as pd

from .base_database import BaseDatabase


class BnpParibasDatabase(BaseDatabase):
    """
    Gère l'accès et la manipulation des données financières d'un compte bancaire.

    Cette classe hérite de `BaseDatabase` et fournit des fonctionnalités pour :
    - Créer et maintenir la structure de la base de données en anglais.
    - Ajouter et récupérer des opérations financières.
    - Vérifier la cohérence des catégories par rapport à la configuration.
    - Grouper et organiser les opérations par année pour les analyses.
    """

    _BUTTON_LABELS = {
        'Épargne': ["Livret A"],
        'Investissement': ["CTO", "Autres"],
        'Revenus': [
            "Aides et allocations", "Salaires et revenus d'activité", 
            "Revenus de placement", "Pensions", "Intérêts", "Loyers", 
            "Dividendes", "Remboursement", "Chèques reçus", "Déblocage emprunt", 
            "Virements reçus", "Virements internes", "Cashback", "Autres"
        ],
        'Abonnement': ["Téléphone", "Internet", "Streaming", "Logiciels", "Musiques"],
        'Impôts': [
            "Impôts sur taxes", "Impôt sur le revenu", "Impôt sur la fortune", 
            "Taxe foncière", "Taxe d'habitation", "Contributions sociales (CSG / CRDS)", 
            "Bourse (flat tax)"
        ],
        'Banque': [
            "Remboursement emprunt", "Frais bancaires", 
            "Prélèvement carte débit différé", "Retrait d'espèces", "Autres"
        ],
        "Logement": [
            "Électricité, gaz", "Eau", "Chauffage", "Loyer", "Prêt immobilier", 
            "Bricolage et jardinage", "Assurance habitation", 
            "Mobilier, électroménager, déco", "Autres"
        ],
        'Loisirs et sorties': [
            "Voyages, vacances", "Restaurants - Fast food", "Bars", 
            "Boites de nuit", "Divertissements, sorties culturelles", 
            "Sports", "Sorties", "Pari perdu", "Concerts", "Spectacles", "Autres"
        ],
        'Santé': ["Médecin", "Pharmacie", "Dentiste", "Mutuelle", "Opticien", "Hôpital"],
        'Transports et véhicules': [
            "Assurance véhicule", "Crédit auto", "Carburant", "Entretien véhicule", 
            "Transports en commun", "Avion", "Train", "Taxis, VTC", 
            "Location de véhicule", "Péage", "Stationnement"
        ],
        'Vie quotidienne': [
            "Alimentation - Supermarché", "Frais animaux", "Coiffeur, soins", 
            "Habillement", "Achat, shopping", "Jeux vidéo", "Frais postaux", 
            "Achat multimédias - High tech", "Aide à domicile", "Cadeaux", 
            "Échange d'argent", "Autres"
        ],
        'Enfants': [
            "Pension alimentaire", "Crèche, baby-sitter", "Scolarité, études", 
            "Argent de poche", "Activités enfants"
        ],
        'Amendes': ["Amende de stationnement"],
        'Couple': [
            'Aides financières', 'Cadeaux - Petits plaisirs', 'Restaurants - Nourritures',
            'Voyages & week-ends', 'Loisirs & activités', 'Abonnements partagés'
        ],
        'Parents': ['Aides'],
        'Scolarité': ['Frais de scolarité', 'Alimentation'],
    }

    def __init__(self, db_path: str):
        """
        Initialise la connexion et prépare la structure de la base de données.

        Prépare l'environnement de la base de données en s'assurant que le schéma 
        SQL est présent, que les catégories par défaut sont insérées et que 
        l'intégrité des données est respectée par rapport à la configuration actuelle.

        Agrs:
        - db_path (str) : Chemin complet vers le fichier de base de données SQLite.
        """
        super().__init__(db_path)
        self.__create_database_schema()
        self.__verify_category_consistency()
        self.__insert_default_categories()


    # --- [ Méthodes principales pour manipuler les opérations et fusionner les bases ] ---
    def add_raw_data(self, df: pd.DataFrame):
        """
        Ajoute des lignes dans la table `raw_data` en gérant les doublons légitimes.
        
        Si une opération identique apparaît plusieurs fois dans le DataFrame, on vérifie
        si le même nombre d'occurrences existe en base. On n'insère que les exemplaires
        manquants.

        Args:
            df (pd.DataFrame): Données à ajouter (colonnes : date_operation, 
                               libelle_court, type_operation, libelle_operation, montant).
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        # Nettoyage et conversion des dates pour SQLite
        working_df = df.copy()
        for column in working_df.columns:
            if working_df[column].dtype == "datetime64[ns]":
                working_df[column] = working_df[column].dt.strftime("%Y-%m-%d")

        # Identification et comptage des occurrences dans le DataFrame fourni
        # On groupe par toutes les colonnes de données pour compter les doublons
        colonnes_cles = ['operation_date', 'short_label', 'operation_type', 'full_label', 'amount']
        # S'assurer que les colonnes du DF correspondent aux noms attendus pour le groupby
        working_df.columns = colonnes_cles
        df_counts = working_df.groupby(colonnes_cles, dropna=False).size().reset_index(name='nb_occurrences_df')

        rows_to_insert = []

        # Requête de comptage en base de données
        # Utilisation de IS pour gérer correctement les valeurs NULL (nan)
        count_sql = """
            SELECT COUNT(*) FROM raw_data 
            WHERE operation_date IS ?
            AND short_label IS ?
            AND operation_type IS ?
            AND full_label IS ?
            AND amount IS ?
        """

        for row in df_counts.itertuples(index=False):
            # Préparation des paramètres pour la requête SQL (les 5 premières colonnes)
            params = (row[0], row[1], row[2], row[3], row[4])
            nb_dans_df = row.nb_occurrences_df

            # On compte combien de fois cette opération exacte existe déjà en BDD
            cursor.execute(count_sql, params)
            nb_dans_bdd = cursor.fetchone()[0]

            # Si le fichier contient plus d'occurrences que la BDD, on ajoute la différence
            nb_a_ajouter = nb_dans_df - nb_dans_bdd
            
            if nb_a_ajouter > 0:
                for _ in range(nb_a_ajouter):
                    rows_to_insert.append(params)

        if rows_to_insert:
            insert_sql = """
                INSERT INTO raw_data
                (operation_date, short_label, operation_type, full_label, amount)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.executemany(insert_sql, rows_to_insert)

        connection.commit()
        connection.close()
        
    def merge_bank_databases(source_db_path: str, target_db_path: str, output_path: str):
        """
        Fusionne deux bases de données bancaires en préservant l'intégrité référentielle.

        Cette fonction crée une nouvelle base de données à partir de la première, puis
        importe les données de la seconde. Elle gère la réassignation des clés étrangères
        pour éviter que les liens entre catégories et opérations ne soient rompus à cause
        de la réindexation des identifiants (Auto-increment).

        Args:
            source_db_path (str): Chemin vers la première base de données (base).
            target_db_path (str): Chemin vers la seconde base de données à intégrer.
            output_path (str): Chemin du fichier de destination final.
        """
        try:
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            shutil.copy2(source_db_path, output_path)
            
            connection = sqlite3.connect(output_path)
            cursor = connection.cursor()
            cursor.execute(f"ATTACH DATABASE '{target_db_path}' AS db_to_merge")

            # Fusion des catégories et sous-catégories (nom -> name)
            cursor.execute("INSERT OR IGNORE INTO categories (name) SELECT name FROM db_to_merge.categories")
            
            cursor.execute("""
                INSERT OR IGNORE INTO sub_categories (category_id, name) 
                SELECT (SELECT id FROM categories WHERE name = c.name), sc.name 
                FROM db_to_merge.sub_categories sc
                JOIN db_to_merge.categories c ON sc.category_id = c.id
            """)

            # Fusion des données brutes
            cols_raw = "operation_date, short_label, operation_type, full_label, amount, processed"
            cursor.execute(f"INSERT INTO raw_data ({cols_raw}) SELECT {cols_raw} FROM db_to_merge.raw_data")

            # Fusion des opérations catégorisées avec remappage des IDs
            cursor.execute("""
                INSERT INTO categorized_operations (
                    category_id, sub_category_id, raw_data_id, 
                    operation_date, short_label, operation_type, full_label, amount
                )
                SELECT 
                    (SELECT id FROM categories WHERE name = (SELECT name FROM db_to_merge.categories WHERE id = co.category_id)),
                    (SELECT id FROM sub_categories WHERE name = (SELECT name FROM db_to_merge.sub_categories WHERE id = co.sub_category_id)),
                    (SELECT id FROM raw_data WHERE full_label = co.full_label AND operation_date = co.operation_date AND amount = co.amount),
                    operation_date, short_label, operation_type, full_label, amount
                FROM db_to_merge.categorized_operations co
            """)

            connection.commit()
            cursor.execute("DETACH DATABASE db_to_merge")
            connection.close()

        except Exception as error:
            raise RuntimeError(f"Échec du processus de fusion : {str(error)}")


    # --- [ Méthodes protégées liées à la récupération et l'enregistrement des transactions ] ---
    def _get_category_mappings(self) -> tuple:
        """
		Charge toutes les catégories et sous-catégories depuis la base de données.

		Returns:
		- category_ids : dictionnaire { 'Categorie': categorie_id }
		- sub_category_ids : dictionnaire { 'Categorie': { 'Sous-categorie': sous_categorie_id } }
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        category_rows = cursor.fetchall()

        category_ids = {}
        sub_category_ids = {}

        for cat_id, cat_name in category_rows:
            category_ids[cat_name] = cat_id

            cursor.execute("""
                SELECT id, name FROM sub_categories
                WHERE category_id = ? ORDER BY name
            """, (cat_id,))
            
            sub_category_ids[cat_name] = {row[1]: row[0] for row in cursor.fetchall()}

        connection.close()
        return category_ids, sub_category_ids

    def _get_categories_hierarchy(self) -> dict:
        """
        Récupère l'arborescence des noms de catégories.

		Returns:
		- dict : dictionnaire { 'Categorie': [liste des sous-catégories] }
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        cursor.execute("SELECT id, name FROM categories")
        categories = cursor.fetchall()

        result = {}
        for cat_id, cat_name in categories:
            cursor.execute("SELECT name FROM sub_categories WHERE category_id = ? ORDER BY name", (cat_id,))
            result[cat_name] = [row[0] for row in cursor.fetchall()]

        connection.close()
        return result

    def _get_unprocessed_raw_operations(self) -> list:
        """
        Récupère les transactions brutes non traitées (processed = 0).

		Returns:
		- list : liste des tuples contenant (id, date_operation, libelle_court, type_operation, libelle_operation, montant)
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, operation_date, short_label, operation_type, full_label, amount
            FROM raw_data WHERE processed = 0
            ORDER BY operation_date ASC, id ASC
        """)

        rows = cursor.fetchall()
        connection.close()
        return rows

    def _get_categorized_operations_df(self) -> pd.DataFrame:
        """
        Récupère les opérations catégorisées en DataFrame.

        Returns:
            - pd.DataFrame : Données jointes des transactions et leurs catégories.
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT co.id, c.name AS category, sc.name AS sub_category,
                   co.operation_date, co.short_label, co.operation_type,
                   co.full_label, co.amount
            FROM categorized_operations co
            LEFT JOIN categories c ON co.category_id = c.id
            LEFT JOIN sub_categories sc ON co.sub_category_id = sc.id
            ORDER BY co.operation_date ASC, co.id ASC
        """)

        rows = cursor.fetchall()
        connection.close()

        df = pd.DataFrame(rows, columns=[
            'id', 'category', 'sub_category', 'operation_date', 
            'short_label', 'operation_type', 'full_label', 'amount'
        ])
        df["operation_date"] = pd.to_datetime(df["operation_date"])
        return df

    def _get_categorized_operations_by_year(self) -> dict:
        """
        Regroupe les opérations par année.

		Returns:
		- dict : { year (int) : DataFrame des opérations de l'année correspondante }
        """
        df = self._get_categorized_operations_df()
        df["year"] = df["operation_date"].dt.year
        
        years_dict = {}
        for year, year_df in df.groupby("year"):
            years_dict[int(year)] = year_df.reset_index(drop=True)
        return years_dict

    def _save_categorized_transaction(self, raw_row: tuple, category_id: int, sub_category_id: int):
        """
		Enregistre une opération catégorisée dans la base de données
		et marque la ligne correspondante dans `donnees_brutes` comme traitée.

		Args:
		- raw_row : tuple contenant les données brutes de l'opération
		- category_id : int, identifiant de la catégorie
		- sub_category_id : int, identifiant de la sous-catégorie
        """
        raw_id = raw_row[0]
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO categorized_operations
            (category_id, sub_category_id, raw_data_id, operation_date, 
             short_label, operation_type, full_label, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (category_id, sub_category_id, raw_row[0], raw_row[1], 
              raw_row[2], raw_row[3], raw_row[4], raw_row[5]))

        cursor.execute("UPDATE raw_data SET processed = 1 WHERE id = ?", (raw_id,))
        connection.commit()
        connection.close()


    # --- [ Méthodes privées pour la création, l'insertion par défaut et la vérification d'intégrité ] ---
    def __create_database_schema(self):
        """
        Crée le schéma initial de la base de données SQLite avec une nomenclature anglaise.

        Génère les tables nécessaires pour stocker les catégories, les 
        sous-catégories, les transactions brutes importées (raw_data) et les 
        opérations finales catégorisées (categorized_operations).
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name TEXT UNIQUE,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_date TEXT NOT NULL,
                short_label TEXT,
                operation_type TEXT,
                full_label TEXT NOT NULL,
                amount REAL NOT NULL,
                processed INTEGER DEFAULT 0
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorized_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                sub_category_id INTEGER,
                raw_data_id INTEGER,
                operation_date TEXT,
                short_label TEXT,
                operation_type TEXT,
                full_label TEXT,
                amount REAL,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (sub_category_id) REFERENCES sub_categories(id),
                FOREIGN KEY (raw_data_id) REFERENCES raw_data(id)
            );
        """)

        connection.commit()
        connection.close()

    def __insert_default_categories(self):
        """
		Ajoute les catégories et sous-catégories définies en configuration
		dans la base de données si elles n'existent pas déjà.
		"""
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        for category, sub_list in self._BUTTON_LABELS.items():
            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
            cursor.execute("SELECT id FROM categories WHERE name = ?", (category,))
            category_id = cursor.fetchone()[0]

            for sub_category in sub_list:
                cursor.execute(
                    "INSERT OR IGNORE INTO sub_categories (name, category_id) VALUES (?, ?)",
                    (sub_category, category_id)
                )

        connection.commit()
        connection.close()

    def __verify_category_consistency(self):
        """
        Vérifie que toutes les catégories et sous-catégories présentes dans la BDD
        existent dans self._BUTTON_LABELS .

        Si une catégorie ou sous-catégorie n'existe plus :
            - supprimer les lignes dans operations_categorisees
            - remettre traite = 0 dans donnees_brutes
            - supprimer la catégorie ou sous-catégorie dans la BDD
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        allowed_categories = set(self._BUTTON_LABELS.keys())
        allowed_sub_categories = set()
        for _, sub_list in self._BUTTON_LABELS.items():
            allowed_sub_categories.update(sub_list)

        cursor.execute("SELECT id, name FROM categories")
        db_categories = cursor.fetchall()

        cursor.execute("SELECT id, name FROM sub_categories")
        db_sub_categories = cursor.fetchall()

        def cleanup_field(field_name: str, field_id: int):
            cursor.execute(f"SELECT raw_data_id FROM categorized_operations WHERE {field_name} = ?", (field_id,))
            raw_ids = cursor.fetchall()
            for (r_id,) in raw_ids:
                cursor.execute("UPDATE raw_data SET processed = 0 WHERE id = ?", (r_id,))
            cursor.execute(f"DELETE FROM categorized_operations WHERE {field_name} = ?", (field_id,))

        for cat_id, cat_name in db_categories:
            if cat_name not in allowed_categories:
                cleanup_field("category_id", cat_id)
                cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))

        for sub_id, sub_name in db_sub_categories:
            if sub_name not in allowed_sub_categories:
                cleanup_field("sub_category_id", sub_id)
                cursor.execute("DELETE FROM sub_categories WHERE id = ?", (sub_id,))

        connection.commit()
        connection.close()
