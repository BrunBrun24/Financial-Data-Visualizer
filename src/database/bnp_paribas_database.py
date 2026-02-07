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

    def __init__(self, db_path: str):
        """
        Initialise la connexion et prépare la structure de la base de données.

        Prépare l'environnement de la base de données en s'assurant que le schéma 
        SQL est présent et que l'intégrité des données est respectée par rapport 
        à la configuration actuelle.

        Agrs:
        - db_path (str) : Chemin complet vers le fichier de base de données SQLite.
        """
        super().__init__(db_path)
        self._categories_labels = {
            'Épargne': ["Livret A"],
            'Investissement': ["CTO", "PEA", "Cryptomonnaies"],
            'Revenus': [
                "Aides - Allocations", "Salaires", "Revenus d'activité", 
                "Revenus de placement", "Pensions", "Intérêts", "Loyers", 
                "Remboursement", "Chèques reçus", "Déblocage emprunt", 
                "Virements reçus", "Virements internes", "Cashback",
            ],
            'Abonnement': ["FAI", "Streaming", "Logiciels", "Musiques", "Assurance habitation", 
                        "Assurance véhicule", "Assurance Bancaire", 'Abonnements partagés'],
            'Impôts': [
                "Impôts sur taxes", "Impôt sur le revenu", "Impôt sur la fortune", 
                "Taxe foncière", "Taxe d'habitation", "Contributions sociales (CSG / CRDS)", 
                "Bourse (flat tax)"
            ],
            'Banque': [
                "Remboursement emprunt", "Frais bancaires", "Frais de carte",
                "Retrait d'espèces"
            ],
            "Logement": [
                "Électricité - gaz", "Eau", "Chauffage", "Loyer", "Prêt immobilier", 
                "Bricolage - Jardinage"
            ],
            'Alimentation extérieure': [
                "Restauration", "Restaurants", "Fast-food", "Stand - Food truck",
                "Boulangerie - Snacks", "Vente à emporter"
            ],
            'Loisirs': [
                "Vacances - Voyages", "Activités", "Événements sportifs",
                "Spectacles - Culture"
            ],
            'Sorties': [
                "Bars - Cafés", "Boîte de nuit", "Sorties amis - Afters",
                "Pari perdu"
            ],
            'Santé': ["Médecin", "Pharmacie", "Dentiste", "Mutuelle", "Opticien", "Hôpital", 
                    "Kinésithérapie", "Dermatologue", "Analyse médicale"
            ],
            'Transports et véhicules': [
                "Crédit auto", "Carburant", "Entretien véhicule", 
                "Transports en commun", "Avion", "Train", "Taxis, VTC", 
                "Location de véhicule", "Péage", "Stationnement"
            ],
            'Vie quotidienne': [
                "Supermarché", "Coiffeur, soins", 
                "Frais postaux", "Aide à domicile", "Échange d'argent"
            ],
            "Achat": [
                "Shopping", "Jeux vidéos", "High tech", "Cadeaux"
            ],
            'Enfants': [
                "Pension alimentaire", "Crèche, baby-sitter", "Scolarité - Études", 
                "Argent de poche", "Activités enfants"
            ],
            'Amendes': ["Amende de stationnement"],
            'Couple': [
                'Aides financières', 'Cadeaux - Petits plaisirs', 'Restaurants - Nourritures',
                'Voyages - week-ends', 'Loisirs - activités'
            ],
            'Parents': ['Aides']
        }
        
        self.__create_database_schema()
        self.__verify_category_consistency()


    # --- [ Flux Principal ] ---
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
        
    @staticmethod
    def merge_bank_databases(source_db_path: str, target_db_path: str, output_path: str):
        """
        Fusionne deux bases de données bancaires en préservant l'intégrité référentielle.

        Cette fonction crée une copie de la source, y attache la base cible, 
        puis transfère les données en utilisant une table de correspondance temporaire 
        pour réassocier correctement les nouveaux IDs générés.

        Args:
            - source_db_path (str) : Chemin vers la première base de données (base).
            - target_db_path (str) : Chemin vers la seconde base de données à intégrer.
            - output_path (str) : Chemin du fichier de destination final.
        """
        try:
            # Préparation du dossier de destination
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # Copie de la base source vers la destination
            shutil.copy2(source_db_path, output_path)
            
            connection = sqlite3.connect(output_path)
            connection.execute("PRAGMA foreign_keys = ON;")
            cursor = connection.cursor()
            
            # Attacher la base de données cible
            cursor.execute(f"ATTACH DATABASE '{target_db_path}' AS db_to_merge")

            # 1. Fusion des catégories et sous-catégories (sans doublons)
            cursor.execute("INSERT OR IGNORE INTO categories (name) SELECT name FROM db_to_merge.categories")
            
            cursor.execute("""
                INSERT OR IGNORE INTO sub_categories (category_id, name) 
                SELECT (SELECT id FROM categories WHERE name = c.name), sc.name 
                FROM db_to_merge.sub_categories sc
                JOIN db_to_merge.categories c ON sc.category_id = c.id
            """)

            # 2. Création d'une table de correspondance temporaire pour les IDs de raw_data
            # Cela permet de savoir quel ID de la base cible correspond à quel ID dans la nouvelle base.
            cursor.execute("CREATE TEMP TABLE id_mapping (old_id INTEGER, new_id INTEGER)")

            # 3. Insertion des données brutes et remplissage du mapping
            # On récupère les données de la base cible
            cursor.execute("SELECT id, operation_date, short_label, operation_type, full_label, amount, processed FROM db_to_merge.raw_data")
            rows_to_merge = cursor.fetchall()

            for row in rows_to_merge:
                old_id = row[0]
                # Insertion dans la nouvelle table (l'ID est auto-généré)
                cursor.execute("""
                    INSERT INTO raw_data (operation_date, short_label, operation_type, full_label, amount, processed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, row[1:])
                new_id = cursor.lastrowid
                # On mémorise le lien entre l'ancien et le nouveau
                cursor.execute("INSERT INTO id_mapping VALUES (?, ?)", (old_id, new_id))

            # 4. Fusion des opérations catégorisées en utilisant le mapping
            # On désactive temporairement le TRIGGER pour ne pas interférer avec le flag 'processed' déjà importé
            cursor.execute("""
                INSERT INTO categorized_operations (category_id, sub_category_id, raw_data_id)
                SELECT 
                    (SELECT id FROM categories WHERE name = c_merged.name),
                    (SELECT id FROM sub_categories WHERE name = sc_merged.name 
                        AND category_id = (SELECT id FROM categories WHERE name = c_merged.name)),
                    m.new_id
                FROM db_to_merge.categorized_operations co_merged
                JOIN db_to_merge.categories c_merged ON co_merged.category_id = c_merged.id
                JOIN db_to_merge.sub_categories sc_merged ON co_merged.sub_category_id = sc_merged.id
                JOIN id_mapping m ON co_merged.raw_data_id = m.old_id
            """)

            connection.commit()
            cursor.execute("DETACH DATABASE db_to_merge")
            connection.close()

        except Exception as error:
            if 'connection' in locals():
                connection.rollback()
            raise RuntimeError(f"Échec du processus de fusion : {str(error)}")


    # --- [ Getters ] ---
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
        Récupère les opérations catégorisées en joignant les tables via les pointeurs.

        Returns:
            - pd.DataFrame : Données reconstruites (id_brut, catégorie, sous-catégorie, date, etc.).
        """
        connection = sqlite3.connect(self._db_path)
        
        # On utilise JOIN (ou LEFT JOIN) pour rassembler les données éparpillées
        # La table 'categorized_operations' sert de pivot central.
        query = """
            SELECT 
                r.id, 
                c.name AS category, 
                sc.name AS sub_category,
                r.operation_date, 
                r.short_label, 
                r.operation_type,
                r.full_label, 
                r.amount
            FROM categorized_operations co
            JOIN raw_data r ON co.raw_data_id = r.id
            JOIN categories c ON co.category_id = c.id
            JOIN sub_categories sc ON co.sub_category_id = sc.id
            ORDER BY r.operation_date ASC, r.id ASC
        """

        # Utilisation de pandas pour lire directement le flux SQL
        df = pd.read_sql_query(query, connection)
        connection.close()

        # Conversion de la date en objet datetime
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

    def __get_or_create_category_id(self, category_name: str) -> int:
        """
        Récupère l'identifiant d'une catégorie ou la crée si elle n'existe pas.

        Args:
            - category_name (str) : Le nom de la catégorie.
        
        Returns:
            - int : L'identifiant technique (ID) de la catégorie.
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()
        
        # Recherche de l'ID existant
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = cursor.fetchone()
        
        if result:
            category_id = result[0]
        else:
            # Création si inexistante
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
            category_id = cursor.lastrowid
            
        connection.commit()
        connection.close()
        return category_id

    def __get_or_create_sub_category_id(self, category_id: int, sub_category_name: str) -> int:
        """
        Récupère l'ID d'une sous-catégorie ou la crée pour une catégorie parente donnée.

        Args:
            - category_id (int) : L'ID de la catégorie parente.
            - sub_category_name (str) : Le nom de la sous-catégorie.

        Returns:
            - int : L'identifiant technique (ID) de la sous-catégorie.
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id FROM sub_categories 
            WHERE category_id = ? AND name = ?
        """, (category_id, sub_category_name))
        result = cursor.fetchone()
        
        if result:
            sub_category_id = result[0]
        else:
            # Création liée à la catégorie parente
            cursor.execute("""
                INSERT INTO sub_categories (category_id, name) 
                VALUES (?, ?)
            """, (category_id, sub_category_name))
            sub_category_id = cursor.lastrowid
            
        connection.commit()
        connection.close()
        return sub_category_id


    # --- [ Enregistrement ] ---
    def _save_categorized_transaction(self, row: list, category_name: str, sub_category_name: str):
        """
        Enregistre la liaison entre une opération brute et ses catégories.
        
        Cette méthode convertit les noms de catégories en identifiants techniques 
        (en les créant si nécessaire) avant d'insérer la liaison. 
        Note : Le flag 'processed' dans 'raw_data' est mis à jour par un TRIGGER SQL.

        Args:
            - row (list) : La ligne de l'opération brute (l'ID doit être en index 0).
            - category_name (str) : Le nom de la catégorie parente.
            - sub_category_name (str) : Le nom de la sous-catégorie.
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        # Récupération ou création des identifiants techniques (IDs)
        category_id = self.__get_or_create_category_id(category_name)
        sub_category_id = self.__get_or_create_sub_category_id(category_id, sub_category_name)

        try:
            cursor.execute("""
                INSERT INTO categorized_operations (raw_data_id, category_id, sub_category_id)
                VALUES (?, ?, ?)
            """, (row[0], category_id, sub_category_id))
            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            print(f"Erreur SQL lors de l'insertion : {error}")
        finally:
            connection.close()

    def _delete_categorized_transaction(self, raw_data_id: int):
        """
        Supprime la catégorisation d'une opération brute.
        
        La suppression dans 'categorized_operations' déclenche automatiquement 
        le trigger SQL qui remet le champ 'processed' à 0 dans 'raw_data'.

        Args:
            - raw_data_id (int) : Identifiant technique de l'opération dans la table raw_data.
        """
        connection = sqlite3.connect(self._db_path)
        # Activation des clés étrangères pour garantir l'exécution des triggers
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        try:
            # On supprime la liaison uniquement
            cursor.execute("""
                DELETE FROM categorized_operations 
                WHERE raw_data_id = ?
            """, (raw_data_id,))
            
            connection.commit()
            
        except sqlite3.Error as error:
            # En cas d'échec, on annule les modifications
            connection.rollback()
            raise RuntimeError(f"Erreur lors de la suppression de la catégorisation {raw_data_id} : {error}")
            
        finally:
            connection.close()


    # --- [ Configuration ] ---
    def __create_database_schema(self):
        """
        Crée le schéma SQLite optimisé avec index et triggers automatiques.
        """
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()

        # Activation impérative des clés étrangères
        cursor.execute("PRAGMA foreign_keys = ON;")

        # --- [ Tables, Index et Triggers ] ---
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sub_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                UNIQUE(category_id, name)
            );

            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_date TEXT NOT NULL,
                short_label TEXT,
                operation_type TEXT,
                full_label TEXT NOT NULL,
                amount REAL NOT NULL,
                processed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS categorized_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_data_id INTEGER UNIQUE NOT NULL,
                category_id INTEGER NOT NULL,
                sub_category_id INTEGER NOT NULL,
                FOREIGN KEY (raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (sub_category_id) REFERENCES sub_categories(id)
            );

            -- --- [ Indexation ] ---
                             
            CREATE INDEX IF NOT EXISTS idx_categorized_cat ON categorized_operations(category_id);
            CREATE INDEX IF NOT EXISTS idx_categorized_sub ON categorized_operations(sub_category_id);
            CREATE INDEX IF NOT EXISTS idx_raw_processed ON raw_data(processed);

            -- --- [ Triggers Automatiques ] ---
                             
            -- Activation du flag processed à l'insertion
            CREATE TRIGGER IF NOT EXISTS trg_after_insert_categorization
            AFTER INSERT ON categorized_operations
            BEGIN
                UPDATE raw_data SET processed = 1 WHERE id = new.raw_data_id;
            END;

            -- Désactivation du flag processed à la suppression
            CREATE TRIGGER IF NOT EXISTS trg_after_delete_categorization
            AFTER DELETE ON categorized_operations
            BEGIN
                UPDATE raw_data SET processed = 0 WHERE id = old.raw_data_id;
            END;

            -- Gestion du flag processed en cas de mise à jour du lien
            CREATE TRIGGER IF NOT EXISTS trg_after_update_categorization
            AFTER UPDATE OF raw_data_id ON categorized_operations
            BEGIN
                UPDATE raw_data SET processed = 0 WHERE id = old.raw_data_id;
                UPDATE raw_data SET processed = 1 WHERE id = new.raw_data_id;
            END;
        """)

        connection.commit()
        connection.close()
    
    def __verify_category_consistency(self):
        """
        Vérifie la conformité des catégories en BDD avec le dictionnaire de référence.
        
        Si une catégorie/sous-catégorie n'est plus dans le dictionnaire, elle est
        supprimée. La cascade et les triggers SQL s'occupent de remettre les 
        transactions liées en état "non traité" (processed = 0).
        """
        connection = sqlite3.connect(self._db_path)
        # Indispensable pour que le CASCADE et les Triggers s'activent
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        # 1. Nettoyage des Catégories Parentes
        allowed_categories = set(self._categories_labels.keys())
        cursor.execute("SELECT id, name FROM categories")
        db_categories = cursor.fetchall()

        for category_id, category_name in db_categories:
            if category_name not in allowed_categories:
                # On supprime juste la catégorie. 
                # Le CASCADE supprime la liaison, le TRIGGER libère la donnée brute.
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))

        # 2. Nettoyage des Sous-Catégories (Cohérence Parent-Enfant)
        cursor.execute("""
            SELECT sc.id, sc.name, c.name 
            FROM sub_categories sc
            JOIN categories c ON sc.category_id = c.id
        """)
        db_sub_categories = cursor.fetchall()

        for sub_id, sub_name, parent_name in db_sub_categories:
            is_valid = (parent_name in self._categories_labels and 
                        sub_name in self._categories_labels[parent_name])
            
            if not is_valid:
                # Même logique : la suppression déclenche la libération automatique
                cursor.execute("DELETE FROM sub_categories WHERE id = ?", (sub_id,))

        connection.commit()
        connection.close()