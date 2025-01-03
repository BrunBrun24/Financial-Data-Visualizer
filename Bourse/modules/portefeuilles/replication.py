from .basePortefeuille import BasePortefeuille

import pandas as pd


class Replication(BasePortefeuille):
    
    def __init__(self):
        super().__init__()
        
        
    def ReplicationDeMonPortefeuille(self):
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        prixTickers = self.prixTickers.copy()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " Réplication"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            montantsInvestis, montantsInvestisCumules = self.CalculerPrixMoyenPondereAchatReplicationDeMonPortefeuille(prixTickersFiltree, portfolio)

            # Calcul des montants
            evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.CalculerPlusMoinsValueCompose(montantsInvestis, prixTickersFiltree)
            evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
            evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1)

            # Calcul des pourcentages
            evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
            evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesPortefeuille, montantsInvestisCumules.iloc[-1].sum())

            # On stock les DataFrames
            self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
            self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
            self.fondsInvestis[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
            self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
            self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
            self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
            self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, prixTickersFiltree)
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), {})
            self.soldeCompteBancaire[nomPortefeuille] = (self.EvolutionDepotEspeces() + evolutionArgentsInvestisPortefeuille)

    def CalculerPrixMoyenPondereAchatReplicationDeMonPortefeuille(self, prixTickers: pd.DataFrame, portefeuille: list) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat en fonction des investissements et des ventes dans le portefeuille.
        Args:
            prixTickers (pd.DataFrame): DataFrame contenant les prix des tickers avec les dates en index.
            portefeuille (list): Liste de dictionnaires représentant la répartition des investissements par ticker.
        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: 
                - montantsInvestis (pd.DataFrame): DataFrame des montants investis par date et par ticker.
                - montantsInvestisCumules (pd.DataFrame): DataFrame des montants investis cumulés par date et par ticker.
        """
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."
        assert isinstance(portefeuille, list) and len(portefeuille) == 2, "portefeuille doit être une liste contenant un dictionnaire et une chaîne de caractère."
        assert isinstance(portefeuille[0], dict), "Le premier élément de portefeuille doit être un dictionnaire."
        assert isinstance(portefeuille[1], str), "Le deuxième élément de portefeuille doit être une chaîne de caractère (str)."

        datesInvestissementsPrix = self.SommeInvestissementParDate(self.datesAchats)
        datesVentesPrix = self.SommeInvestissementParDate(self.datesVentes)
        datesVentes = sorted(list(datesVentesPrix.keys()))
        datesInvestissements = sorted(list(datesInvestissementsPrix.keys()))
        datesInvestissementsVentes = sorted(datesVentes + datesInvestissements)
        argentVendu = 0

        # Créer des DataFrames pour stocker les prix moyens pondérés d'achat, les quantités totales et les montants investis
        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for date in datesInvestissementsVentes:

            if date in datesVentes:
                argentVendu += datesVentesPrix[date]

            if date in datesInvestissements:
                montant = max(0, (datesInvestissementsPrix[date] - argentVendu))
                # On met à jour l'argent vendu
                argentVendu = max(0, (argentVendu - montant))

                for ticker, repartitionPourcentage in portefeuille[0].items():
                    # Pour chaque ticker, on calcule la quantité achetée et met à jour les prix et quantités cumulés
                    montantAchete = (montant * repartitionPourcentage / 100)
                    montantsInvestis.at[date, ticker] = montantAchete

        montantsInvestisCumules = montantsInvestis.cumsum(axis=0)
        return montantsInvestis, montantsInvestisCumules
    
    