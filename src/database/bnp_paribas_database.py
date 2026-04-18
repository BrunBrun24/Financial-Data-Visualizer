import os
import shutil
import sqlite3

import pandas as pd

from .base_database import BaseDatabase
from .database import Database


class BnpParibasDatabase(BaseDatabase, Database):
    """Gère l'accès et la manipulation des données financières d'un compte bancaire."""

    def __init__(self, db_path: str):
        """Initialise la connexion et prépare la structure de la base de données."""

        super().__init__(db_path)
        self._categories_labels = {
            "Épargne": ["Livret A"],
            "Investissement": ["CTO", "PEA", "Cryptomonnaies"],
            "Revenus": [
                "Aides - Allocations",
                "Salaires",
                "Revenus d'activité",
                "Revenus de placement",
                "Pensions",
                "Intérêts",
                "Loyers",
                "Remboursement",
                "Chèques reçus",
                "Déblocage emprunt",
                "Virements reçus",
                "Virements internes",
                "Cashback",
                "Remboursement amis",
            ],
            "Abonnement": [
                "FAI",
                "Streaming",
                "Logiciels",
                "Musiques",
                "Assurance habitation",
                "Assurance véhicule",
                "Assurance Bancaire",
                "Abonnements partagés",
            ],
            "Impôts": [
                "Impôts sur taxes",
                "Impôt sur le revenu",
                "Impôt sur la fortune",
                "Taxe foncière",
                "Taxe d'habitation",
                "Contributions sociales (CSG / CRDS)",
                "Bourse (flat tax)",
            ],
            "Banque": [
                "Remboursement emprunt",
                "Frais bancaires",
                "Frais de carte",
                "Retrait d'espèces",
            ],
            "Logement": [
                "Électricité - gaz",
                "Eau",
                "Chauffage",
                "Loyer",
                "Prêt immobilier",
                "Bricolage - Jardinage",
            ],
            "Alimentation extérieure": [
                "Restauration",
                "Restaurants",
                "Fast-food",
                "Stand - Food truck",
                "Boulangerie - Snacks",
                "Vente à emporter",
            ],
            "Loisirs": [
                "Vacances - Voyages",
                "Activités",
                "Événements sportifs",
                "Spectacles - Culture",
            ],
            "Sorties": [
                "Bars - Cafés",
                "Boîte de nuit",
                "Sorties amis - Afters",
                "Pari perdu",
            ],
            "Santé": [
                "Médecin",
                "Pharmacie",
                "Dentiste",
                "Mutuelle",
                "Opticien",
                "Hôpital",
                "Kinésithérapie",
                "Dermatologue",
                "Analyse médicale",
            ],
            "Transports et véhicules": [
                "Crédit auto",
                "Carburant",
                "Entretien véhicule",
                "Transports en commun",
                "Avion",
                "Train",
                "Taxis, VTC",
                "Location de véhicule",
                "Péage",
                "Stationnement",
            ],
            "Vie quotidienne": [
                "Supermarché",
                "Coiffeur, soins",
                "Frais postaux",
                "Aide à domicile",
                "Échange d'argent",
            ],
            "Achat": ["Shopping", "Jeux vidéos", "High tech", "Cadeaux"],
            "Enfants": [
                "Pension alimentaire",
                "Crèche, baby-sitter",
                "Scolarité - Études",
                "Argent de poche",
                "Activités enfants",
            ],
            "Amendes": ["Amende de stationnement"],
            "Couple": [
                "Aides financières",
                "Cadeaux - Petits plaisirs",
                "Restaurants - Nourritures",
                "Voyages - week-ends",
                "Loisirs - activités",
            ],
            "Parents": ["Aides"],
            "Argent": ["Argent prêter"],
        }

        self._create_database()
        self._verify_category_consistency()

    def add_bank_account(self, bank_account_name: str) -> None:
        """Ajout d'un nouveau compte bancaire."""

        with self._get_db() as conn:
            conn.cursor().execute("INSERT INTO bank_account (name) VALUES (?)", (bank_account_name,))

    def add_operations(self, operations_df: pd.DataFrame, categorization: bool) -> None:
        """Ajout de plusieurs opérations avec gestion des doublons."""

        if operations_df.empty:
            return

        # On renomme pour correspondre aux noms de la base de données
        column_mapping = {
            "operation_date": "operation_date",
            "libelle_court": "short_label",
            "type_operation": "operation_type",
            "libelle_operation": "full_label",
            "montant": "amount",
            "bank_account_id": "bank_account_id",
        }

        operations_df = operations_df.rename(columns=column_mapping)
        operations_df["operation_date"] = pd.to_datetime(operations_df["operation_date"]).dt.strftime("%Y-%m-%d")

        key_cols = [
            "operation_date",
            "short_label",
            "operation_type",
            "full_label",
            "amount",
            "bank_account_id",
        ]

        # Vérification de sécurité avant le slice
        missing = [c for c in key_cols if c not in operations_df.columns]
        if missing:
            raise KeyError(f"Colonnes manquantes après renommage : {missing}")

        df_to_process = operations_df[key_cols].copy()
        current_account_id = int(operations_df["bank_account_id"].iloc[0])
        query = f"""
            SELECT {", ".join(key_cols)} 
            FROM raw_data 
            WHERE bank_account_id = ?
        """

        with self._get_db() as conn:
            db_existing = pd.read_sql_query(query, conn, params=(current_account_id,))

        # On fusionne les deux dataframes sur toutes les colonnes communes
        df_final = df_to_process.merge(db_existing, how="left", indicator=True)

        # On ne garde que les lignes qui n'étaient présentes que dans les opérations à ajouter
        df_final = df_final[df_final["_merge"] == "left_only"].drop(columns="_merge")

        df_final["bank_account_id"] = operations_df["bank_account_id"][0]
        
        df_final["processed"] = 0 if categorization else 1

        with self._get_db() as conn:
            df_final.to_sql(name="raw_data", con=conn, if_exists="append", index=False)

        # Si l'opération n'a pas été catégorisée on arrête
        if not categorization:
            return

        # Récupération des IDs créés et des IDs de catégories
        with self._get_db() as conn:
            # Récupération des nouveaux IDs de raw_data
            db_raw_ids = pd.read_sql_query(
                f"SELECT id as raw_data_id, {', '.join(key_cols)} FROM raw_data WHERE bank_account_id = ?",
                conn,
                params=(current_account_id,),
            )

            # Récupération de la hiérarchie des catégories
            query_cat = """
                SELECT c.id as category_id, sc.id as sub_category_id, c.name as cat_name, sc.name as sub_name
                FROM sub_categories sc
                JOIN categories c ON sc.category_id = c.id
                WHERE c.bank_account_id = ?
            """
            db_cat_map = pd.read_sql_query(query_cat, conn, params=(current_account_id,))

        # Liaison et insertion dans categorized_operations
        # On réintègre d'abord les noms de catégories du DF original
        df_link = df_final.merge(operations_df[key_cols + ["category", "sub_category"]], on=key_cols, how="left")

        # On lie avec les IDs de raw_data
        df_link = df_link.merge(db_raw_ids, on=key_cols)

        # On transforme les noms de catégories en IDs techniques
        df_categorized = df_link.merge(
            db_cat_map, left_on=["category", "sub_category"], right_on=["cat_name", "sub_name"]
        )

        # Sélection finale des colonnes pour la table de liaison
        df_insert_cat = df_categorized[["bank_account_id", "raw_data_id", "category_id", "sub_category_id"]]

        with self._get_db() as conn:
            df_insert_cat.to_sql(name="categorized_operations", con=conn, if_exists="append", index=False)

    def delete_bank_account(self, account_id: str) -> None:
        """Ajout d'un nouveau compte bancaire."""

        with self._get_db() as conn:
            conn.cursor().execute("DELETE FROM bank_account WHERE id = ?", (account_id,))

    def delete_operation(self, bank_account_id: int, categorized_operations_id: int) -> None:
        """Supprime une opération d'un compte bancaire"""

        with self._get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM categorized_operations WHERE bank_account_id = ? AND id = ?",
                (
                    bank_account_id,
                    categorized_operations_id,
                ),
            )
            raw_data_id = cursor.fetchone()[0]

            cursor.execute(
                "DELETE FROM categorized_operations WHERE id = ?",
                (categorized_operations_id,),
            )
            # En supprimant l'opération dans la table raw_data cela la supprimera aussi dans categorized_operations
            cursor.execute(
                "DELETE FROM raw_data WHERE bank_account_id = ? AND id = ?",
                (
                    bank_account_id,
                    raw_data_id,
                ),
            )

    def _delete_operation(self, raw_data_id: int) -> None:
        """
        Supprime la catégorisation d'une opération brute.

        La suppression dans 'categorized_operations' déclenche automatiquement
        le trigger SQL qui remet le champ 'processed' à 0 dans 'raw_data'.
        """

        with self._get_db() as conn:
            conn.cursor().execute(
                """
                DELETE FROM categorized_operations 
                WHERE raw_data_id = ?
                """,
                (raw_data_id,),
            )

    def update_bank_account_name(self, bank_account_id: int, new_name: str) -> None:
        """Met à jour le nom d'un compte bancaire"""

        with self._get_db() as conn:
            conn.cursor().execute(
                "UPDATE bank_account SET name = ? WHERE id = ?",
                (new_name, bank_account_id),
            )

    def update_operation(self, bank_account_id: int, updated_data: dict) -> bool:
        """Mets à jour une opération d'un compte bancaire"""

        with self._get_db() as conn:
            cursor = conn.cursor()

            # Récupération de l'id
            cursor.execute(
                """
                SELECT raw_data_id FROM categorized_operations 
                WHERE bank_account_id = ? AND id = ?
                """,
                (bank_account_id, updated_data["id"]),
            )

            res = cursor.fetchone()
            if not res:
                return False

            raw_data_id = res[0]

            # Mise à jour de la table raw_data
            cursor.execute(
                """
                UPDATE raw_data 
                SET operation_date = ?, full_label = ?, amount = ?
                WHERE id = ?
                """,
                (
                    updated_data["operation_date"],
                    updated_data["libelle_operation"],
                    updated_data["amount"],
                    raw_data_id,
                ),
            )

            # Mise à jour de la table categorized_operations
            cursor.execute(
                """
                UPDATE categorized_operations
                SET 
                    category_id = (SELECT id FROM categories WHERE name = ? AND bank_account_id = ?),
                    sub_category_id = (SELECT id FROM sub_categories WHERE name = ? 
                                       AND category_id = (SELECT id FROM categories WHERE name = ? AND bank_account_id = ?))
                WHERE id = ?
                """,
                (
                    updated_data["category"],
                    bank_account_id,
                    updated_data["sub_category"],
                    updated_data["category"],
                    bank_account_id,
                    updated_data["id"],
                ),
            )

            return True

    def _update_operation(
        self,
        bank_account_id: int,
        row: list,
        category_name: str,
        sub_category_name: str,
    ) -> None:
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

        with self._get_db() as conn:
            cursor = conn.cursor()

            # Récupération ou création des identifiants techniques (IDs)
            category_id = self.__get_or_create_category_id(bank_account_id, category_name)
            sub_category_id = self.__get_or_create_sub_category_id(category_id, sub_category_name)

            cursor.execute(
                """
                INSERT INTO categorized_operations (bank_account_id, raw_data_id, category_id, sub_category_id)
                VALUES (?, ?, ?, ?)
                """,
                (str(bank_account_id), row[0], category_id, sub_category_id),
            )

    def get_operations_by_account(self, bank_account_id: int) -> pd.DataFrame:
        """Retourne toutes les transactions liées à compte bancaire"""

        query = """
            SELECT 
                r.operation_date AS operation_date,
                r.full_label AS libelle_operation,
                c.name AS category,
                s.name AS sub_category,
                r.amount AS amount,
                cat.id AS id
            FROM categorized_operations cat
            JOIN raw_data r ON cat.raw_data_id = r.id
            JOIN categories c ON cat.category_id = c.id
            JOIN sub_categories s ON cat.sub_category_id = s.id
            WHERE cat.bank_account_id = ?
            ORDER BY r.operation_date DESC
        """

        with self._get_db() as conn:
            return pd.read_sql_query(query, conn, params=(bank_account_id,))

    def get_account_statistics(self, bank_account_id: int) -> dict:
        """
        Calcule les statistiques d'utilisation d'un compte bancaire.

        Returns:
            dict: Contient total_rows, processed_rows, remaining_rows, category_count.
        """

        stats = {"total": 0, "processed": 0, "remaining": 0, "categories": 0}

        with self._get_db() as conn:
            cursor = conn.cursor()

            # Calcule le nombre total d'opérations et ceux qui sont déjà triés
            cursor.execute(
                """
                SELECT COUNT(*), SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END)
                FROM raw_data WHERE bank_account_id = ?
                """,
                (bank_account_id,),
            )
            res = cursor.fetchone()
            if res:
                stats["total"] = res[0] or 0
                stats["processed"] = res[1] or 0
                stats["remaining"] = stats["total"] - stats["processed"]

            # Nombre de catégories créées
            cursor.execute(
                "SELECT COUNT(*) FROM categories WHERE bank_account_id = ?",
                (bank_account_id,),
            )
            stats["categories"] = cursor.fetchone()[0] or 0

        return stats

    def _get_categories(self, bank_account_id: int) -> dict:
        """
        Récupère l'arborescence complète des catégories pour un compte.

        Returns: dict { 'Catégorie': ['Sous-cat 1', 'Sous-cat 2'] }
        """

        query = """
            SELECT c.name, sc.name
            FROM categories c
            LEFT JOIN sub_categories sc ON c.id = sc.category_id
            WHERE c.bank_account_id = ?
            ORDER BY c.name, sc.name
        """

        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (bank_account_id,))
            rows = cursor.fetchall()

            tree = {}
            for cat, sub in rows:
                if cat not in tree:
                    tree[cat] = []
                if sub:
                    tree[cat].append(sub)
            return tree

    def _get_all_operations(self, table_name: str) -> pd.DataFrame:
        """Récupère toutes les opérations."""

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
            """,
        }

        query = queries.get(table_name, f'SELECT * FROM "{table_name}"')

        try:
            with self._get_db() as conn:
                return pd.read_sql_query(query, conn)
        except Exception as error:
            print(f"Erreur lors de la lecture de la table {table_name}: {error}")
            return pd.DataFrame()

    def _get_unprocessed_raw_operations(self) -> list:
        """Récupère les transactions brutes non traitées (processed = 0)"""

        with self._get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, operation_date, short_label, operation_type, full_label, amount
                FROM raw_data WHERE processed = 0
                ORDER BY operation_date ASC, id ASC
            """)

            rows = cursor.fetchall()
            return rows

    def _get_categorized_operations_df(self) -> pd.DataFrame:
        """Récupère les opérations catégorisées."""

        with self._get_db() as conn:
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

            df = pd.read_sql_query(query, conn)

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

    def __get_or_create_category_id(self, bank_account_id: int, category_name: str) -> int:
        """Récupère l'ID d'une catégorie ou la crée si elle n'existe pas pour ce compte."""

        with self._get_db() as conn:
            cursor = conn.cursor()

            # Tentative de récupération
            cursor.execute(
                "SELECT id FROM categories WHERE bank_account_id = ? AND name = ?;",
                (bank_account_id, category_name),
            )
            result = cursor.fetchone()

            if result:
                return result[0]

            # Création si inexistante
            cursor.execute(
                "INSERT INTO categories (bank_account_id, name) VALUES (?, ?);",
                (bank_account_id, category_name),
            )
            return cursor.lastrowid

    def __get_or_create_sub_category_id(self, category_id: int, sub_category_name: str) -> int:
        """Récupère l'ID d'une sous-catégorie ou la crée pour une catégorie parente donnée."""

        with self._get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM sub_categories 
                WHERE category_id = ? AND name = ?
                """,
                (category_id, sub_category_name),
            )
            result = cursor.fetchone()

            if result:
                sub_category_id = result[0]
            else:
                # Création liée à la catégorie parente
                cursor.execute(
                    """
                    INSERT INTO sub_categories (category_id, name) 
                    VALUES (?, ?)
                    """,
                    (category_id, sub_category_name),
                )
                sub_category_id = cursor.lastrowid

            return sub_category_id

    def _create_database(self) -> None:
        """Crée le schéma SQLite optimisé avec index et triggers automatiques"""

        with self._get_db() as conn:
            cursor = conn.cursor()

            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS bank_account (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_account_id INTEGER NOT NULL,
                    name TEXT NOT NULL,

                    FOREIGN KEY (bank_account_id) REFERENCES bank_account(id) ON DELETE CASCADE,
                    UNIQUE(bank_account_id, name)
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
                    bank_account_id INTEGER NOT NULL,
                    operation_date DATE NOT NULL,
                    short_label TEXT,
                    operation_type TEXT,
                    full_label TEXT NOT NULL,
                    amount REAL NOT NULL,
                    processed INTEGER DEFAULT 0,
                    
                    FOREIGN KEY (bank_account_id) REFERENCES bank_account(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS categorized_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_account_id INTEGER NOT NULL,
                    raw_data_id INTEGER UNIQUE NOT NULL,
                    category_id INTEGER NOT NULL,
                    sub_category_id INTEGER NOT NULL,
                    
                    FOREIGN KEY (bank_account_id) REFERENCES bank_account(id) ON DELETE CASCADE,
                    FOREIGN KEY (raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (sub_category_id) REFERENCES sub_categories(id)
                );
                                    
                CREATE INDEX IF NOT EXISTS idx_categorized_cat ON categorized_operations(category_id);
                CREATE INDEX IF NOT EXISTS idx_categorized_sub ON categorized_operations(sub_category_id);
                CREATE INDEX IF NOT EXISTS idx_raw_processed ON raw_data(processed);
                                    
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

    def _verify_category_consistency(self) -> None:
        """
        Vérifie la conformité des catégories en BDD avec le dictionnaire de référence.

        Si une catégorie/sous-catégorie n'est plus dans le dictionnaire, elle est
        supprimée. La cascade et les triggers SQL s'occupent de remettre les
        transactions liées en état "non traité" (processed = 0).
        """

        with self._get_db() as conn:
            cursor = conn.cursor()

            # Nettoyage des Catégories Parentes
            allowed_categories = set(self._categories_labels.keys())
            cursor.execute("SELECT id, name FROM categories")
            db_categories = cursor.fetchall()

            for category_id, category_name in db_categories:
                if category_name not in allowed_categories:
                    # On supprime juste la catégorie.
                    # Le CASCADE supprime la liaison, le TRIGGER libère la donnée brute.
                    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))

            # Nettoyage des Sous-Catégories (Cohérence Parent-Enfant)
            cursor.execute("""
                SELECT sc.id, sc.name, c.name 
                FROM sub_categories sc
                JOIN categories c ON sc.category_id = c.id
            """)
            db_sub_categories = cursor.fetchall()

            for sub_id, sub_name, parent_name in db_sub_categories:
                is_valid = parent_name in self._categories_labels and sub_name in self._categories_labels[parent_name]

                if not is_valid:
                    # Même logique : la suppression déclenche la libération automatique
                    cursor.execute("DELETE FROM sub_categories WHERE id = ?", (sub_id,))

    @staticmethod
    def merge_bank_databases(source_db_path: str, target_db_path: str, output_path: str) -> None:
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

            with sqlite3.connect(output_path) as conn:
                cursor = conn.cursor()

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
                cursor.execute(
                    "SELECT id, operation_date, short_label, operation_type, full_label, amount, processed FROM db_to_merge.raw_data"
                )
                rows_to_merge = cursor.fetchall()

                for row in rows_to_merge:
                    old_id = row[0]
                    cursor.execute(
                        """
                        INSERT INTO raw_data (operation_date, short_label, operation_type, full_label, amount, processed)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        row[1:],
                    )
                    # On mémorise le lien (old -> new)
                    cursor.execute(
                        "INSERT INTO id_mapping VALUES (?, ?)",
                        (old_id, cursor.lastrowid),
                    )

                # 4. Fusion des opérations catégorisées en utilisant le mapping
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

                cursor.execute("DETACH DATABASE db_to_merge")

        except Exception as error:
            raise RuntimeError(f"Échec du processus de fusion : {str(error)}")
