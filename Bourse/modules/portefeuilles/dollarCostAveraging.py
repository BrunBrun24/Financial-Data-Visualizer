from .basePortefeuille import BasePortefeuille

import pandas as pd
from datetime import datetime

class DollarCostAveraging(BasePortefeuille):
    
    def DCA(self):
        """
        Cette méthode permet de simuler un investissement en Dollar Cost Average (DCA) en fonction de différents portefeuilles.

        Explication:
            L’investissement en DCA (Dollar-Cost Averaging) est une stratégie simple mais efficace,
            qui consiste à investir régulièrement des montants fixes dans un actif financier, indépendamment de son prix.
            Plutôt que d'essayer de deviner le meilleur moment pour investir, le DCA permet d'acheter des parts de façon continue,
            réduisant l'impact des fluctuations du marché.
        """

        prixTickers = self.prixTickers.copy()
        datesInvestissements = self.DatesInvesissementDCA_DCV()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + f" DCA"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]
            datesInvestissementsPrix = {date: (self.ArgentInitialementInvesti()/len(datesInvestissements)) for date in datesInvestissements}

            montantsInvestisTickers, montantsInvestisCumules = self.CalculerPrixMoyenPondereAchatDollarCostAveraging(datesInvestissementsPrix, prixTickersFiltree, portfolio[0])

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
            self.cash[nomPortefeuille] = pd.Series(0.0, index=prixTickers.index, dtype=float)

    @staticmethod
    def CalculerPrixMoyenPondereAchatDollarCostAveraging(datesInvestissementsPrix: dict, prixTickers: pd.DataFrame, tickerPourcentages: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat en utilisant la méthode Dollar Cost Averaging.

        Args:
            datesInvestissementsPrix (dict): Un dictionnaire où les clés sont des dates (datetime) et les valeurs sont des montants investis (int ou float).
            prixTickers (pd.DataFrame): Un DataFrame contenant les prix des tickers avec les dates en index et les tickers en colonnes.
            tickerPourcentages (dict): Un dictionnaire où les clés sont des tickers et les valeurs sont les pourcentages du portefeuille alloués à chaque ticker.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: Un tuple contenant deux DataFrames :
                - Le premier DataFrame représente les montants investis pour chaque ticker à chaque date.
                - Le deuxième DataFrame représente les montants investis cumulés pour chaque ticker à chaque date.
        """
        assert isinstance(datesInvestissementsPrix, dict), "datesInvestissementsPrix doit être un dictionnaire."
        assert all(isinstance(date, datetime) for date in datesInvestissementsPrix.keys()), "Les clés de datesInvestissementsPrix doivent être des instances datetime."
        assert all(isinstance(montant, (int, float)) for montant in datesInvestissementsPrix.values()), "Les valeurs de datesInvestissementsPrix doivent être des nombres (int ou float)."

        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."
        assert isinstance(tickerPourcentages, dict), "tickerPourcentages doit être un dictionnaire."

        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for date, montant in datesInvestissementsPrix.items():
            if date in prixTickers.index:  # Vérifier si la date est dans le DataFrame des prix
                for ticker in prixTickers.columns:
                    ajouterArgentTicker = (montant * tickerPourcentages[ticker] / 100)
                    montantsInvestis.at[date, ticker] = ajouterArgentTicker

        montantsInvestisCumules = montantsInvestis.cumsum()
        return montantsInvestis, montantsInvestisCumules

    def DatesInvesissementDCA_DCV(self) -> list:
        """
        Extrait les dates de début de chaque mois dans la plage donnée entre startDate et endDate.

        Returns:
            list: Liste des dates de début de chaque mois sous forme de chaînes formatées 'YYYY-MM-DD'.
        """
        
        startDate = self.startDate
        endDate = self.endDate

        # Initialisation de la liste pour stocker les dates de début de chaque mois
        debutMois = []
        currentDate = startDate

        while currentDate <= endDate:
            # Ajouter la date de début du mois formatée
            debutMois.append(currentDate)

            # Passer au mois suivant
            next_month = currentDate.month % 12 + 1
            next_year = currentDate.year + (currentDate.month // 12)
            currentDate = currentDate.replace(month=next_month, year=next_year, day=1)

        return sorted(debutMois)
    
    