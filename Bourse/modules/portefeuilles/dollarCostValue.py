from .basePortefeuille import BasePortefeuille

import pandas as pd
from datetime import datetime

class DollarCostValue(BasePortefeuille):
    
    def DCV(self):
        """
        Cette méthode permet de simuler un investissement en Dollar-Cost Value ou Dynamic Cost Averaging (DCV) en fonction de différents portefeuilles sur différentes plages de date.

        Explication:
            Cette méthode d’investissement est similaire au Dollar-Cost Averaging (DCA),
            mais avec une différence clé : au lieu d’investir des montants fixes à intervalles réguliers,
            l’investissement est ajusté dynamiquement pour maintenir des pourcentages cibles du portefeuille.
        """

        prixTickers = self.prixTickers.copy()
        datesInvestissements = self.DatesInvesissementDCA_DCV()

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " DCV"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]
            datesInvestissementsPrix = {date: (self.ArgentInitialementInvesti()/len(datesInvestissements)) for date in datesInvestissements}

            montantsInvestisTickers, montantsInvestisCumules = self.CalculerPrixMoyenPondereAchatDollarCostValue(datesInvestissementsPrix, prixTickersFiltree, portfolio[0])

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

    def CalculerPrixMoyenPondereAchatDollarCostValue(self, datesInvestissementsPrix: dict, prixTickers: pd.DataFrame, tickerPourcentages: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat en utilisant la méthode Dollar Cost Value.

        Args:
            datesInvestissementsPrix (dict): Un dictionnaire où les clés sont des dates (datetime) et les valeurs sont des montants investis (int ou float).
            prixTickers (pd.DataFrame): Un DataFrame contenant les prix des tickers avec les dates en index et les tickers en colonnes.
            tickerPourcentages (dict): Un dictionnaire avec les pourcentages alloués à chaque ticker.

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

        # DataFrames pour stocker les montants investis et cumulés
        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)
        montantsInvestisFinal = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        datesInvestissement = sorted([date for date in datesInvestissementsPrix.keys()])
        premiereDateInvestissement = min(datesInvestissement)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for nbDate, (date, montant) in enumerate(datesInvestissementsPrix.items()):
            if date in prixTickers.index:  # Vérifier si la date est dans le DataFrame des prix
                if nbDate == 0:
                    # Si c'est la première fois qu'on ajoute de l'argent alors on rétablit l'argent ajouté en fonction des pourcentages de chaque ticker
                    for ticker in prixTickers.columns:
                        ajouterArgentTicker = (montant * tickerPourcentages[ticker] / 100)
                        montantsInvestis.at[date, ticker] = ajouterArgentTicker
                        montantsInvestisFinal.at[date, ticker] = ajouterArgentTicker
                else:
                    # Si on a déjà ajouté de l'argent on ajuste dynamiquement les prix à ajouter de chaque ticker pour maintenir les pourcentages cibles du portefeuille
                    derniereDateInvestissement = datesInvestissement[nbDate - 1] if nbDate >= 1 else premiereDateInvestissement

                    evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.CalculerPlusMoinsValueCompose(montantsInvestis.loc[derniereDateInvestissement:date], prixTickers)
                    montantActuelTickers = evolutionArgentsInvestisTickers.iloc[-2]

                    # On ajuste les investissements des tickers selon les pourcentages cibles
                    montantFuturAjouterTickers = self.AjusterInvestissementCible(tickerPourcentages, montant, montantActuelTickers)
                    # On met à jour les montants investis pour cette date
                    for ticker in prixTickers.columns:
                        montantsInvestisFinal.at[date, ticker] = montantFuturAjouterTickers[ticker]
                        montantsInvestis.at[date, ticker] = montantFuturAjouterTickers[ticker]

                    montantsInvestis.loc[date] += montantActuelTickers

        return montantsInvestisFinal, montantsInvestisFinal.cumsum()

    @staticmethod
    def AjusterInvestissementCible(repartitionPortefeuille: dict, montantInvestissement: float, prixActuel: pd.Series) -> dict:
        """
        Calcule combien d'argent doit être ajouté à chaque entreprise pour atteindre la répartition cible, en respectant
        le montant total à investir.

        Args:
            repartitionPortefeuille (dict): Dictionnaire avec les tickers comme clés et les pourcentages cibles comme valeurs.
            montantInvestissement (float): Montant total supplémentaire à investir.
            prixActuel (pd.Series): Series avec les tickers comme index et les valeurs actuelles du portefeuille.

        Returns:
            dict: Dictionnaire avec les tickers comme clés et le montant à investir pour chaque entreprise,
                totalisant exactement le montantInvestissement.
        """
        assert isinstance(repartitionPortefeuille, dict), "repartitionPortefeuille doit être un dictionnaire"
        assert round(sum(repartitionPortefeuille.values())) == 100, "Les pourcentages de repartitionPortefeuille doivent totaliser 100"
        assert isinstance(montantInvestissement, (int, float)), "montantInvestissement doit être un nombre"
        assert isinstance(prixActuel, pd.Series), "prixActuel doit être un pd.Series"

        # Calcul de la valeur actuelle totale du portefeuille
        valeurActuelleTotale = prixActuel.sum() + montantInvestissement

        # Calcul des montants cibles pour chaque entreprise
        montantCible = {entreprise: (pourcentage / 100) * valeurActuelleTotale for entreprise, pourcentage in repartitionPortefeuille.items()}

        # Calcul du montant à ajouter pour chaque entreprise
        montantAInvestir = {entreprise: max(0, montantCible[entreprise] - prixActuel.get(entreprise, 0)) for entreprise in repartitionPortefeuille}

        # Ajustement pour que la somme des montants à investir soit égale à montantInvestissement
        totalAInvestir = sum(montantAInvestir.values())
        if totalAInvestir != montantInvestissement:
            # Normalisation pour ajuster le montant total à exactement montantInvestissement
            facteurAjustement = montantInvestissement / totalAInvestir
            montantAInvestir = {entreprise: montant * facteurAjustement for entreprise, montant in montantAInvestir.items()}

        return montantAInvestir
    
    