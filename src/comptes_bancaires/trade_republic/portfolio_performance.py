import pandas as pd

from comptes_bancaires.trade_republic.portfolio_engine import PortfolioEngine
from database.trade_republic_database import TradeRepublicDatabase


class PortfolioPerformance(TradeRepublicDatabase):
    """
    Cette classe orchestre le calcul et la gestion des performances du portefeuille financier.
    
    Elle hérite de 'TradeRepublicDatabase' pour l'accès aux données persistées et assure 
    la consolidation des indicateurs (valorisation, performance, gains, dividendes) à l'échelle 
    individuelle (tickers) et globale (portefeuille).
    
    La classe gère nativement le regroupement par devise, la conversion monétaire vers 
    l'Euro et la synchronisation des données temporelles pour garantir des calculs 
    de performance homogènes.
    """

    def __init__(self, db_path: str):
        """
        Initialise l'analyseur de performance en configurant la connexion à la base de données
        et en chargeant les données de référence (prix, dates, structures).

        Args:
            - db_path (str) : Chemin d'accès vers le fichier de base de données SQLite.
        """
        super().__init__(db_path)
        self.performances = self.__init_performance_structure()

        # Récupère les tickers et prix d’ouverture globaux
        self.__tickers_open_prices = self._get_all_tickers_opening_prices_df()
        self.__start_date = self._get_first_transaction_date()
        self.__end_date = pd.to_datetime(self.__tickers_open_prices.index[-1])
        self.__portfolio_engine = PortfolioEngine(self.__start_date, self.__end_date)
        self.__portfolio_name = 'Mes Portefeuilles'


    # --- [ Analyse de Performance ] ---
    def calculate_performance(self):
        """
        Point d'entrée principal pour le calcul et la visualisation des performances du portefeuille.

        Initialise les structures de données, regroupe les actifs par devise, traite les transactions 
        et, si des données sont présentes, génère les résultats consolidés ainsi que les graphiques associés.
        """
        # Initialisation de la structure de stockage et récupération des tickers par devise
        performances_tickers_eur = self.__init_tickers_structure()
        currencies_tickers = self._get_tickers_grouped_by_currency_transaction()

        # Traitement séquentiel par devise pour la conversion et le calcul
        transactions_not_empty = self.__process_currencies(currencies_tickers, performances_tickers_eur)

        # Calcul final et rendu graphique si des transactions ont été traitées
        if transactions_not_empty:
            self.__compute_portfolio_results(performances_tickers_eur)

    def __compute_portfolio_results(self, performances_tickers_eur: dict):
        """
        Calcule les performances globales du portefeuille et effectue la comparaison avec les benchmarks.

        Agrège les données de valorisation, d'investissement et de dividendes à l'échelle du portefeuille. 
        Calcule les plus-values réalisées, le gain total (latent et réalisé), ainsi que divers 
        indicateurs de performance (CAGR, Yield).

        Args:
            performances_tickers_eur (dict): Dictionnaire consolidé des performances par ticker en EUR.
        """

        # Consolidation des métriques de base par somme pondérée des tickers
        portfolio_valuation = performances_tickers_eur["tickers_valuation"][self.__portfolio_name].sum(axis=1)
        portfolio_invested_amounts = performances_tickers_eur["tickers_invested_amounts"][self.__portfolio_name].sum(axis=1)
        portfolio_dividends = performances_tickers_eur["tickers_dividends"][self.__portfolio_name].sum(axis=1)

        # Récupération des transactions et initialisation du moteur de calcul
        transactions_eur = self._get_transactions_in_eur()

        # Calcul de l'évolution des plus-values réalisées
        portfolio_realized_gains_losses = self.__portfolio_engine._compute_plus_value_evolution(
            transactions_eur,
            performances_tickers_eur["tickers_invested_amounts"][self.__portfolio_name]
        )["plus_value_cumulative"]

        # Le gain total combine les gains latents des tickers et les plus-values déjà réalisées
        portfolio_gain = performances_tickers_eur["tickers_gain"][self.__portfolio_name].sum(axis=1) + portfolio_realized_gains_losses

        # Calcul du capital réellement investi net des plus-values réalisées
        invested_money = (
            performances_tickers_eur["tickers_invested_amounts"][self.__portfolio_name].sum(axis=1).iloc[-1] - portfolio_realized_gains_losses.iloc[-1]
        )

        # Calcul du pourcentage de gain global
        portfolio_gain_pct = self.__portfolio_engine._calculate_portfolio_percentage_change(portfolio_gain, invested_money)

        # Sauvegarde de l'ensemble des indicateurs de performance globale
        self.performances["portfolio_valuation"][self.__portfolio_name] = portfolio_valuation
        self.performances["portfolio_invested_amounts"][self.__portfolio_name] = portfolio_invested_amounts
        self.performances["portfolio_gain"][self.__portfolio_name] = portfolio_gain
        self.performances["portfolio_performance"][self.__portfolio_name] = portfolio_gain_pct
        self.performances["portfolio_monthly_percentages"][self.__portfolio_name] = self.__portfolio_engine._calculate_monthly_percentage_change(portfolio_valuation, transactions_eur)
        self.performances["portfolio_dividends"][self.__portfolio_name] = portfolio_dividends
        self.performances["portfolio_dividend_earn"][self.__portfolio_name] = self.__portfolio_engine._calculate_dividend_earn(transactions_eur)
        self.performances["portfolio_dividend_yield"][self.__portfolio_name] = self.__portfolio_engine._calculate_dividend_yield(transactions_eur, portfolio_valuation)
        self.performances["portfolio_cash"][self.__portfolio_name] = self.__portfolio_engine._compute_cash_evolution(transactions_eur)["cash_cumulative"]
        self.performances["portfolio_fees"][self.__portfolio_name] = self.__portfolio_engine._compute_fees_evolution(transactions_eur)["cumulative_fees"]
        self.performances["portfolio_cagr"][self.__portfolio_name] = self.__portfolio_engine._calculate_portfolio_cagr(portfolio_valuation, portfolio_invested_amounts)

        # On vide la table pour repartir sur une base propre
        self._truncate_performance_table()

        for metric_type, content in self.performances.items():
            # CAS 1 : C'est un dictionnaire (ex: tickers_valuation ou portfolio_cagr)
            if isinstance(content, dict):
                for entity_name, data in content.items():
                    # entity_name sera soit le nom du portfolio, soit le ticker (ex: 'AAPL')
                    if data is not None and hasattr(data, 'empty') and not data.empty:
                        self._insert_performance_from_df(
                            data, 
                            metric_type, 
                            entity_name
                        )
                    elif isinstance(data, (int, float)):
                        # Gestion optionnelle si la donnée est un score unique (ex: CAGR)
                        # Vous pourriez créer un DF d'une ligne ici si nécessaire
                        pass

            # CAS 2 : C'est directement un DataFrame (pour les métriques portfolio_xxx)
            elif isinstance(content, pd.DataFrame):
                if not content.empty:
                    # On utilise le nom du portefeuille actuel pour ces métriques globales
                    self._insert_performance_from_df(
                        content, 
                        metric_type, 
                        self.__portfolio_name
                    )

    def __process_currencies(self, currencies_tickers: dict, performances_tickers_eur: dict) -> bool:
        """
        Traite séquentiellement toutes les devises présentes dans le portefeuille.

        Parcourt le dictionnaire des tickers groupés par devise, récupère les transactions 
        correspondantes et lance le calcul des performances si des données sont disponibles. 
        Retourne un indicateur signalant si au moins une transaction a été traitée.

        Args:
            currencies_tickers (dict): Dictionnaire mappant chaque devise à sa liste de tickers.
            performances_tickers_eur (dict): Dictionnaire global pour le stockage des performances consolidées.

        Returns:
            bool: True si des transactions non vides ont été trouvées et traitées, False sinon.
        """
        transactions_not_empty = False

        for currency, tickers in currencies_tickers.items():
            # Récupération de l'historique des transactions pour la devise actuelle
            transactions = self._get_transactions_by_currency(currency)

            # Si des transactions existent, on déclenche le traitement et le calcul des indicateurs
            if not transactions.empty:
                transactions_not_empty = True
                self.__process_transactions(transactions, tickers, currency, performances_tickers_eur)

        return transactions_not_empty
    
    def __process_transactions(self, transactions: pd.DataFrame, tickers: list, currency: str, performances_tickers_eur: dict):
        """
        Calcule et sauvegarde les performances pour une devise donnée avec gestion de la conversion en EUR.

        Prépare les prix, calcule les indicateurs de performance et archive les résultats. 
        Si la devise est le USD, une conversion monétaire des résultats est effectuée 
        avant la sauvegarde finale dans le dictionnaire consolidé en EUR.

        Args:
            transactions (pd.DataFrame): Historique des transactions.
            tickers (list): Liste des actifs concernés.
            currency (str): Devise de traitement (EUR ou USD).
            performances_tickers_eur (dict): Dictionnaire global de stockage des performances en EUR.
        """

        # Préparation des prix d'ouverture convertis et calcul des performances du portefeuille
        tickers_open_prices_currency = self.__prepare_open_prices_currency(tickers, currency)
        results = self.__compute_portfolio_performance(transactions, tickers_open_prices_currency)

        # Sauvegarde initiale dans la structure de performance principale
        self.__save_performance_tickers(self.performances, results)

        if currency == "EUR":
            # Sauvegarde directe si la devise source est déjà l'euro
            self.__save_performance_tickers(performances_tickers_eur, results)
        elif currency == "USD":
            # Conversion de toutes les métriques en EUR, excepté la performance qui reste un pourcentage
            for key, df in results.items():
                if key != "tickers_performance":
                    results[key] = self._convert_dataframe_to_currency(df, "EUR")
            
            # Sauvegarde des résultats convertis
            self.__save_performance_tickers(performances_tickers_eur, results)

    def __compute_portfolio_performance(self, transactions: pd.DataFrame, tickers_prices: pd.DataFrame) -> dict:
        """
        Calcule l'ensemble des indicateurs de performance pour un portefeuille donné.

        Initialise le moteur de calcul pour évaluer l'évolution des montants investis, 
        le prix de revient unitaire (PRU), les plus-values/moins-values, la performance, 
        la valorisation ainsi que les dividendes perçus.

        Args:
            transactions (pd.DataFrame): Historique des transactions du portefeuille.
            tickers_prices (pd.DataFrame): Historique des prix d'ouverture des actifs.
            start_date (datetime): Date de début de la période d'analyse.
            end_date (datetime): Date de fin de la période d'analyse.

        Returns:
            dict: Dictionnaire regroupant les DataFrames de performance par catégorie.
        """
        # Calcul de l'évolution des montants investis et du prix de revient unitaire (PRU)
        tickers_invested_amounts = self.__portfolio_engine._tickers_investment_amount_evolution(transactions)
        tickers_pru = self.__portfolio_engine._calculate_pru(transactions, tickers_invested_amounts)

        # Calcul de la valorisation, de la performance et des gains/pertes
        tickers_valuation, tickers_performance, tickers_gain = self.__portfolio_engine._capital_gain_losses_composed(tickers_invested_amounts, tickers_pru, tickers_prices)

        # Calcul des dividendes sur la période via la méthode d'instance
        tickers_dividends = self.__portfolio_engine._calculate_dividends(transactions)

        return {
            "tickers_invested_amounts": tickers_invested_amounts,
            "tickers_performance": tickers_performance,
            "tickers_gain": tickers_gain,
            "tickers_valuation": tickers_valuation,
            "tickers_dividends": tickers_dividends,
            "tickers_pru": tickers_pru,
        }
    
    def __save_performance_tickers(self, all_performance: dict, performance: dict):
        """
        Fusionne les performances par ticker dans la structure globale.
        Gère la concaténation de DataFrames ayant des colonnes (tickers) différentes.

        Args:
            all_performance (dict): Dictionnaire global de destination.
            performance (dict): Dictionnaire source contenant les nouveaux DataFrames.
        """
        # Liste exhaustive des catégories de métriques
        categories = [
            "tickers_invested_amounts",
            "tickers_performance",
            "tickers_gain",
            "tickers_valuation",
            "tickers_dividends",
            "tickers_pru"
        ]

        # --- [ Fusion Horizontale et Verticale ] ---
        for key in categories:
            new_df = performance.get(key)

            # Récupération de l'existant
            existing_data = all_performance[key].get(self.__portfolio_name)

            if isinstance(existing_data, pd.DataFrame) and not existing_data.empty:
                # On utilise combine_first ou concat avec une gestion d'index.
                # 'combine_first' est idéal ici : il met à jour les valeurs existantes,
                # ajoute les nouvelles colonnes (tickers) et les nouvelles lignes (dates).
                
                # On s'assure d'abord que les deux sont bien alignés temporellement si nécessaire
                updated_df = existing_data.combine_first(new_df)
                all_performance[key][self.__portfolio_name] = updated_df
            else:
                # Premier enregistrement pour ce portefeuille
                all_performance[key][self.__portfolio_name] = new_df


    # --- [ Préparation des Données ] ---
    def __prepare_open_prices_currency(self, tickers: list, currency: str) -> pd.DataFrame:
        """
        Prépare, convertit et nettoie les prix d'ouverture pour une liste de tickers 
        et une devise spécifique sur une période donnée.

        Filtre les colonnes selon les tickers fournis, applique la conversion monétaire, 
        restreint la plage temporelle et assure la continuité des données par 
        réindexation et remplissage des valeurs manquantes.

        Args:
            tickers (list): Liste des symboles boursiers à extraire.
            currency (str): Code de la devise cible pour la conversion.

        Returns:
            pd.DataFrame: DataFrame des prix d'ouverture réindexé quotidiennement (ffill/bfill).
        """
        # Sélection des colonnes présentes à l'intersection des tickers demandés et disponibles
        open_prices = self.__tickers_open_prices.loc[:, self.__tickers_open_prices.columns.intersection(tickers)]

        # Conversion des prix dans la devise cible via la méthode dédiée
        open_prices_converted = self._convert_dataframe_to_currency(open_prices, currency)

        # Restriction à la date de début et création d'un index quotidien complet
        open_prices_filtered = open_prices_converted.loc[self.__start_date:]
        full_date_range = pd.date_range(
            start=self.__start_date, 
            end=self.__end_date, 
            freq='D'
        )

        # Réindexation pour combler les trous (week-ends) et propagation des valeurs
        return open_prices_filtered.reindex(full_date_range).ffill().bfill()
    
    def __init_performance_structure(self) -> dict:
        """Initialise la structure des performances du portefeuille."""
        return {
            "tickers_invested_amounts": {},
            "tickers_performance": {},
            "tickers_gain": {},
            "tickers_valuation": {},
            "tickers_dividends": {},
            "tickers_pru": {},
            "portfolio_performance": pd.DataFrame(dtype=float),
            "portfolio_gain": pd.DataFrame(dtype=float),
            "portfolio_monthly_percentages": pd.DataFrame(dtype=float),
            "portfolio_valuation": pd.DataFrame(dtype=float),
            "portfolio_invested_amounts": pd.DataFrame(dtype=float),
            "portfolio_cash": pd.DataFrame(dtype=float),
            "portfolio_fees": pd.DataFrame(dtype=float),
            "portfolio_dividends": pd.DataFrame(dtype=float),
            "portfolio_cagr": {},
            "portfolio_dividend_yield": {},
            "portfolio_dividend_earn": {},
        }

    def __init_tickers_structure(self) -> dict:
        """Initialise la structure des performances par ticker."""
        return {
            "tickers_invested_amounts": {},
            "tickers_performance": {},
            "tickers_gain": {},
            "tickers_valuation": {},
            "tickers_dividends": {},
            "tickers_pru": {},
        }
