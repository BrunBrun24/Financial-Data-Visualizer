from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from database.trade_republic_database import TradeRepublicDatabase


class PortfolioEngine:
    """
    Classe complète pour le calcul des performances, des flux et des métriques
    d'un portefeuille d'investissement.
    
    Fournit les outils mathématiques pour l'analyse de rentabilité (CAGR),
    de risque (Sharpe, Drawdown) et de gestion de trésorerie.
    """

    def __init__(self, start_date: datetime, end_date: datetime):
        """
        Initialise le moteur avec la période d'analyse définie.

        Args:
            - start_date (datetime) : Date de début de l'analyse.
            - end_date (datetime) : Date de fin de l'analyse.
        """
        self.__start_date = start_date
        self.__end_date = end_date


    # --- [ Analyse de Performance ] ---
    @staticmethod
    def _calculate_monthly_percentage_change(portfolio_series: pd.Series, transactions_df: pd.DataFrame) -> pd.Series:
        """
        Calcule l'évolution mensuelle en pourcentage du portefeuille.
        Ajuste les apports selon qu'il s'agisse d'une stratégie active ou passive.

        Args:
            - portfolio_series (pd.Series) : Valeur quotidienne du portefeuille.
            - transactions_df (pd.DataFrame) : Historique des transactions.

        Returns:
            - pd.Series : Série mensuelle d'évolution en pourcentage.
        """
        portfolio_series.index = pd.to_datetime(portfolio_series.index)
        transactions_df = transactions_df.copy()
        transactions_df.index = pd.to_datetime(transactions_df.index)

        # Nettoyage des données (suppression des valeurs nulles ou négatives)
        portfolio_series = portfolio_series[portfolio_series > 0].dropna()
        monthly_start = portfolio_series.resample("ME").first()
        monthly_end = portfolio_series.resample("ME").last()
        
        has_sales = "sell" in transactions_df["operation"].unique()

        if has_sales:
            monthly_returns = pd.Series(index=monthly_start.index, dtype=float)
            is_first_month = True

            for date in monthly_start.index:
                month_start = date.replace(day=1)
                month_end = month_start + pd.offsets.MonthEnd(0)

                # Extraction des achats nets sur la période
                buys = transactions_df.loc[
                    (transactions_df["operation"] == "buy") &
                    (transactions_df.index >= month_start) &
                    (transactions_df.index <= month_end)
                ].copy()
                
                # Conversion explicite pour éviter les erreurs de type
                buys["amount"] = buys["amount"].astype(float)
                buys["fees"] = buys["fees"].astype(float)
                
                monthly_net_buy = (buys["amount"] - buys["fees"]).sum()
                
                # Correction pour le tout premier mois si des achats initiaux existent
                if is_first_month and not buys.empty:
                    monthly_net_buy -= buys["amount"].iloc[0]
                    is_first_month = False

                # Extraction des ventes sur la période
                sells = transactions_df.loc[
                    (transactions_df["operation"] == "sell") &
                    (transactions_df.index >= month_start) &
                    (transactions_df.index <= month_end)
                ].copy()
                monthly_net_sell = sells["amount"].astype(float).sum()

                start_val = monthly_start.get(date)
                end_val = monthly_end.get(date)

                # Calcul du rendement ajusté des flux de trésorerie (performance approximé)
                if pd.isna(start_val) or (start_val + monthly_net_buy) == 0:
                    monthly_returns[date] = float("nan")
                else:
                    monthly_returns[date] = ((end_val / (start_val + monthly_net_buy - monthly_net_sell)) - 1) * 100
            return monthly_returns
        else:
            # Calcul simple si aucune vente n'a eu lieu
            return ((monthly_end - monthly_start) / monthly_start) * 100

    @staticmethod
    def _calculate_portfolio_percentage_change(portfolio_pnl_evolution: pd.Series, invested_money: float) -> pd.DataFrame:
        """
        Calcule l'évolution globale en pourcentage par rapport au capital investi.

        Args:
            - portfolio_pnl_evolution (pd.Series) : Évolution du PnL (Profit and Loss) du portefeuille.
            - invested_money (float) : Capital total investi.

        Returns:
            - pd.DataFrame : DataFrame contenant une colonne 'PercentageChange'.
        """
        assert isinstance(portfolio_pnl_evolution, pd.Series)
        change = round((((invested_money + portfolio_pnl_evolution) - invested_money) / invested_money) * 100, 2)
        return pd.DataFrame(change, columns=['PercentageChange'])

    @staticmethod
    def _capital_gain_losses_composed(tickers_invested: pd.DataFrame, tickers_pru: pd.DataFrame, tickers_prices: pd.DataFrame) -> tuple:
        """
        Calcule la valorisation actuelle, le pourcentage de gain et le gain absolu par actif.

        Args:
            - tickers_invested (pd.DataFrame) : Montant total investi par ticker.
            - tickers_pru (pd.DataFrame) : Prix de Revient Unitaire (PRU) par ticker.
            - tickers_prices (pd.DataFrame) : Prix actuels du marché par ticker.

        Returns:
            - tuple : (valuation: pd.DataFrame, gain_pct: pd.DataFrame, gain_abs: pd.DataFrame).
        """
        # Calcul du pourcentage de variation par rapport au PRU
        gain_pct = (tickers_prices - tickers_pru) / tickers_pru * 100
        
        # Calcul de la valorisation totale
        valuation = (tickers_invested * ((gain_pct / 100) + 1))
        
        # Calcul du gain en valeur absolue (Latent)
        gain_abs = (valuation - tickers_invested)
        return valuation, gain_pct, gain_abs

    def _calculate_portfolio_cagr(self, valuation: pd.Series, invested: pd.Series, horizons_days=(1, 2, 3, 5, 10)) -> dict:
        """
        Calcule le Taux de Croissance Annuel Composé (CAGR) sur plusieurs horizons.

        Args:
            - valuation (pd.Series) : Série de la valorisation.
            - invested (pd.Series) : Série du capital investi.
            - horizons_days (tuple) : Liste des durées en années pour le calcul.

        Returns:
            - dict : CAGR par horizon temporel (clé 'all' pour la durée totale).
        """
        # Alignement sur la première donnée non nulle
        val = valuation.loc[valuation.ne(0).idxmax():]
        inv = invested.loc[invested.ne(0).idxmax():]
        res = {}
        
        for d in horizons_days:
            # Vérification de la disponibilité des données (365 jours * années)
            if len(val.index) < (365 * d):
                res[d] = None
            else:
                # Formule : (Valeur Finale / Valeur Initiale)^(1/n) - 1
                res[d] = round(((val.iloc[-1] / inv.iloc[-(365 * d)]) ** (1 / d) - 1) * 100, 2)
        
        # Calcul sur la durée totale disponible
        total_yrs = len(val.index) / 365
        res["all"] = round(((val.iloc[-1] / inv.iloc[0]) ** (1 / total_yrs) - 1) * 100, 2)
        return res


    # --- [ Analyse des Flux & Cash ] ---
    def _compute_cash_evolution(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les flux journaliers et le cumul de la trésorerie (Cash).

        Args:
            - transactions_df (pd.DataFrame) : DataFrame des transactions.

        Returns:
            - pd.DataFrame : Évolution du cash (colonnes 'cash_flow' et 'cash_cumulative').
        """
        def __calculate_flow(row):
            # Détermination du sens du flux de trésorerie selon l'opération
            op, amt, fee = row['operation'], row['amount'], row['fees']
            if op == 'buy':
                return -(amt + fee)
            elif op == 'sell':
                return amt - fee
            elif op in ['deposit', 'dividend', 'interest']:
                return (amt - fee)
            elif op == 'withdrawal':
                return -amt
            return 0

        transactions_df.index = pd.to_datetime(transactions_df.index)
        transactions_df['cash_flow'] = transactions_df.apply(__calculate_flow, axis=1)

        # Agrégation par date et réindexation sur la période complète
        cash_by_date = transactions_df['cash_flow'].groupby(transactions_df.index).sum()
        full_index = pd.date_range(start=self.__start_date, end=self.__end_date, freq='D')
        cash_by_date = cash_by_date.reindex(full_index, fill_value=0)

        return pd.DataFrame({
            'cash_flow': cash_by_date,
            'cash_cumulative': cash_by_date.cumsum()
        }).rename_axis('index')

    def _initial_invested_amount(self, transactions_df: pd.DataFrame, ticker_invested_amounts: pd.DataFrame) -> float:
        """
        Calcule le capital extérieur net réellement injecté dans le portefeuille.
        Distingue l'argent frais du réinvestissement des ventes.

        Args:
            - transactions_df (pd.DataFrame) : Transactions.
            - ticker_invested_amounts (pd.DataFrame) : Évolution des montants investis par ticker.

        Returns:
            - float : Montant total net injecté.
        """
        tx = transactions_df.copy()
        tx.index = pd.to_datetime(tx.index)
        tx.sort_index(inplace=True)

        available_cash, money_reinvested, invested_cash = 0.0, 0.0, 0.0

        for date, row in tx.iterrows():
            ticker, amt, fees = row["ticker"], float(row["amount"]), float(row["fees"])
            
            if row["operation"] == "sell":
                # Gestion du réinvestissement vs cash disponible
                prev_date = date - timedelta(days=1)
                if ticker in ticker_invested_amounts.columns and prev_date in ticker_invested_amounts.index:
                    if amt > ticker_invested_amounts.loc[prev_date, ticker]:
                        money_reinvested += ticker_invested_amounts.loc[prev_date, ticker]
                available_cash += (amt - fees)
            
            elif row["operation"] == "buy":
                cost = amt + fees
                if available_cash >= cost:
                    # Utilisation du cash issu des ventes/dividendes
                    available_cash -= cost
                else:
                    # Injection de nouvel argent frais
                    invested_cash += (cost - available_cash)
                    available_cash = 0.0
                
                if money_reinvested >= cost:
                    money_reinvested -= cost

        return (invested_cash + money_reinvested)

    def _tickers_investment_amount_evolution(self, transaction_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution quotidienne du montant investi par ticker.

        Args:
            - transaction_df (pd.DataFrame) : DataFrame des transactions.

        Returns:
            - pd.DataFrame : Montants investis quotidiennement par ticker.
        """
        tickers = transaction_df["ticker"].dropna().unique()
        date_range = pd.date_range(self.__start_date, self.__end_date)
        invested = pd.DataFrame(0.0, index=date_range, columns=tickers)

        for ticker in tickers:
            ops = transaction_df[
                (transaction_df["ticker"] == ticker) & 
                (transaction_df["operation"].isin(["buy", "sell"]))
            ]
            qty_tracker = 0

            # Itération sur chaque transaction pour mettre à jour l'encours
            for date, data in ops.iterrows():
                if data["operation"] == "buy":
                    invested.loc[date:, ticker] += data["amount"]
                    qty_tracker += data["quantity"]
                elif data["operation"] == "sell":
                    if round(qty_tracker, 6) > round(data["quantity"], 6):
                        # Vente partielle : réduction proportionnelle
                        new_amt = invested.loc[date, ticker] - data["amount"]
                        invested.loc[date:, ticker] = max(new_amt, 0.0)
                        qty_tracker -= data["quantity"]
                    else:
                        # Vente totale
                        invested.loc[date:, ticker] = 0.0
                        qty_tracker = 0
        return invested

    def _compute_plus_value_evolution(self, transactions_df: pd.DataFrame, ticker_invested_amounts: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution de la plus-value réalisée (Realized PnL), plafonnée à 0.

        Args:
            - transactions_df (pd.DataFrame) : Transactions.
            - ticker_invested_amounts (pd.DataFrame) : Montants investis par ticker.

        Returns:
            - pd.DataFrame : Flux et cumul de plus-value.
        """
        def __calc_pv(row):
            if row['operation'] == 'sell':
                prev_date = row.name - timedelta(days=1)
                ticker = row['ticker']
                if ticker in ticker_invested_amounts.columns and prev_date in ticker_invested_amounts.index:
                    return row['amount'] - ticker_invested_amounts.loc[prev_date, ticker]
            return 0

        transactions_df.index = pd.to_datetime(transactions_df.index)
        transactions_df['plus_value_flow'] = transactions_df.apply(__calc_pv, axis=1)

        pv_by_date = transactions_df['plus_value_flow'].groupby(transactions_df.index).sum()
        full_index = pd.date_range(start=self.__start_date, end=self.__end_date, freq='D')
        pv_by_date = pv_by_date.reindex(full_index, fill_value=0)

        # Calcul du cumul avec un plancher à zéro
        pv_cumulative = []
        current_sum = 0
        for val in pv_by_date:
            current_sum = max(current_sum + val, 0)
            pv_cumulative.append(current_sum)

        return pd.DataFrame({'plus_value_flow': pv_by_date.values, 'plus_value_cumulative': pv_cumulative}, index=full_index)


    # --- [ Analyse du Risque ] ---
    @staticmethod
    def _calculate_portfolio_sharpe_ratio(valuation: pd.Series, risk_free_rate: float = 0.025, periods: str='annuel') -> float:
        """
        Calcule le ratio de Sharpe pour évaluer la performance ajustée au risque.

        Args:
            - valuation (pd.Series) : Série temporelle de la valorisation du portefeuille.
            - risk_free_rate (float) : Taux sans risque annuel (défaut: 0.025).
            - periods (str) : Fréquence des données ('journalier', 'mensuel', 'annuel').

        Returns:
            - float : Ratio de Sharpe arrondi.
        """
        val = valuation.loc[valuation.ne(0).idxmax():]
        if periods == 'journalier':
            rets, scale = val.pct_change().dropna(), 252
        elif periods == 'mensuel':
            rets, scale = val.resample('ME').ffill().pct_change().dropna(), 12
        else:
            rets, scale = val.resample('YE').ffill().pct_change().dropna(), 1
        
        ann_ret = rets.mean() * scale
        ann_vol = rets.std() * (scale ** 0.5)
        return round((ann_ret - risk_free_rate) / ann_vol, 2)

    @staticmethod
    def _calculate_portfolio_sortino_ratio(valuation: pd.Series, risk_free_rate: float = 0.025, periods_per_year: int = 252) -> float:
        """
        Calcule le ratio de Sortino pour évaluer la performance ajustée au risque de baisse uniquement.

        Args:
            - valuation (pd.Series) : Série de la valorisation du portefeuille.
            - risk_free_rate (float) : Taux sans risque annuel (par défaut 0.025).
            - periods_per_year (int) : Nombre de périodes par an (252 pour base journalière).

        Returns:
            - float : Ratio de Sortino ou NaN si données insuffisantes.
        """
        val = valuation.loc[valuation.ne(0).idxmax():]
        rets = val.pct_change().dropna()
        if rets.empty:
            return np.nan
        
        rf_p = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
        excess = rets - rf_p
        neg = excess[excess < 0]
        
        if neg.empty:
            return np.nan
        
        dd_dev = np.sqrt(np.mean(neg ** 2))
        return round(float((excess.mean() / dd_dev) * np.sqrt(periods_per_year)), 2)

    @staticmethod
    def _calculate_ecart_type(valuation_series: pd.Series) -> float:
        """
        Calcule la volatilité historique (écart-type) des rendements quotidiens.

        Args:
            - valuation_series (pd.Series) : Série de la valorisation du portefeuille.

        Returns:
            - float : Écart-type des rendements exprimé en pourcentage.
        """
        val = valuation_series.loc[valuation_series.ne(0).idxmax():]
        return round(val.pct_change().dropna().std() * 100, 2)
    
    @staticmethod
    def _calculer_drawdown_max(valuation: pd.Series) -> dict:
        """
        Calcule le drawdown maximal historique (baisse maximale du sommet au creux).

        Args:
            - valuation (pd.Series) : Série de la valorisation.

        Returns:
            - dict : Dictionnaire contenant la perte max, la date du pic et la date du creux.
        """
        val = valuation.loc[valuation.ne(0).idxmax():].dropna()
        peak = val.cummax()
        dd = (val / peak - 1.0) * 100
        
        dd_max = dd.min()
        date_dd = dd.idxmin()
        peak_date = val.loc[:date_dd][val.loc[:date_dd] == peak.loc[date_dd]].index[-1]
        
        return {
            "drawdown_max": round(dd_max, 2), 
            "date_max_before_drawdown": peak_date.date(), 
            "date_drawdown_max": date_dd.date()
        }

    @staticmethod
    def _calculer_drawdown_max_un_jour(valuation_series: pd.Series) -> list:
        """
        Identifie la pire perte subie sur une seule journée de bourse.

        Args:
            - valuation_series (pd.Series) : Série de la valorisation du portefeuille.

        Returns:
            - list : [perte maximale en %, date de l'événement].
        """
        val = valuation_series.loc[valuation_series.ne(0).idxmax():]
        returns = val.pct_change().dropna()
        
        if returns.empty:
            return [np.nan, None]

        # Recherche du rendement minimum journalier
        return [round(float(returns.min() * 100), 2), returns.idxmin()]


    # --- [ Gestion des Revenus & Frais ] ---
    def _compute_fees_evolution(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution quotidienne et cumulée des frais de transaction.

        Args:
            - transactions_df (pd.DataFrame) : DataFrame des transactions.

        Returns:
            - pd.DataFrame : Évolution des frais (colonnes 'daily_fees', 'cumulative_fees').
        """
        date_range = pd.date_range(start=self.__start_date, end=self.__end_date, freq='D')
        daily_fees = transactions_df['fees'].resample('D').sum().reindex(date_range, fill_value=0.0)
        
        fees_df = daily_fees.to_frame(name='daily_fees')
        fees_df['cumulative_fees'] = fees_df['daily_fees'].cumsum()
        return fees_df

    def _calculate_pru(self, transaction_df: pd.DataFrame, tickers_invested_amounts: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le Prix de Revient Unitaire (PRU) quotidien par actif.

        Args:
            - transaction_df (pd.DataFrame) : Historique des transactions.
            - tickers_invested_amounts (pd.DataFrame) : Évolution des montants investis.

        Returns:
            - pd.DataFrame : Historique quotidien du PRU par ticker.
        """
        buys = transaction_df[transaction_df["operation"] == "buy"].copy()
        date_range = pd.date_range(self.__start_date, self.__end_date, freq="D")
        tickers = buys["ticker"].unique()

        invested = pd.DataFrame(0.0, index=date_range, columns=tickers)
        qty = pd.DataFrame(0.0, index=date_range, columns=tickers)

        for (ticker, date), grp in buys.groupby(["ticker", buys.index]):
            amt = grp["amount"].sum()
            # Calcul du prix moyen pondéré
            avg_px = (grp["amount"] * grp["stock_price"]).sum() / amt
            invested.at[date, ticker] += amt
            qty.at[date, ticker] += amt / avg_px

        pru = (invested.cumsum() / qty.cumsum()).ffill()
        pru = pru.reindex_like(tickers_invested_amounts)
        
        # Nettoyage des valeurs si aucun montant n'est investi
        pru[tickers_invested_amounts == 0] = np.nan
        return pru

    def _calculate_dividends(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les dividendes nets perçus pour chaque ticker, organisés par date.

        Args:
            - transactions (pd.DataFrame) : Historique des transactions.

        Returns:
            - pd.DataFrame : Matrice quotidienne des dividendes nets par actif.
        """
        dividends_df = transactions[transactions["operation"] == "dividend"].copy()
        dividends_df.index = pd.to_datetime(dividends_df.index)

        tickers = dividends_df["ticker"].dropna().unique()
        date_range = pd.date_range(start=self.__start_date, end=self.__end_date)
        cash_amount = pd.DataFrame(0.0, index=date_range, columns=tickers)

        for date, row in dividends_df.iterrows():
            ticker = row["ticker"]
            # Calcul du net : Montant brut - Frais
            amount = float(row["amount"]) - float(row.get("fees", 0.0))
            if pd.notna(ticker) and date in cash_amount.index:
                cash_amount.at[date, ticker] += amount

        return cash_amount

    def _calculate_dividends_evolution(self, portfolio_valuation: pd.DataFrame, tickers_prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution pondérée des dividendes par rapport à la valorisation.

        Args:
            - portfolio_valuation (pd.DataFrame) : Valorisation par ticker.
            - tickers_prices (pd.DataFrame) : Prix par ticker.

        Returns:
            - pd.DataFrame : Évolution pondérée des dividendes.
        """
        tickers = list(portfolio_valuation.columns)
        # Appel statique à la base de données pour récupérer les dividendes bruts
        raw_divs = TradeRepublicDatabase._get_tickers_dividends_df(tickers, self.__start_date, self.__end_date)
        
        if raw_divs.empty:
            return pd.DataFrame(0.0, index=portfolio_valuation.index, columns=tickers)

        results = pd.DataFrame(0.0, index=portfolio_valuation.index, columns=tickers)
        for date in raw_divs.index:
            for ticker in raw_divs.columns:
                div = raw_divs.at[date, ticker]
                if pd.notna(div) and date in results.index:
                    # Pondération par le ratio de valorisation
                    results.at[date, ticker] += div * (portfolio_valuation.at[date, ticker] / tickers_prices.at[date, ticker])
        return results

    @staticmethod
    def _calculate_dividend_earn(transactions: pd.DataFrame) -> float:
        """
        Calcule le montant total cumulé des dividendes nets perçus.

        Args:
            - transactions (pd.DataFrame) : DataFrame des transactions.

        Returns:
            - float : Somme totale des dividendes nets.
        """
        mask = transactions["operation"] == "dividend"
        return (transactions.loc[mask, "amount"] - transactions.loc[mask, "fees"]).sum()

    @staticmethod
    def _calculate_dividend_yield(transactions_df: pd.DataFrame, final_valuation_series: pd.Series) -> float:
        """
        Calcule le rendement global du dividende (Yield) par rapport à la valorisation finale.

        Args:
            - transactions_df (pd.DataFrame) : DataFrame des transactions.
            - final_valuation_series (pd.Series) : Série de la valorisation pour référence finale.

        Returns:
            - float : Rendement du dividende en pourcentage.
        """
        divs = transactions_df[transactions_df["operation"] == "dividend"]
        total_income = (divs["amount"] - divs["fees"]).sum()
        
        # Division par la dernière valeur connue du portefeuille
        return round((total_income / final_valuation_series.iloc[-1]) * 100, 2)


    # --- [ Fonctions Utilitaires & Techniques ] ---
    def _download_tickers_sma(self, tickers: list, sma_periods: list) -> pd.DataFrame:
        """
        Calcule les moyennes mobiles simples (SMA) pour une liste de tickers.

        Args:
            - tickers (list) : Liste des symboles boursiers.
            - sma_periods (list) : Liste des périodes SMA (ex: [20, 50, 200]).

        Returns:
            - pd.DataFrame : DataFrame contenant les SMA calculées par ticker.
        """
        # Note : Suppose l'existence d'une méthode 'download_tickers_price' héritée ou injectée
        prices = self.download_tickers_price(tickers, (self.__start_date - timedelta(max(sma_periods) + 50)), self.__end_date)
        sma_df = pd.DataFrame()

        for num_days in sma_periods:
            rolling_mean = prices.rolling(window=num_days).mean()
            for col in rolling_mean.columns:
                sma_df[f"{col}_SMA_{num_days}"] = rolling_mean[col]
        return sma_df
