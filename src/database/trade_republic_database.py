import concurrent.futures
import os
import sqlite3
from collections import defaultdict
from datetime import datetime

import pandas as pd
import yfinance as yf

from .base_database import BaseDatabase


class TradeRepublicDatabase(BaseDatabase):
    """
    Cette classe gère la persistance et la structure des données financières 
    spécifiques à Trade Republic dans une base de données SQLite.

    Elle fait le pont entre les données brutes extraites et le stockage organisé, 
    tout en enrichissant les informations via l'API Yahoo Finance (yfinance). 
    Elle gère également le stockage binaire (BLOB) des fichiers PDF pour 
    garantir la traçabilité et l'unicité des imports.
    """
    
    def __init__(self, db_path):
        """
        Initialise la base de données et crée les tables de base si nécessaire.

        Args:
            - db_path (str) : Chemin vers le fichier de base de données SQLite.
        """
        super().__init__(db_path)

        # Initialisation de la structure des tables au démarrage
        self.__create_base_tables()

  
    # --- [ Configuration & Schéma ] ---
    def __create_base_tables(self):
        """
        Initialise la structure de la base de données en utilisant la connexion sécurisée.
        
        Les vérifications de cohérence entre les tickers sont gérées manuellement 
        au niveau de la logique applicative (Python).
        """
        # Utilisation de la méthode privée pour obtenir une connexion configurée
        with self.__get_connection() as connection:
            cursor = connection.cursor()

            # 1. Table Company
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company (
                    ticker TEXT PRIMARY KEY,
                    name TEXT,
                    isin TEXT UNIQUE,
                    sector TEXT,
                    country TEXT,
                    website TEXT,
                    description TEXT,
                    stock_exchange TEXT,
                    currency TEXT NOT NULL
                );
            ''')

            # 2. Table Stock Price
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_price (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    UNIQUE(ticker, date)
                );
            ''')

            # 3. Table Split
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS split (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    ratio REAL NOT NULL,
                    UNIQUE(ticker, date)
                );
            ''')

            # 4. Table Dividend
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dividend (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL, 
                    amount REAL NOT NULL,
                    UNIQUE(ticker, date)
                );
            ''')

            # 5. Table Transaction (user_transaction)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_transaction (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    currency TEXT NOT NULL,
                    operation TEXT NOT NULL CHECK(operation IN ('buy', 'sell', 'dividend', 'interest', 'deposit', 'withdrawal')),
                    date DATE NOT NULL,
                    amount REAL NOT NULL,
                    fees REAL NOT NULL,
                    stock_price REAL,
                    quantity REAL
                );
            ''')

            # Index pour l'unicité des achats et ventes
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_trade 
                ON user_transaction (date, ticker, currency, operation, stock_price) 
                WHERE operation IN ('buy', 'sell');
            ''')

            # Index pour l'unicité des autres opérations
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_other_ops 
                ON user_transaction (date, ticker, currency, operation) 
                WHERE operation NOT IN ('buy', 'sell');
            ''')

            # 6. Table File (Stockage binaire)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file BLOB NOT NULL UNIQUE,
                    table_associee TEXT NOT NULL CHECK(table_associee IN (
                        'buy', 'sell', 'dividend', 'interest', 'deposit', 
                        'withdrawal', 'purchase_costs', 'sales_costs'
                    )),
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER NOT NULL DEFAULT 0
                );
            ''')

            # 7. Table des performances
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL,
                    portfolio_name TEXT NOT NULL,
                    UNIQUE(date, ticker, metric_type, portfolio_name)
                );
            """)

            connection.commit()

    def __get_connection(self) -> sqlite3.Connection:
        """
        Établit et retourne une connexion active à la base de données SQLite.
        Configure le timeout pour la gestion des accès concurrents.

        Returns:
            - sqlite3.Connection : Instance de connexion à la base de données.
        """
        try:
            # On utilise le timeout stocké ou une valeur par défaut de 10 secondes
            # pour éviter les blocages lors d'écritures simultanées.
            connection = sqlite3.connect(self._db_path, timeout=10)
            
            # Activation des clés étrangères pour garantir l'intégrité référentielle
            connection.execute("PRAGMA foreign_keys = ON;")
            
            return connection
            
        except sqlite3.Error as error:
            raise ConnectionError(f"Erreur lors de l'établissement de la connexion SQLite : {error}")


    # --- [ Gestion des Données Financières ] ---
    def _truncate_performance_table(self):
        """
        Supprime l'intégralité des données stockées dans la table 'performances'.

        Cette opération réinitialise la table sans supprimer sa structure. Elle est 
        utile avant un recalcul complet pour garantir la propreté des données.
        """
        query_delete = "DELETE FROM performances"
        query_reset_seq = "DELETE FROM sqlite_sequence WHERE name='performances'"

        try:
            # Utilisation de la méthode de connexion privée de la classe
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query_delete)
                cursor.execute(query_reset_seq)
                connection.commit()

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors du vidage de la table performances : {error}")
        
    def _fetch_and_update_companies(self, tickers: list[str]) -> None:
        """
        Récupère et met à jour les données pour une liste de tickers de manière groupée.
        
        Optimisation : Utilise le multi-threading pour paralléliser les appels réseau 
        vers Yahoo Finance (I/O bound), puis effectue les écritures en base 
        de manière séquentielle pour garantir l'intégrité SQLite.

        Args:
            - tickers (list[str]) : Liste des symboles boursiers.
        """
        if not tickers:
            return

        # Fonction interne pour encapsuler la récupération réseau
        def __fetch_metadata(ticker_symbol: str) -> dict:
            try:
                stock = yf.Ticker(ticker_symbol)
                # L'accès aux propriétés force le téléchargement des données
                return {
                    "ticker": ticker_symbol,
                    "stock_obj": stock,
                    "info": stock.info,      # Appel réseau 1
                    "dividends": stock.dividends, # Appel réseau 2
                    "splits": stock.splits,    # Appel réseau 3
                    "error": None
                }
            except Exception as e:
                return {"ticker": ticker_symbol, "error": str(e)}

        # 1. Téléchargement parallèle (Gain de performance majeur)
        # max_workers=10 est un bon équilibre pour ne pas saturer la connexion
        fetched_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            fetched_results = list(executor.map(__fetch_metadata, tickers))

        # 2. Écriture séquentielle en base (Sécurité SQLite)
        for data in fetched_results:
            if data["error"]:
                # On log l'erreur mais on ne bloque pas le processus pour les autres
                print(f"[Attention] Échec récupération métadonnées pour {data['ticker']} : {data['error']}")
                continue
            
            try:
                # Mise à jour des métadonnées
                self.__upsert_company_info(data["ticker"], data["info"])
                
                # Mise à jour des événements sur titres
                # On passe l'objet stock déjà hydraté par le thread pour éviter un nouvel appel réseau
                self.__update_dividends(data["ticker"], data["stock_obj"])
                self.__update_splits(data["ticker"], data["stock_obj"])
                
            except RuntimeError as e:
                print(f"[Erreur] Échec écriture BDD pour {data['ticker']} : {e}")

        # 3. Téléchargement massif des prix historiques (Géré nativement par yfinance)
        self.__update_mass_stock_prices(tickers)
        
    def __update_mass_stock_prices(self, tickers: list[str]):
        """
        Télécharge et insère les prix historiques pour tous les tickers en un seul bloc.
        Écrase les données existantes en base si elles sont déjà présentes (Upsert).

        Args:
            - tickers (list[str]) : Liste des tickers à mettre à jour.
        """
        if not tickers:
            return

        # On cherche la dernière date connue pour chaque ticker pour optimiser l'appel
        last_dates = [self.__get_last_date_in_table("stock_price", t) for t in tickers]
        
        if None in last_dates:
            period = "max"
            start_date = None
        else:
            period = None
            # Marge de sécurité de 5 jours pour pallier les éventuelles corrections de données
            start_date = (pd.to_datetime(min(last_dates)) - pd.Timedelta(days=5)).strftime('%Y-%m-%d')

        # threads=True permet d'accélérer la récupération réseau
        data = yf.download(
            tickers,
            start=start_date,
            period=period,
            group_by='ticker',
            threads=True,
            auto_adjust=False,
            progress=False
        )

        if data.empty:
            return

        price_records = []

        # yfinance renvoie un MultiIndex si plusieurs tickers, ou un DF simple si un seul
        actual_tickers = [tickers] if isinstance(data.columns, pd.Index) and not isinstance(data.columns, pd.MultiIndex) else tickers

        for ticker in actual_tickers:
            try:
                # Extraction du sous-ensemble pour le ticker actuel
                ticker_df = data[ticker] if len(actual_tickers) > 1 else data
                ticker_df = ticker_df.dropna(subset=['Open', 'Close'])

                if ticker_df.empty:
                    continue

                # Préparation vectorisée pour limiter l'usage de boucles Python
                temp_df = ticker_df.reset_index()
                temp_df['ticker'] = ticker
                temp_df['formatted_date'] = temp_df['Date'].dt.strftime('%Y-%m-%d')

                # Création des tuples pour executemany
                for _, row in temp_df.iterrows():
                    price_records.append((
                        row['ticker'],
                        row['formatted_date'],
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume'])
                    ))
            except KeyError:
                # Cas où un ticker demandé n'est pas retourné par l'API
                continue

        # --- Insertion en base de données ---
        if price_records:
            query = """
                INSERT OR REPLACE INTO stock_price 
                (ticker, date, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            try:
                with self.__get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, price_records)
                    conn.commit()
            except sqlite3.Error as error:
                raise RuntimeError(f"Erreur lors de l'insertion massive des prix : {error}")

    def __upsert_company_info(self, ticker: str, info: dict):
        """
        Insère ou met à jour les données descriptives de l'entreprise dans la table 'company'.

        Utilise la clause 'ON CONFLICT' pour mettre à jour les informations si le ticker 
        existe déjà, garantissant ainsi la fraîcheur des données (secteur, site web, etc.).

        Args:
            - ticker (str) : Symbole boursier de l'actif.
            - info (dict) : Dictionnaire de données provenant de yfinance.
        """
        # Préparation du tuple de données avec gestion des valeurs de repli (fallbacks)
        data = (
            ticker,
            info.get('longName') or info.get('shortName') or ticker,
            info.get('isin'),
            info.get('sector'),
            info.get('country'),
            info.get('website'),
            info.get('longBusinessSummary'),
            info.get('exchange'),
            info.get('currency')
        )

        query = """
            INSERT INTO company (
                ticker, name, isin, sector, country, website, description, stock_exchange, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name, 
                isin=excluded.isin, 
                sector=excluded.sector,
                country=excluded.country, 
                website=excluded.website, 
                description=excluded.description, 
                stock_exchange=excluded.stock_exchange,
                currency=excluded.currency
        """

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query, data)
                connection.commit()

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de l'UPSERT des infos de l'entreprise {ticker} : {error}")
        
    def __update_dividends(self, ticker: str, stock_obj: yf.Ticker):
        """
        Récupère et insère les dividendes versés par une entreprise.

        Extrait l'historique complet des dividendes bruts et procède à une 
        insertion par remplacement pour éviter les doublons sur le couple ticker/date.

        Args:
            - ticker (str) : Symbole boursier de l'actif.
            - stock_obj (yf.Ticker) : Objet Ticker initialisé de Yahoo Finance.
        """
        # Récupération de la série temporelle des dividendes
        dividends = stock_obj.dividends
        
        if dividends.empty:
            return

        # Préparation des données pour l'insertion SQL (Mapping Date et Montant)
        div_data = [
            (ticker, date.strftime('%Y-%m-%d'), float(amount)) 
            for date, amount in dividends.items()
        ]

        query = """
            INSERT OR REPLACE INTO dividend (ticker, date, amount)
            VALUES (?, ?, ?)
        """

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.executemany(query, div_data)
                connection.commit()

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de la mise à jour des dividendes pour {ticker} : {error}")

    def __update_splits(self, ticker: str, stock_obj: yf.Ticker):
        """
        Récupère et insère les fractionnements d'actions (splits) depuis Yahoo Finance.

        Cette méthode extrait l'historique des splits et utilise une insertion par 
        remplacement pour éviter les doublons sur le couple ticker/date.

        Args:
            - ticker (str) : Symbole boursier de l'actif.
            - stock_obj (yf.Ticker) : Objet Ticker initialisé de Yahoo Finance.
        """
        # Récupération de la série temporelle des splits
        splits = stock_obj.splits
        
        if splits.empty:
            return

        # Préparation des données pour l'insertion SQL
        # Le ratio est converti en float pour assurer la compatibilité avec la base
        split_data = [
            (ticker, date.strftime('%Y-%m-%d'), float(ratio)) 
            for date, ratio in splits.items()
        ]

        query = """
            INSERT OR REPLACE INTO split (ticker, date, ratio)
            VALUES (?, ?, ?)
        """

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.executemany(query, split_data)
                connection.commit()

        except sqlite3.Error as error:
            # Levée d'une RuntimeError avec un message explicite en français
            raise RuntimeError(f"Erreur lors de la mise à jour des splits pour {ticker} : {error}")
    
    def __apply_splits(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ajuste les quantités et les prix d'achat des transactions en fonction
        des fractionnements d'actions (splits) enregistrés en base.

        Args:
            - df (pd.DataFrame) : DataFrame des transactions (indexé par date).

        Returns:
            - pd.DataFrame : DataFrame avec les colonnes 'quantity' et 'stock_price' ajustées.
        """
        # Récupération de l'historique des splits via la méthode dédiée
        splits = self.__get_splits_from_db()
        
        if splits.empty or df.empty:
            return df

        # Copie profonde pour garantir l'intégrité du DataFrame original
        adjusted_df = df.copy()

        # Tri des splits par date (du plus ancien au plus récent)
        # Indispensable pour appliquer les ratios de manière cumulative
        splits = splits.sort_values(by='date', ascending=True)

        for _, split in splits.iterrows():
            ticker = split['ticker']
            split_date = split['date']
            ratio = float(split['ratio'])

            # Cible : transactions du même ticker effectuées STRICTEMENT AVANT le split
            mask = (adjusted_df['ticker'] == ticker) & (adjusted_df.index < split_date)

            if mask.any():
                # --- Logique d'Ajustement ---
                # Exemple : Split 1:10 (ratio = 10)
                # 1. La quantité possédée est multipliée par le ratio
                adjusted_df.loc[mask, 'quantity'] *= ratio
                
                # 2. Le prix de revient unitaire est divisé par le ratio
                # Note : Le montant total (quantity * stock_price) reste constant
                adjusted_df.loc[mask, 'stock_price'] /= ratio

        return adjusted_df


    # --- [ Gestion des Transactions ] ---
    def _insert_transactions_from_df(self, transactions_df: pd.DataFrame):
        """
        Insère un ensemble de transactions en base à partir d'un DataFrame.

        Args:
            - transactions_df (pd.DataFrame) : DataFrame contenant les colonnes :
                                              'ticker', 'currency', 'operation', 'date', 
                                              'amount', 'fees', 'stock_price', 'quantity'.
        """
        if transactions_df.empty:
            return

        query = """
            INSERT INTO user_transaction (
                ticker, currency, operation, date, amount, fees, stock_price, quantity
            ) VALUES (
                :ticker, :currency, :operation, :date, :amount, :fees, :stock_price, :quantity
            )
        """

        try:
            with self.__get_connection() as connection:
                # Conversion du DataFrame en liste de dictionnaires (orient='records')
                # Cette structure est parfaitement adaptée à executemany
                data_to_insert = transactions_df.to_dict(orient='records')
                connection.executemany(query, data_to_insert)
                connection.commit()

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de l'insertion groupée des transactions : {error}")
           

    # --- [ Gestion des Performances ] ---
    def _insert_performance_from_df(self, df: pd.DataFrame, metric_type: str, portfolio_name: str):
        """
        Insère ou met à jour les données de performance d'un DataFrame dans la table SQL.

        Le DataFrame est transformé d'un format large vers un format long. 
        Utilise 'INSERT OR REPLACE' pour gérer les doublons sur le couple date/ticker.

        Args:
            - df (pd.DataFrame) : DataFrame indexé par date avec les tickers en colonnes.
            - metric_type (str) : Type de métrique (ex: 'tickers_twr', 'tickers_gain').
            - portfolio_name (str) : Nom du portefeuille associé aux données.
        """
        if df.empty:
            return

        # Transformation du DataFrame : passage du format large au format long
        # Logique : reset_index pour récupérer la date, puis melt pour pivoter les tickers
        melted_df = (
            df.reset_index()
            .rename(columns={'index': 'date'})
            .melt(id_vars=['date'], var_name='ticker', value_name='value')
        )

        # Ajout des métadonnées et formatage de la date pour SQLite
        melted_df['metric_type'] = metric_type
        melted_df['portfolio_name'] = portfolio_name
        melted_df['date'] = melted_df['date'].dt.strftime('%Y-%m-%d')

        # Requête SQL utilisant l'UPSERT (Gestion des conflits via la contrainte UNIQUE)
        query = """
            INSERT OR REPLACE INTO performances (date, ticker, metric_type, value, portfolio_name)
            VALUES (:date, :ticker, :metric_type, :value, :portfolio_name)
        """

        try:
            with self.__get_connection() as connection:
                # Transformation en liste de dictionnaires pour une insertion groupée efficace
                records = melted_df.to_dict(orient='records')
                connection.executemany(query, records)
                connection.commit()

        except Exception as error:
            raise RuntimeError(
                f"Erreur lors de l'insertion des performances ({metric_type}) "
                f"pour le portefeuille '{portfolio_name}' : {error}"
            )
         

    # --- [ Gestion des Devises ] ---
    def _convert_dataframe_to_currency(self, df: pd.DataFrame, target_currency: str) -> pd.DataFrame:
        """
        Convertit les colonnes d'un DataFrame (prix de tickers) vers une devise cible 
        de façon vectorisée en utilisant les taux de change EUR/USD.

        Args:
            - df (pd.DataFrame) : DataFrame avec les tickers en colonnes et les dates en index.
            - target_currency (str) : La devise de destination ("USD" ou "EUR").

        Returns:
            - pd.DataFrame : Le DataFrame converti dans la devise cible.
        """
        if df.empty:
            return df

        if target_currency not in ("USD", "EUR"):
            raise ValueError("La devise cible doit être USD ou EUR")

        # Récupération de la structure des devises par ticker via la méthode protégée
        # Renvoie un dictionnaire : {'USD': ['AAPL', ...], 'EUR': ['AIR', ...]}
        currencies_groups = self.__get_tickers_grouped_by_currency_company(list(df.columns))
        
        # Récupération des taux de change EURUSD (base Euro : 1 EUR = X USD)
        fx_data = self.__get_stock_opening_prices("EURUSD=X")
        
        if fx_data.empty:
            raise ValueError("Données de change indisponibles pour EURUSD=X dans la base.")

        # On aligne les taux sur l'index du DF et on comble les trous (jours fériés)
        fx_series = fx_data["open_price"].reindex(df.index).ffill().bfill().astype(float)

        converted_df = df.copy()
        
        # Cas 1 : Conversion vers l'EUR
        if target_currency == "EUR":
            # On ne convertit que les tickers qui sont initialement en USD
            usd_tickers = [t for t in df.columns if t in currencies_groups.get("USD", [])]
            if usd_tickers:
                # Prix EUR = Prix USD / Taux (EUR/USD)
                converted_df[usd_tickers] = converted_df[usd_tickers].div(fx_series, axis=0)

        # Cas 2 : Conversion vers l'USD
        elif target_currency == "USD":
            # On ne convertit que les tickers qui sont initialement en EUR
            eur_tickers = [t for t in df.columns if t in currencies_groups.get("EUR", [])]
            if eur_tickers:
                # Prix USD = Prix EUR * Taux (EUR/USD)
                converted_df[eur_tickers] = converted_df[eur_tickers].mul(fx_series, axis=0)

        return converted_df

    def __get_tickers_grouped_by_currency_company(self, tickers: list[str]) -> dict[str, list[str]]:
        """
        Groupe une liste de tickers par leur devise respective enregistrée en base.

        Interroge la table 'company' pour déterminer la devise de chaque ticker 
        fourni. Organise ensuite les résultats dans un dictionnaire.

        Args:
            - tickers (list[str]) : Liste des symboles boursiers à filtrer et grouper.

        Returns:
            - dict[str, list[str]] : Dictionnaire mappant les codes de devises à leurs listes de tickers.
        """
        if not tickers:
            return {}

        # Préparation de la requête sécurisée
        placeholders = ', '.join(['?'] * len(tickers))
        query = f"SELECT ticker, currency FROM company WHERE ticker IN ({placeholders})"
        
        # Initialisation du dictionnaire de regroupement
        grouped_tickers = defaultdict(list)

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query, tickers)
                results = cursor.fetchall()

                # La structure SQL garantit que 'currency' ne peut pas être NULL
                for ticker, currency in results:
                    grouped_tickers[currency].append(ticker)

            return dict(grouped_tickers)

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de la récupération des devises : {error}")
        

    # --- [ Gestion des Fichiers ] ---
    def _mark_file_as_processed(self, file_id: int):
        """
        Met à jour le statut d'un fichier en base de données pour indiquer qu'il a été traité.

        Args:
            - file_id (int) : L'identifiant du fichier à marquer comme traité.
        """
        query = "UPDATE file SET processed = 1 WHERE id = ?"

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query, (file_id,))
                connection.commit()

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de la mise à jour du statut 'processed' : {error}")
        
    def _insert_pdf_to_database(self, file_path: str, table_name: str) -> int:
        """
        Gère la lecture d'un fichier PDF et son insertion sécurisée en base de données.
        Vérifie l'absence de doublons avant l'écriture.

        Args:
            - file_path (str) : Chemin complet du fichier sur le disque.
            - table_name (str) : Nom de la catégorie associée au document (ex: 'buy', 'sell').

        Returns:
            - int : L'identifiant (ID) de la ligne insérée, ou -1 si le fichier est un doublon.
        """
        # Vérification de l'existence du fichier physique
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        # Lecture binaire du fichier pour stockage en BLOB
        with open(file_path, 'rb') as file:
            file_binary_data = file.read()

        # Vérification de l'unicité via le contenu binaire (évite les doublons exacts)
        if self.__is_file_duplicated(file_binary_data):
            return -1

        # Insertion en base de données via la méthode privée dédiée
        return self.__add_file_record(
            file_bytes=file_binary_data,
            table_name=table_name
        )

    def __add_file_record(self, file_bytes: bytes, table_name: str) -> int:
        """
        Insère un nouvel enregistrement dans la table 'file'.
        La date est gérée automatiquement par le DEFAULT CURRENT_TIMESTAMP de la base.

        Args:
            - file_bytes (bytes) : Le contenu binaire du fichier PDF.
            - table_name (str) : Le nom de la table associée (ex: 'buy', 'sell').

        Returns:
            - int : L'identifiant (ID) de la ligne insérée.
        """
        query = """
            INSERT INTO file (file, table_associee, processed)
            VALUES (?, ?, 0)
        """
        
        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query, (file_bytes, table_name))
                
                # Récupération de l'ID auto-incrémenté généré par SQLite
                return cursor.lastrowid
            
        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de l'insertion dans la table 'file' : {error}")
        
    def __is_file_duplicated(self, file_bytes: bytes) -> bool:
        """
        Vérifie si le contenu binaire du fichier existe déjà dans la table 'file'.
        
        Args:
            - file_bytes (bytes) : Le contenu binaire du PDF à vérifier.
            
        Returns:
            - bool : True si le fichier est un doublon, False sinon.
        """
        query = "SELECT 1 FROM file WHERE file = ? LIMIT 1"

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                
                # Recherche par contenu binaire exact (BLOB)
                cursor.execute(query, (file_bytes,))
                result = cursor.fetchone()
                
                # Si un résultat est trouvé, c'est un doublon
                return result is not None

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de la vérification d'unicité du fichier : {error}")

    
    # --- [ Getters ] ---
    def _get_all_company_tickers(self) -> list[str]:
        """
        Récupère la liste de tous les symboles boursiers (tickers) 
        enregistrés dans la table 'company'.

        Returns:
            - list[str] : Une liste de chaînes de caractères contenant les tickers.
        """
        query = "SELECT ticker FROM company"

        try:
            with self.__get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query)
                
                # fetchall renvoie une liste de tuples : [('AAPL',), ('MSFT',)]
                # On utilise une compréhension de liste pour extraire la première valeur
                return [row[0] for row in cursor.fetchall()]

        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur lors de la récupération des tickers : {error}")
        
    def _get_all_tickers_opening_prices_df(self) -> pd.DataFrame:
        """
        Récupère l'intégralité des prix d'ouverture pour tous les tickers stockés 
        dans la base de données et les organise dans un DataFrame structuré.

        Returns:
            - pd.DataFrame : DataFrame dont l'index est la date et les colonnes sont les tickers.
        """
        query = "SELECT date, ticker, open_price FROM stock_price"
        
        try:
            with self.__get_connection() as conn:
                raw_data = pd.read_sql_query(query, conn, parse_dates=['date'])

            if raw_data.empty:
                return pd.DataFrame()
            
            # Passage d'un format 'long' à un format 'wide'
            prices_df = raw_data.pivot(index='date', columns='ticker', values='open_price')

            # Tri chronologique de l'index et remplissage par propagation (forward fill)
            prices_df = prices_df.sort_index().ffill()

            return prices_df

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la récupération globale des prix : {error}")
      
    def _get_tickers_grouped_by_currency_transaction(self) -> dict[str, list[str]]:
        """
        Récupère les tickers présents dans les transactions et les regroupe par devise.
        Cette méthode part du principe que la devise est obligatoirement renseignée.

        Returns:
            - dict[str, list[str]] : Dictionnaire {devise: [liste_de_tickers]}.
        """
        query = """
            SELECT DISTINCT ticker, currency 
            FROM user_transaction 
            WHERE ticker IS NOT NULL
        """
        
        # Initialisation du dictionnaire de regroupement
        # Utilisation de defaultdict pour éviter les tests d'existence de clés
        grouped_data = defaultdict(list)

        try:
            with self.__get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()

                for ticker, currency in results:
                    # On s'assure que la devise est traitée uniformément (ex: 'eur' -> 'EUR')
                    currency_key = str(currency).strip().upper()
                    
                    # Validation résiduelle pour éviter les clés vides inattendues
                    if not currency_key:
                        raise ValueError(f"La devise pour le ticker '{ticker}' est vide en base.")
                    
                    grouped_data[currency_key].append(ticker)

                return dict(grouped_data)

        except Exception as error:
            if isinstance(error, ValueError):
                raise error
            raise RuntimeError(f"Erreur lors du regroupement des tickers par devise : {error}")
        
    def _get_transactions_by_currency(self, currency: str = None) -> pd.DataFrame:
        """
        Récupère les transactions en filtrant par la devise définie.
        La colonne 'date' est définie comme index.

        Args:
            - currency (str, optional) : Le code de la devise (ex: 'EUR', 'USD'). 
                                         Si None, récupère toutes les transactions.

        Returns:
            - pd.DataFrame : DataFrame indexé par date contenant les transactions.
        """
        query = "SELECT * FROM user_transaction"
        params = []

        if currency:
            query += " WHERE currency = ?"
            params.append(currency)
        
        query += " ORDER BY date ASC"

        try:
            with self.__get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)

            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()

            return self.__apply_splits(df)

        except Exception as error:
            scope = f"en {currency}" if currency else "globales"
            raise RuntimeError(f"Erreur lors de la récupération des transactions {scope} : {error}")
        
    def _get_first_transaction_date(self) -> pd.Timestamp:
        """
        Récupère la date de la toute première transaction enregistrée dans la base.
        Cette date sert généralement de point de départ pour les calculs de performance.

        Returns:
            - pd.Timestamp : La date la plus ancienne trouvée dans la table transaction.
        """
        query = "SELECT MIN(date) FROM user_transaction"

        try:
            with self.__get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()

                if result and result[0]:
                    return pd.to_datetime(result[0])
                
                return None

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la récupération de la première date de transaction : {error}")
        
    def _get_tickers_dividends_df(self, tickers: list[str], start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Récupère les dividendes nets perçus pour une liste de tickers entre deux dates.
        Structure les données sous forme de DataFrame avec les tickers en colonnes.

        Args:
            - tickers (list[str]) : Liste des symboles boursiers pour lesquels extraire les dividendes.
            - start_date (datetime) : Date de début de la période de recherche.
            - end_date (datetime) : Date de fin de la période de recherche.

        Returns:
            - pd.DataFrame : DataFrame indexé par date avec les dividendes nets par ticker en colonnes.
        """
        # Création de l'index temporel complet pour la période demandée
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        dividends_df = pd.DataFrame(0.0, index=date_range, columns=tickers)
        dividends_df.index.name = 'date'

        # Conversion des dates en chaînes de caractères pour la requête SQL (format ISO)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # Requête SQL pour récupérer les dividendes nets (montant - frais)
        # Utilisation de placeholders pour sécuriser la requête contre les injections
        placeholders = ','.join(['?'] * len(tickers))
        query = f"""
            SELECT date, ticker, (amount - fees) as net_dividend 
            FROM user_transaction 
            WHERE operation = 'dividend' 
            AND date BETWEEN ? AND ?
            AND ticker IN ({placeholders})
        """

        params = [start_str, end_str] + tickers

        try:
            with self.__get_connection() as conn:
                raw_data = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])

            if not raw_data.empty:
                # Pivotage des données pour aligner les tickers en colonnes
                pivoted_data = raw_data.pivot(index='date', columns='ticker', values='net_dividend')
                
                # Mise à jour du DataFrame principal
                # L'opération 'update' modifie l'objet en place
                dividends_df.update(pivoted_data)

            return dividends_df

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la récupération des dividendes : {error}")
        
    def _get_transactions_in_eur(self) -> pd.DataFrame:
        """
        Récupère toutes les transactions et convertit les montants en EUR.
        Utilise le taux de change EURUSD=X pour les opérations en USD.

        Returns:
            - pd.DataFrame : Transactions converties en EUR, indexées par date.
        """
        query_tx = "SELECT id, ticker, currency, operation, date, amount, fees, stock_price, quantity FROM user_transaction"
        
        try:
            with self.__get_connection() as conn:
                df = pd.read_sql_query(query_tx, conn, parse_dates=['date'])

            if df.empty:
                return pd.DataFrame()

            df = df.set_index("date").sort_index()
            
            # Conversion des colonnes numériques pour garantir la précision
            numeric_cols = ["amount", "fees", "stock_price", "quantity"]
            df[numeric_cols] = df[numeric_cols].astype(float)

            # Récupération des taux d'ouverture via la méthode interne
            fx_df = self.__get_stock_opening_prices("EURUSD=X")

            if fx_df.dropna().empty:
                raise ValueError("Pas de données de change disponibles (EURUSD=X) dans la base.")

            # Alignement des taux sur les dates des transactions (gestion week-ends/fériés)
            fx_df = fx_df.reindex(df.index.unique()).ffill().bfill()

            # Identification des lignes nécessitant une conversion
            usd_mask = df["currency"] == "USD"

            if usd_mask.any():
                # On joint les taux correspondants à chaque ligne de transaction
                # map() est beaucoup plus rapide que apply() pour cette opération
                rates = df.index.map(fx_df["EURUSD=X"])

                # Division vectorisée (USD -> EUR)
                df.loc[usd_mask, "amount"] /= rates[usd_mask]
                df.loc[usd_mask, "fees"] /= rates[usd_mask]
                df.loc[usd_mask, "stock_price"] /= rates[usd_mask]
                
                # Mise à jour de la devise
                df.loc[usd_mask, "currency"] = "EUR"

            # Uniformisation finale
            df["currency"] = "EUR"

            return self.__apply_splits(df)

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la conversion des transactions en EUR : {error}")
        
    def _get_unprocessed_files(self) -> list:
        """
        Récupère les données binaires des PDF non traités.
        """
        try:
            connection = sqlite3.connect(self._db_path)
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            # On récupère directement le BLOB (colonne 'file')
            query = "SELECT id, table_associee, file FROM file WHERE processed = 0"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            unprocessed_list = []
            for row in rows:
                unprocessed_list.append({
                    'id': row['id'],
                    'table_associee': row['table_associee'],
                    'content': row['file'] # Le contenu binaire
                })

            connection.close()
            return unprocessed_list
        except sqlite3.Error as error:
            raise RuntimeError(f"Erreur SQL : {error}")

    def __get_stock_opening_prices(self, ticker: str) -> pd.DataFrame:
        """
        Récupère l'historique des prix d'ouverture pour un titre spécifique.
        La date est définie comme index du DataFrame.

        Args:
            - ticker (str) : Le symbole boursier (ex: 'AAPL').

        Returns:
            - pd.DataFrame : DataFrame avec 'date' en index et 'open_price' en colonne.
                             Retourne un DataFrame vide si aucune donnée n'est trouvée.
        """
        query = """
            SELECT date, open_price 
            FROM stock_price 
            WHERE ticker = ? 
            ORDER BY date ASC
        """
        
        try:
            with self.__get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[ticker])

                if not df.empty:
                    # Conversion et indexation via chaînage (plus robuste et explicite)
                    # On évite inplace=True pour garantir une transition propre des données
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                    df.index.name = 'date'
                
                return df

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la récupération des prix pour {ticker} : {error}")
        
    def __get_last_date_in_table(self, table_name: str, ticker: str) -> str:
        """
        Cherche la date la plus récente enregistrée pour un ticker spécifique dans une table donnée.

        Args:
            - table_name (str) : Nom de la table SQL (stock_price, dividend, split).
            - ticker (str) : Le symbole boursier.

        Returns:
            - str : La date au format 'YYYY-MM-DD' ou None si aucune donnée n'est trouvée.
        """
        # Comme on ne peut pas utiliser de paramètre (?) pour un nom de table,
        # on valide que la table demandée fait partie des tables autorisées.
        allowed_tables = ['stock_price', 'dividend', 'split']
        if table_name not in allowed_tables:
            raise ValueError(f"Nom de table non autorisé : {table_name}")

        query = f"SELECT MAX(date) FROM {table_name} WHERE ticker = ?"

        try:
            with self.__get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (ticker,))
                result = cursor.fetchone()
                
                # Logique : renvoie la date (str) ou None
                return result[0] if result and result[0] else None

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la récupération de la dernière date ({table_name}) : {error}")
        
    def __get_splits_from_db(self) -> pd.DataFrame:
        """
        Récupère tous les fractionnements d'actions (splits) enregistrés en base de données.

        Returns:
            - pd.DataFrame : DataFrame contenant les colonnes [ticker, date, ratio].
        """
        query = "SELECT ticker, date, ratio FROM split"
        
        try:
            with self.__get_connection() as conn:
                # Chargement des données avec conversion automatique des dates
                df = pd.read_sql_query(query, conn, parse_dates=['date'])
            
            return df

        except Exception as error:
            raise RuntimeError(f"Erreur lors de la récupération des splits : {error}")
      
    def _get_performance_data(self, portfolio_name: str = None, ticker: str = None, metric_type: str = None) -> pd.DataFrame:
        """
        Récupère les données de performance de manière filtrée et ordonnée.

        La méthode applique un filtre dynamique : si un argument est None, il est 
        exclu des critères de recherche. Les résultats sont triés par portefeuille, 
        puis par ticker, et enfin par type de métrique.

        Args:
            - portfolio_name (str, optional) : Nom du portefeuille cible.
            - ticker (str, optional) : Symbole de l'actif cible.
            - metric_type (str, optional) : Type de métrique (ex: 'valuation').

        Returns:
            - pd.DataFrame : Données filtrées et triées par [portfolio_name, ticker, metric_type].
        """
        # Construction de la requête de base
        query = "SELECT date, ticker, metric_type, value, portfolio_name FROM performances WHERE 1=1"
        params = []

        # Application des filtres dynamiques
        if portfolio_name:
            query += " AND portfolio_name = ?"
            params.append(portfolio_name)

        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)

        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)

        # Tri selon vos instructions : Portefeuille > Ticker > Métrique
        # On ajoute également la date à la fin pour garantir un ordre chronologique
        query += " ORDER BY portfolio_name ASC, ticker ASC, metric_type ASC, date ASC"

        # Extraction des données
        with self.__get_connection() as connection:
            df = pd.read_sql_query(query, connection, params=params)
            
            # Conversion de la date pour faciliter l'exploitation des séries temporelles
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                
            return df
    