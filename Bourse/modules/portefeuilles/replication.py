from .basePortefeuille import BasePortefeuille

import pandas as pd

class Replication(BasePortefeuille):
        
    def ReplicationDeMonPortefeuille(self):
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        prixTickers = self.prixTickers.copy()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " Réplication"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            montantsInvestisTickers, evolutionVentesTickers, montantsInvestisCumules = self.CalculerPrixMoyenPondereAchatReplicationDeMonPortefeuille(prixTickersFiltree, portfolio[0])

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
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), {})
            self.prixFifoTickers[nomPortefeuille] = self.CalculerPrixFifoTickers(montantsInvestisTickers)
            self.fondsInvestisTickers[nomPortefeuille] = montantsInvestisCumules
            self.montantsInvestisTickers[nomPortefeuille] = montantsInvestisTickers
            self.montantsVentesTickers[nomPortefeuille] = evolutionVentesTickers
            self.soldeCompteBancaire[nomPortefeuille] = (self.EvolutionDepotEspeces() + evolutionArgentsInvestisPortefeuille)
            self.cash[nomPortefeuille] = pd.Series(0.0, index=prixTickers.index, dtype=float)

    def CalculerPrixMoyenPondereAchatReplicationDeMonPortefeuille(self, prixTickers: pd.DataFrame, tickerPourcentages: list) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat pour chaque ticker en fonction des investissements et des ventes réalisés
        dans le portefeuille. Simule également l'évolution des montants investis au fil du temps.

        Args:
            prixTickers (pd.DataFrame): 
                DataFrame contenant les prix quotidiens des tickers, indexé par date (datetime).
                - Les lignes représentent les dates.
                - Les colonnes représentent les tickers.

            tickerPourcentages (dict): 
                Dictionnaire comportant les tickers (str) comme clés, et leurs pourcentages (float) comme valeurs,
                indiquant la répartition des investissements pour chaque ticker dans le portefeuille.
                Exemple : {'AAPL': 50.0, 'MSFT': 50.0}.

        Returns:
            tuple: 
                - pd.DataFrame: Montants investis par date et par ticker.
                - pd.DataFrame: Montants des ventes réalisées par date et par ticker.
                - pd.DataFrame: Montants investis cumulés par date et par ticker.
        """
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."
        assert isinstance(tickerPourcentages, dict), "tickerPourcentages doit être un dictionnaire."

        datesInvestissementsPrix = self.SommeInvestissementParDate(self.datesAchats)
        datesVentesPrix = self.SommeInvestissementParDate(self.datesVentes)
        datesVentes = sorted(list(datesVentesPrix.keys()))
        datesInvestissements = sorted(list(datesInvestissementsPrix.keys()))
        datesInvestissementsVentes = sorted(datesVentes + datesInvestissements)
        argentVendu = 0

        # Créer des DataFrames pour stocker les prix moyens pondérés d'achat, les quantités totales et les montants investis
        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)
        evolutionVentesTickers = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for date in datesInvestissementsVentes:

            if date in datesVentes:
                argentVendu += datesVentesPrix[date]

            if date in datesInvestissements:
                montant = max(0, (datesInvestissementsPrix[date] - argentVendu))
                # On met à jour l'argent vendu
                argentVendu = max(0, (argentVendu - montant))

                for ticker, repartitionPourcentage in tickerPourcentages.items():
                    # Pour chaque ticker, on calcule la quantité achetée et met à jour les prix et quantités cumulés
                    montantAchete = (montant * repartitionPourcentage / 100)
                    montantsInvestis.at[date, ticker] = montantAchete

        montantsInvestisCumules = montantsInvestis.cumsum(axis=0)
        return montantsInvestis, evolutionVentesTickers, montantsInvestisCumules
    
    