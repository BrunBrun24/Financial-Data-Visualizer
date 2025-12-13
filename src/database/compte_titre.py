import sqlite3

import pandas as pd

from .bdd import Bdd


class CompteTireBdd(Bdd):
    """
    Gère l'accès et la manipulation des données financières d'un compte bancaire.

    Cette classe hérite de `Bdd` et fournit des fonctionnalités pour :
    - Créer et maintenir la structure de la base de données (catégories, sous-catégories, opérations brutes et catégorisées)
    - Ajouter et récupérer des opérations financières
    - Vérifier la cohérence des catégories et sous-catégories par rapport à la configuration définie
    - Grouper et organiser les opérations par année

    Paramètres :
    - db_path (str) : chemin vers la base de données à utiliser.

    Attributs :
    - _BUTTON_LABELS : dictionnaire définissant les catégories et leurs sous-catégories.
    """

    _BUTTON_LABELS  = {
        'Épargne': [
            "Livret A"
        ],
        'Investissement': [
            "CTO", 
            "Autres"
        ],
        'Revenus': [
            "Aides et allocations", 
            "Salaires et revenus d'activité", 
            "Revenus de placement", 
            "Pensions", 
            "Intérêts", 
            "Loyers", 
            "Dividendes", 
            "Remboursement", 
            "Chèques reçus", 
            "Déblocage emprunt", 
            "Virements reçus", 
            "Virements internes", 
            "Cashback", 
            "Autres"
        ],
        'Abonnement': [
            "Téléphone", 
            "Internet", 
            "Streaming", 
            "Logiciels",
            "Musiques"
        ],
        'Impôts': [
            "Impôts sur taxes", 
            "Impôt sur le revenu", 
            "Impôt sur la fortune", 
            "Taxe foncière", 
            "Taxe d'habitation", 
            "Contributions sociales (CSG / CRDS)", 
            "Bourse (flat tax)"
        ],
        'Banque': [
            "Remboursement emprunt", 
            "Frais bancaires", 
            "Prélèvement carte débit différé", 
            "Retrait d'espèces", 
            "Autres"
        ],
        "Logement": [
            "Électricité, gaz", 
            "Eau", 
            "Chauffage", 
            "Loyer", 
            "Prêt immobilier", 
            "Bricolage et jardinage", 
            "Assurance habitation", 
            "Mobilier, électroménager, déco", 
            "Autres"
        ],
        'Loisirs et sorties': [
            "Voyages, vacances", 
            "Restaurants - Fast food",
            "Bars", 
            "Boites de nuit", 
            "Divertissements, sorties culturelles", 
            "Sports", 
            "Sorties", 
            "Pari perdu", 
            "Concerts",
            "Spectacles",  
            "Autres"
        ],
        'Santé': [
            "Médecin", 
            "Pharmacie", 
            "Dentiste", 
            "Mutuelle", 
            "Opticien", 
            "Hôpital"
        ],
        'Transports et véhicules': [
            "Assurance véhicule", 
            "Crédit auto", 
            "Carburant", 
            "Entretien véhicule", 
            "Transports en commun", 
            "Avion", 
            "Train",
            "Taxis, VTC", 
            "Location de véhicule", 
            "Péage", 
            "Stationnement"
        ],
        'Vie quotidienne': [
            "Alimentation - Supermarché", 
            "Frais animaux", 
            "Coiffeur, soins", 
            "Habillement", 
            "Achat, shopping", 
            "Jeux vidéo", 
            "Frais postaux", 
            "Achat multimédias - High tech", 
            "Aide à domicile", 
            "Cadeaux", 
            "Échange d'argent", 
            "Autres"
        ],
        'Enfants': [
            "Pension alimentaire", 
            "Crèche, baby-sitter", 
            "Scolarité, études", 
            "Argent de poche", 
            "Activités enfants"
        ],
        'Amendes': [
            "Amende de stationnement"
        ],
        'Couple': [
            'Aides financières',
            'Cadeaux - Petits plaisirs',
            'Restaurants - Nourritures',
            'Voyages & week-ends',
            'Loisirs & activités',
            'Abonnements partagés'
        ],
        'Parents': [
            'Aides'
        ],
    }

    def __init__(self, db_path: str):
        super().__init__(db_path)
        
        self.__creer_base_avec_tables()
        self.__verifier_categories_coherentes()
        self.__ajouter_categories()


    def __creer_base_avec_tables(self):
        """
        Crée l'ensemble des tables nécessaires au fonctionnement de la base de données
        si elles n'existent pas déjà.
        """
        connexion = sqlite3.connect(self._db_path)
        curseur = connexion.cursor()

        # Table des catégories
        curseur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE
            );
        """)

        # Table des sous-catégories
        curseur.execute("""
            CREATE TABLE IF NOT EXISTS sous_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie_id INTEGER,
                nom TEXT UNIQUE,
                FOREIGN KEY (categorie_id) REFERENCES categories(id)
            );
        """)

        # Table des données brutes
        curseur.execute("""
            CREATE TABLE IF NOT EXISTS donnees_brutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_operation TEXT,
                libelle_court TEXT,
                type_operation TEXT,
                libelle_operation TEXT,
                montant REAL,
                traite INTEGER DEFAULT 0
            );
        """)

        # Table des opérations
        curseur.execute("""
            CREATE TABLE IF NOT EXISTS operations_categorisees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie_id INTEGER,
                sous_categorie_id INTEGER,
                donnees_brutes_id INTEGER,
                date_operation TEXT,
                libelle_court TEXT,
                type_operation TEXT,
                libelle_operation TEXT,
                montant REAL,
                FOREIGN KEY (categorie_id) REFERENCES categories(id),
                FOREIGN KEY (sous_categorie_id) REFERENCES sous_categories(id),
                FOREIGN KEY (donnees_brutes_id) REFERENCES donnees_brutes(id)
            );
        """)

        connexion.commit()
        connexion.close()

    def __ajouter_categories(self):
        """
		Ajoute les catégories et sous-catégories définies en configuration
		dans la base de données si elles n'existent pas déjà.
		"""
        connexion = sqlite3.connect(self._db_path)
        curseur = connexion.cursor()

        for categorie, sous_list in self._BUTTON_LABELS.items():
            # Ajout catégorie
            curseur.execute(
                "INSERT OR IGNORE INTO categories (nom) VALUES (?)",
                (categorie,)
            )

            # Récupérer son id
            curseur.execute(
                "SELECT id FROM categories WHERE nom = ?",
                (categorie,)
            )
            categorie_id = curseur.fetchone()[0]

            # Ajout sous-catégories
            for sous in sous_list:
                curseur.execute(
                    "INSERT OR IGNORE INTO sous_categories (nom, categorie_id) VALUES (?, ?)",
                    (sous, categorie_id)
                )

        connexion.commit()
        connexion.close()

    def __verifier_categories_coherentes(self):
        """
        Vérifie que toutes les catégories et sous-catégories présentes dans la BDD
        existent dans self._BUTTON_LABELS .

        Si une catégorie ou sous-catégorie n'existe plus :
            - supprimer les lignes dans operations_categorisees
            - remettre traite = 0 dans donnees_brutes
            - supprimer la catégorie ou sous-catégorie dans la BDD
        """
        connexion = sqlite3.connect(self._db_path)
        cursor = connexion.cursor()

        # Construire les sets autorisés à partir de _BUTTON_LABELS 
        categories_autorisees = set(self._BUTTON_LABELS .keys())

        sous_autorisees = set()
        for _, sous_list in self._BUTTON_LABELS .items():
            sous_autorisees.update(sous_list)

        # Récupérer les catégories en base
        cursor.execute("SELECT id, nom FROM categories")
        categories_en_base = cursor.fetchall()

        # Récupérer les sous-catégories en base
        cursor.execute("SELECT id, nom FROM sous_categories")
        sous_en_base = cursor.fetchall()

        # Fonction utilitaire : suppression + remise traite=0
        def nettoyer_operations_par_champ(champ, valeur_id):
            """
            champ : 'categorie_id' ou 'sous_categorie_id'
            valeur_id : id à nettoyer
            """

            # Récupérer toutes les lignes operations_categorisees
            cursor.execute(
                f"SELECT donnees_brutes_id FROM operations_categorisees WHERE {champ} = ?",
                (valeur_id,)
            )
            donnees_ids = cursor.fetchall()

            # Remettre traite = 0 dans donnees_brutes
            for (db_id,) in donnees_ids:
                cursor.execute(
                    "UPDATE donnees_brutes SET traite = 0 WHERE id = ?",
                    (db_id,)
                )

            # Supprimer les opérations catégorisées correspondantes
            cursor.execute(
                f"DELETE FROM operations_categorisees WHERE {champ} = ?",
                (valeur_id,)
            )

        # Vérification catégories
        for cat_id, cat_nom in categories_en_base:
            if cat_nom not in categories_autorisees:

                print(f"[⚠] Catégorie supprimée : {cat_nom}")

                # Nettoyage des opérations + remise traite=0
                nettoyer_operations_par_champ("categorie_id", cat_id)

                # Suppression catégorie
                cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))

        # Vérification sous-catégories
        for sous_id, sous_nom in sous_en_base:
            if sous_nom not in sous_autorisees:

                print(f"[⚠] Sous-catégorie supprimée : {sous_nom}")

                # Nettoyage des opérations + remise traite=0
                nettoyer_operations_par_champ("sous_categorie_id", sous_id)

                # Suppression sous-catégorie
                cursor.execute("DELETE FROM sous_categories WHERE id = ?", (sous_id,))

        connexion.commit()
        connexion.close()


    def _get_category_ids(self) -> tuple:
        """
		Charge toutes les catégories et sous-catégories depuis la base de données.

		Returns:
		- category_ids : dictionnaire { 'Categorie': categorie_id }
		- sous_categories_ids : dictionnaire { 'Categorie': { 'Sous-categorie': sous_categorie_id } }
        """
        connexion = sqlite3.connect(self._db_path)
        cursor = connexion.cursor()

        # Charger les catégories
        cursor.execute("SELECT id, nom FROM categories ORDER BY nom")
        category_rows = cursor.fetchall()

        category_ids = {}
        sous_categories_ids = {}

        for categorie_id, categorie_nom in category_rows:
            category_ids[categorie_nom] = categorie_id

            # Charger les sous-catégories associées
            cursor.execute("""
                SELECT id, nom 
                FROM sous_categories
                WHERE categorie_id = ?
                ORDER BY nom
            """, (categorie_id,))
            sous_rows = cursor.fetchall()

            sous_categories_ids[categorie_nom] = {
                sous_nom: sous_id for sous_id, sous_nom in sous_rows
            }

        connexion.close()

        return category_ids, sous_categories_ids

    def _get_category(self) -> dict:
        """
		Récupère toutes les catégories et leurs sous-catégories depuis la base de données.

		Returns:
		- dict : dictionnaire { 'Categorie': [liste des sous-catégories] }
        """
        connexion = sqlite3.connect(self._db_path)
        cursor = connexion.cursor()

        # Récupération des catégories
        cursor.execute("SELECT id, nom FROM categories")
        category = cursor.fetchall()

        result = {}

        # Pour chaque catégorie → récupérer les sous-catégories
        for cat_id, cat_name in category:
            cursor.execute(
                "SELECT nom FROM sous_categories WHERE categorie_id = ? ORDER BY nom",
                (cat_id,)
            )
            sous_cats = [row[0] for row in cursor.fetchall()]

            result[cat_name] = sous_cats

        connexion.close()
        return result

    def _get_operations_brut(self) -> list:
        """
		Récupère toutes les opérations brutes non traitées depuis la base de données.

		Returns:
		- list : liste des tuples contenant (id, date_operation, libelle_court, type_operation, libelle_operation, montant)
        """
        connexion = sqlite3.connect(self._db_path)
        cursor = connexion.cursor()

        cursor.execute("""
            SELECT id, date_operation, libelle_court, type_operation, libelle_operation, montant
            FROM donnees_brutes
            WHERE traite = 0
            ORDER BY date_operation ASC, id ASC
        """)

        row = cursor.fetchall()
        connexion.close()
        return row

    def _get_operations_categorisees(self) -> pd.DataFrame:
        """
		Récupère toutes les opérations catégorisées depuis la base de données
		et les retourne sous forme de DataFrame.

		Returns:
		- pd.DataFrame : colonnes ['id', 'categorie', 'sous_categorie', 'date_operation', 
		                           'libelle_court', 'type_operation', 'libelle_operation', 'montant']
        """
        connexion = sqlite3.connect(self._db_path)
        cursor = connexion.cursor()

        cursor.execute("""
            SELECT oc.id,
                c.nom AS categorie,
                sc.nom AS sous_categorie,
                oc.date_operation,
                oc.libelle_court,
                oc.type_operation,
                oc.libelle_operation,
                oc.montant
            FROM operations_categorisees oc
            LEFT JOIN categories c ON oc.categorie_id = c.id
            LEFT JOIN sous_categories sc ON oc.sous_categorie_id = sc.id
            ORDER BY oc.date_operation ASC, oc.id ASC
        """)

        rows = cursor.fetchall()
        connexion.close()

        # Transformer en DataFrame
        df = pd.DataFrame(
            rows,
            columns=[
                'id', 'categorie', 'sous_categorie',
                'date_operation', 'libelle_court', 'type_operation',
                'libelle_operation', 'montant'
            ]
        )

        df["date_operation"] = pd.to_datetime(df["date_operation"])

        return df

    def _save_categorized_operation(self, raw_row, categorie_id, sous_categorie_id):
        """
		Enregistre une opération catégorisée dans la base de données
		et marque la ligne correspondante dans `donnees_brutes` comme traitée.

		Args:
		- raw_row : tuple contenant les données brutes de l'opération
		- categorie_id : int, identifiant de la catégorie
		- sous_categorie_id : int, identifiant de la sous-catégorie
        """
        raw_id = raw_row[0]

        connexion = sqlite3.connect(self._db_path)
        cursor = connexion.cursor()

        cursor.execute("""
            INSERT INTO operations_categorisees
            (categorie_id, sous_categorie_id, donnees_brutes_id, date_operation, libelle_court, type_operation, libelle_operation, montant)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            categorie_id,
            sous_categorie_id,
            raw_row[0],  # donnees_brutes_id
            raw_row[1],  # date_operation
            raw_row[2],  # libelle_court
            raw_row[3],  # type_operation
            raw_row[4],  # libelle_operation
            raw_row[5]   # montant
        ))

        cursor.execute("UPDATE donnees_brutes SET traite = 1 WHERE id = ?", (raw_id,))

        connexion.commit()
        connexion.close()

    def _get_year_operations_categorisees(self) -> dict:
        """
		Groupes les opérations catégorisées par année.

		Returns:
		- dict : { année (int) : DataFrame des opérations de l'année correspondante }
        """
        df = self._get_operations_categorisees()
        df["annee"] = df["date_operation"].dt.year

        years_dict = {}
        # Groupement par année
        for annee, df_annee in df.groupby("annee"):
            years_dict[annee] = df_annee.reset_index(drop=True)

        return years_dict


    def ajouter_donnees_brutes(self, df: pd.DataFrame):
        """
		Ajoute des lignes dans la table `donnees_brutes` à partir d'un DataFrame,
		en évitant les doublons existants dans la base.

		Args:
		- df : pd.DataFrame contenant les opérations à ajouter (colonnes : date_operation, libelle_court, type_operation, libelle_operation, montant)
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Conversion des Timestamp → SQLite attend des strings
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == "datetime64[ns]":
                df[col] = df[col].dt.strftime("%Y-%m-%d")

        # Nettoyage : enlever les doublons dans le DataFrame lui-même
        df = df.drop_duplicates()

        # Liste des lignes à insérer
        lignes_a_inserer = []

        # Préparer une requête pour la vérification
        check_sql = """
            SELECT traite FROM donnees_brutes 
            WHERE date_operation = ?
            AND libelle_court = ?
            AND type_operation = ?
            AND libelle_operation = ?
            AND montant = ?
        """

        # Vérification pour chaque ligne
        for row in df.itertuples(index=False):
            params = (row[0], row[1], row[2], row[3], row[4])

            cursor.execute(check_sql, params)
            result = cursor.fetchone()

            # Si la ligne existe déjà → on ignore
            if result is not None:
                continue

            # Sinon → on ajouté dans la liste à insérer
            lignes_a_inserer.append(params)

        # ✅ Insertion en masse (plus rapide et plus propre)
        if lignes_a_inserer:
            insert_sql = """
                INSERT INTO donnees_brutes
                (date_operation, libelle_court, type_operation, libelle_operation, montant)
                VALUES (?, ?, ?, ?, ?)
            """

            cursor.executemany(insert_sql, lignes_a_inserer)

        conn.commit()
        conn.close()
