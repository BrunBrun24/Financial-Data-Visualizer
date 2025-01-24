from .basePortefeuille import BasePortefeuille

import pandas as pd
from datetime import datetime, timedelta

class MoyenneMobile(BasePortefeuille):

    ########## MovingAveragePullbackStrategyUP ##########
    def MovingAveragePullbackStrategyUP(self, nbJourSMA: int):
        """
        Stratégie d'investissement basée sur un repli sur moyenne mobile (Moving Average Pullback Strategy).
        
        Explication:
            La méthode vérifie les prix d'un ou plusieurs actifs sur une période donnée et achète les actifs lorsque le prix 
            touche la moyenne mobile définie par le nombre de jours spécifié (`nbJourSMA`). La stratégie consiste à acheter
            lorsque le prix descend et touche ou croise la moyenne mobile par le bas, indiquant un potentiel repli avant une reprise haussière.

        Args:
            nbJourSMA (int): Le nombre de jours utilisé pour calculer la moyenne mobile simple (SMA).
        """
        assert isinstance(nbJourSMA, int), "nbJourSMA doit être un entier"

        prixTickers = self.prixTickers.copy()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + f" SMA {nbJourSMA}"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            datesInvestissementsTickers = self.DatesInvesissementSMA_Up(self.startDate, self.endDate, tickers, prixTickers, nbJourSMA)

            montantsInvestisTickers, montantsInvestisCumules, datesInvestissementsPrix, cash = self.CalculerPrixMoyenPondereAchatSmaUp(datesInvestissementsTickers, prixTickersFiltree, portfolio[0], (self.ArgentInitialementInvesti()/len(self.DatesInvesissementDCA_DCV())))

            # Calcul des montants
            evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.CalculerPlusMoinsValueCompose(montantsInvestisTickers, prixTickersFiltree)
            evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
            evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1)

            # Calcul des pourcentages
            evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
            evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesPortefeuille, montantsInvestisCumules.iloc[-1].sum())

            # On stock les DataFrames
            self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
            self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
            self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
            self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
            self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
            self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, prixTickersFiltree)
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, datesInvestissementsPrix, {})
            self.prixFifoTickers[nomPortefeuille] = self.CalculerPrixFifoTickers(montantsInvestisTickers)
            self.fondsInvestisTickers[nomPortefeuille] = montantsInvestisCumules
            self.montantsInvestisTickers[nomPortefeuille] = montantsInvestisTickers
            self.montantsVentesTickers[nomPortefeuille] = pd.DataFrame(index=prixTickersFiltree.index, columns=prixTickersFiltree.columns, dtype=float)
            self.soldeCompteBancaire[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
            self.cash[nomPortefeuille] = cash

    def DatesInvesissementSMA_Up(self, startDate: datetime, endDate: datetime, tickers: list, tickerPriceDf: pd.DataFrame, nbJourSMA: int) -> dict:
        """
        Calcule les dates d'investissement pour chaque ticker, en fonction du croisement du prix de l'action avec la moyenne mobile lorsque ce dernier descend en dessous de celle-ci.

        Args:
            startDate (datetime): Date de début de l'analyse.
            endDate (datetime): Date de fin de l'analyse.
            tickers (list): Liste des tickers à analyser.
            tickerPriceDf (pd.DataFrame): DataFrame des prix des tickers, indexé par date.
            nbJourSMA (int): Période pour le calcul de la moyenne mobile simple (SMA).

        Returns:
            dict: Dictionnaire avec les tickers comme clés et les listes de dates d'investissement comme valeurs.
        """
        # Vérification des dates
        assert isinstance(startDate, datetime), "startDate doit être  un objet datetime"
        assert isinstance(endDate, datetime), "endDate doit être un objet datetime"

        # Vérification du type de tickers
        assert isinstance(tickers, list), "tickers doit être une liste."
        assert all(isinstance(ticker, str) for ticker in tickers), "Chaque élément dans tickers doit être une chaîne de caractères."

        # Vérification de tickerPriceDf
        assert isinstance(tickerPriceDf, pd.DataFrame), "tickerPriceDf doit être un DataFrame pandas."
        assert all(ticker in tickerPriceDf.columns for ticker in tickers), "Tous les tickers doivent être des colonnes dans tickerPriceDf."
        assert isinstance(tickerPriceDf.index, pd.DatetimeIndex), "Les index de tickerPriceDf doivent être de type DatetimeIndex."

        # Vérification de nbJourSMA
        assert isinstance(nbJourSMA, int), "nbJourSMA doit être un entier (int)."

        # Conversion en format datetime si nécessaire
        startDate = pd.to_datetime(startDate)
        endDate = pd.to_datetime(endDate)

        datesInvestissements = {}
        smaDf = self.DownloadTickersSMA((startDate - timedelta(nbJourSMA + 50)), endDate, tickers, [nbJourSMA])
        smaDf = smaDf.loc[startDate:endDate].fillna(0)

        # Calcul de la moyenne mobile pour chaque ticker et détection des dates d'investissement
        for ticker in tickers:
            datesInvestissements[ticker] = []
            # Filtrage des données sur la plage de dates donnée
            prixTickers = tickerPriceDf[ticker].loc[startDate:endDate]

            nomColonne = f"{ticker}_SMA_{nbJourSMA}"

            # Détection des dates où le prix touche ou passe sous la moyenne mobile
            for date in prixTickers.index[1:]:  # On démarre à partir de la deuxième date
                if (prixTickers[date] <= smaDf.loc[date, nomColonne]) and (prixTickers[date - pd.Timedelta(days=1)] > smaDf.loc[date - pd.Timedelta(days=1), nomColonne]):
                    datesInvestissements[ticker].append(date)

        return datesInvestissements

    def CalculerPrixMoyenPondereAchatSmaUp(self, datesInvestissementsTickers: dict, prixTickers: pd.DataFrame, tickerPourcentages: dict, montantInvestirChaqueMois: int|float) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        """
        Calcule les montants investis pour chaque ticker à chaque date d'investissement en répartissant un montant mensuel global
        selon des pourcentages définis. Gère également les montants non investis d'un mois à l'autre, qui sont accumulés.

        Args:
            datesInvestissementsTickers (dict): 
                Dictionnaire où chaque clé est un ticker (str) et chaque valeur est une liste de dates (datetime) 
                représentant les dates prévues d'investissement pour ce ticker.
                Exemple : {'AAPL': [datetime(2023, 1, 15), datetime(2023, 3, 1)]}.

            prixTickers (pd.DataFrame): 
                DataFrame contenant les prix des tickers, indexé par date (datetime).
                Les colonnes représentent les tickers, et les lignes représentent les prix à chaque date.

            tickerPourcentages (dict): 
                Dictionnaire où les clés sont les tickers (str), et les valeurs sont les pourcentages (float ou int) 
                du montant mensuel à allouer à chaque ticker.
                Exemple : {'AAPL': 50.0, 'MSFT': 50.0}.

            montantInvestirChaqueMois (int | float): 
                Montant total à investir chaque mois. Ce montant sera réparti entre les tickers 
                selon les pourcentages spécifiés dans `tickerPourcentages`.

        Returns:
            tuple: 
                - pd.DataFrame: DataFrame contenant les montants investis par ticker à chaque date d'investissement.
                Les dates sont en index, et les tickers en colonnes.
                - pd.DataFrame: DataFrame des investissements cumulés au fil du temps, avec les mêmes dimensions que le premier DataFrame.
                - dict: Dictionnaire où chaque clé est une date d'investissement (datetime), et la valeur est le montant total 
                investi à cette date (somme des investissements pour tous les tickers).
                - pd.Series: Série représentant le cash accumulé (montants non investis) restant à chaque date, indexé par date.
        """
            
        # Validation des types des entrées
        assert isinstance(datesInvestissementsTickers, dict), "datesInvestissements doit être un dictionnaire."
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."
        assert isinstance(tickerPourcentages, dict), "tickerPourcentages doit être un dictionnaire."
        assert isinstance(montantInvestirChaqueMois, (int, float)), "montantInvestirChaqueMois doit être un entier ou un flottant."

        # Initialisation des DataFrame
        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)
        cash = pd.Series(0.0, index=prixTickers.index, dtype=float)
        datesInvestissementsPrix = {}

        # Liste des tickers
        tickers = [ticker for ticker in datesInvestissementsTickers.keys()]

        # Calcul du montant à investir par ticker
        montantInvestirTickers = {}
        for ticker in tickers:
            montantInvestirTickers[ticker] = (montantInvestirChaqueMois * tickerPourcentages[ticker] / 100)

        # Montant en attente pour chaque ticker
        montantEnAttente = {ticker: 0 for ticker in tickers}

        # Itération sur chaque ticker
        for ticker in tickers:
            # Trie les dates du ticker de la plus ancienne à la plus récente
            datesTicker = sorted(datesInvestissementsTickers[ticker])
            ancienneDate = self.startDate

            # Itération sur les dates de chaque ticker
            for date in datesTicker:
                nbMoisDifference = ((date.year - ancienneDate.year) * 12 + (date.month - ancienneDate.month))
                # Si une nouvelle année ou mois arrive, ajouter le montant prévu
                if nbMoisDifference > 0:
                    # Ajoute le montant à investir pour le ticker (accumule si pas d'investissement précédent)
                    montantEnAttente[ticker] += (montantInvestirTickers[ticker] * nbMoisDifference)
                    cash.loc[date:] += (montantInvestirTickers[ticker] * nbMoisDifference)

                if montantEnAttente[ticker] > 0:
                    # Enregistrer l'investissement du mois actuel
                    montantsInvestis.at[date, ticker] = montantEnAttente[ticker]

                    # Ajoute la date et le prix dans datesInvestissementsPrix
                    if date in datesInvestissementsPrix:
                        datesInvestissementsPrix[date] += montantEnAttente[ticker]
                    else:
                        datesInvestissementsPrix[date] = montantEnAttente[ticker]

                    # Réinitialiser le montant en attente après l'investissement
                    cash.loc[date:] -= montantEnAttente[ticker]
                    montantEnAttente[ticker] = 0

                # Mettre à jour ancienneDate
                ancienneDate = date

            # Calcule l'argent en attente restant
            dateActuel = datetime.today()
            nbMoisDifference = ((dateActuel.year - ancienneDate.year) * 12 + (dateActuel.month - ancienneDate.month))
            montantEnAttente[ticker] = (montantInvestirTickers[ticker] * nbMoisDifference)

        return montantsInvestis, montantsInvestis.cumsum(), datesInvestissementsPrix, cash
    #####################################################

    ########## MovingAveragePullbackStrategy ##########
    def MovingAveragePullbackStrategy(self):
        """
        Stratégie d'investissement basée sur la moyenne mobile (SMA).

        Explication:
            La méthode implémente une stratégie qui vérifie le croisement de deux moyennes mobiles simples (SMA 25 et SMA 50).
            L'objectif est d'acheter des actifs lorsque la SMA 25 croise la SMA 50 par le dessus, signalant un potentiel changement de tendance. 
            Une fois ce croisement détecté, la stratégie continue d'acheter tous les 10 jours si la SMA 25 reste en dessous de la SMA 50 et 
            au-dessus du prix de l'action. Cela indique une opportunité d'achat pendant une correction de prix.
        """

        prixTickers = self.prixTickers.copy()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + f" SMA 25 et SMA 50"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            datesInvestissementsTickers = self.DatesInvesissementSMA(self.startDate, self.endDate, tickers, prixTickers)

            montantsInvestisTickers, montantsInvestisCumules, datesInvestissementsPrix, cash = self.CalculerPrixMoyenPondereAchatSmaUp(datesInvestissementsTickers, prixTickersFiltree, portfolio[0], (self.ArgentInitialementInvesti()/len(self.DatesInvesissementDCA_DCV())))

            # Calcul des montants
            evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.CalculerPlusMoinsValueCompose(montantsInvestisTickers, prixTickersFiltree)
            evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
            evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1)

            # Calcul des pourcentages
            evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
            evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesPortefeuille, montantsInvestisCumules.iloc[-1].sum())

            # On stock les DataFrames
            self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
            self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
            self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
            self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
            self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
            self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, prixTickersFiltree)
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, datesInvestissementsPrix, {})
            self.prixFifoTickers[nomPortefeuille] = self.CalculerPrixFifoTickers(montantsInvestisTickers)
            self.fondsInvestisTickers[nomPortefeuille] = montantsInvestisCumules
            self.montantsInvestisTickers[nomPortefeuille] = montantsInvestisTickers
            self.montantsVentesTickers[nomPortefeuille] = pd.DataFrame(index=prixTickersFiltree.index, columns=prixTickersFiltree.columns, dtype=float)
            self.soldeCompteBancaire[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
            self.cash[nomPortefeuille] = cash

    def DatesInvesissementSMA(self, startDate: datetime, endDate: datetime, tickers: list, tickerPriceDf: pd.DataFrame) -> dict:
        """
        Calcule les dates d'investissement pour chaque ticker, basées sur le croisement des moyennes mobiles.
        Acheter quand SMA 25 touche SMA 50 par le dessus et par la suite si SMA 25 reste en dessous de SMA 50 et au dessus du prix de l'action alors acheter tous les 10 jours.

        Args:
            startDate (datetime): Date de début de l'analyse.
            endDate (datetime): Date de fin de l'analyse.
            tickers (list): Liste des tickers à analyser.
            tickerPriceDf (pd.DataFrame): DataFrame des prix des tickers, indexé par date.

        Returns:
            dict: Dictionnaire avec les tickers comme clés et les listes de dates d'investissement comme valeurs.
        """
        # Vérification des dates
        assert isinstance(startDate, datetime), "startDate doit être  un objet datetime"
        assert isinstance(endDate, datetime), "endDate doit être un objet datetime"

        # Vérification du type de tickers
        assert isinstance(tickers, list), "tickers doit être une liste."
        assert all(isinstance(ticker, str) for ticker in tickers), "Chaque élément dans tickers doit être une chaîne de caractères."

        # Vérification de tickerPriceDf
        assert isinstance(tickerPriceDf, pd.DataFrame), "tickerPriceDf doit être un DataFrame pandas."
        assert all(ticker in tickerPriceDf.columns for ticker in tickers), "Tous les tickers doivent être des colonnes dans tickerPriceDf."
        assert isinstance(tickerPriceDf.index, pd.DatetimeIndex), "Les index de tickerPriceDf doivent être de type DatetimeIndex."

        # Conversion en format datetime si nécessaire
        startDate = pd.to_datetime(startDate)
        endDate = pd.to_datetime(endDate)

        datesInvestissements = {}
        smaDf = self.DownloadTickersSMA(startDate, endDate, tickers, [25, 50])

        # Calcul de la moyenne mobile pour chaque ticker et détection des dates d'investissement
        for ticker in tickers:
            datesInvestissements[ticker] = []
            # Filtrage des données sur la plage de dates donnée
            prixTickers = tickerPriceDf[ticker].loc[startDate:endDate]
            dureeDernierInvestissementJour = 0

            # Détection des dates où le prix touche ou passe sous la moyenne mobile
            for date in prixTickers.index[1:]:
                prixTickerAujourdhui = prixTickers.loc[date]

                sma25Aujourdhui = smaDf.loc[date, f"{ticker}_SMA_25"]
                sma25Hier = smaDf.loc[(date - pd.Timedelta(days=1)), f"{ticker}_SMA_25"]
                sma50Aujourdhui = smaDf.loc[date, f"{ticker}_SMA_50"]
                sma50Hier = smaDf.loc[(date - pd.Timedelta(days=1)), f"{ticker}_SMA_50"]

                # Détection des dates où le prix de SMA 25 touche ou passe sous SMA 50
                if (sma25Aujourdhui <= sma50Aujourdhui) and (sma25Hier > sma50Hier):
                    if ((prixTickerAujourdhui < sma25Aujourdhui) and (prixTickerAujourdhui < sma50Aujourdhui)):
                        datesInvestissements[ticker].append(date)

                if (sma25Aujourdhui <= sma50Aujourdhui):
                    dureeDernierInvestissementJour += 1
                    if (prixTickerAujourdhui < sma25Aujourdhui) and (dureeDernierInvestissementJour > 10):
                        datesInvestissements[ticker].append(date)
                        dureeDernierInvestissementJour = 0
                else:
                    dureeDernierInvestissementJour = 0
                
        return datesInvestissements
    #########################

