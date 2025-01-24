from .basePortefeuille import BasePortefeuille

import pandas as pd

class LumpSumInvesting(BasePortefeuille):

    def LumpSum(self):
        """
        Simule un investissement unique (Lump Sum Investing) sur plusieurs portefeuilles, répartis sur différentes plages de dates.

        Explication:
            L’investissement unique, ou Lump Sum Investing, consiste à investir un montant fixe en une seule fois, au lieu de le répartir
            sur plusieurs périodes. Cette méthode permet de visualiser la croissance et les performances d’un ou plusieurs portefeuilles
            sur des périodes de temps définies. Les portefeuilles contiennent des actifs et leurs pourcentages, et sont suivis sur
            différentes plages de dates pour observer l'évolution.
        """

        prixTickers = self.prixTickers.copy()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1]
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]
            datesInvestissementsPrix = {self.startDate: portfolio[1]}

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
    
    