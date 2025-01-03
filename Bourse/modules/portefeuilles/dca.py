from .basePortefeuille import BasePortefeuille

import pandas as pd
from datetime import datetime


class DCA(BasePortefeuille):
    
    def __init__(self):
        super().__init__()
        

    def DollarCostAveraging(self):
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
        datesInvestissementsPrix = {date: (self.ArgentInitialementInvesti()/len(datesInvestissements)) for date in datesInvestissements}

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " DCA"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            montantsInvestis, montantsInvestisCumules = self.PrixMoyenPondereAchatDca(datesInvestissementsPrix, prixTickersFiltree, portfolio)

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
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, datesInvestissementsPrix, {})
            self.soldeCompteBancaire[nomPortefeuille] = evolutionArgentsInvestisPortefeuille

    def DatesInvesissementDCA_DCV(self) -> list:
        """
        Extrait les dates de début de chaque mois dans la plage donnée entre startDate et endDate.

        Returns:
            list: Liste des dates de début de chaque mois sous forme de chaînes formatées 'YYYY-MM-DD'.
        """

        # Conversion en format datetime si nécessaire
        startDate = pd.to_datetime(self.startDate)
        endDate = pd.to_datetime(self.endDate)

        # Initialisation de la liste pour stocker les dates de début de chaque mois
        debutMois = []
        currentDate = startDate
        # Passer au mois suivant
        next_month = currentDate.month % 12 + 1
        next_year = currentDate.year + (currentDate.month // 12)
        currentDate = currentDate.replace(month=next_month, year=next_year, day=1)

        while currentDate <= endDate:
            # Ajouter la date de début du mois formatée
            debutMois.append(currentDate)

            # Passer au mois suivant
            next_month = currentDate.month % 12 + 1
            next_year = currentDate.year + (currentDate.month // 12)
            currentDate = currentDate.replace(month=next_month, year=next_year, day=1)

        return sorted(debutMois)
    
    @staticmethod
    def PrixMoyenPondereAchatDca(datesInvestissementsPrix: dict, prixTickers: pd.DataFrame, portefeuille: list) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat en utilisant la méthode Dollar Cost Averaging.

        Args:
            datesInvestissementsPrix (dict): Un dictionnaire où les clés sont des dates (datetime) et les valeurs sont des montants investis (int ou float).
            prixTickers (pd.DataFrame): Un DataFrame contenant les prix des tickers avec les dates en index et les tickers en colonnes.
            portefeuille (list): Une liste contenant deux éléments :
                - Un dictionnaire où les clés sont des tickers et les valeurs sont les pourcentages du portefeuille alloués à chaque ticker.
                - Une chaîne de caractère représentant une information supplémentaire (non utilisée dans cette fonction).

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: Un tuple contenant deux DataFrames :
                - Le premier DataFrame représente les montants investis pour chaque ticker à chaque date.
                - Le deuxième DataFrame représente les montants investis cumulés pour chaque ticker à chaque date.
        """
        assert isinstance(datesInvestissementsPrix, dict), "datesInvestissementsPrix doit être un dictionnaire."
        assert all(isinstance(date, datetime) for date in datesInvestissementsPrix.keys()), "Les clés de datesInvestissementsPrix doivent être des instances datetime."
        assert all(isinstance(montant, (int, float)) for montant in datesInvestissementsPrix.values()), "Les valeurs de datesInvestissementsPrix doivent être des nombres (int ou float)."

        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."

        assert isinstance(portefeuille, list) and len(portefeuille) == 2, "portefeuille doit être une liste contenant un dictionnaire et une chaîne de caractère."
        assert isinstance(portefeuille[0], dict), "Le premier élément de portefeuille doit être un dictionnaire."
        assert isinstance(portefeuille[1], str), "Le deuxième élément de portefeuille doit être une chaîne de caractère (str)."

        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for date, montant in datesInvestissementsPrix.items():
            if date in prixTickers.index:  # Vérifier si la date est dans le DataFrame des prix
                for ticker in prixTickers.columns:
                    ajouterArgentTicker = (montant * portefeuille[0][ticker] / 100)
                    montantsInvestis.at[date, ticker] = ajouterArgentTicker

        montantsInvestisCumules = montantsInvestis.cumsum()
        return montantsInvestis, montantsInvestisCumules
    
    def ArgentInitialementInvesti(self) -> int|float:
        """
        Calcule l'argent investi initialement.
        
        Il faut calculer la somme des montants investis pour chaque ticker à chaque date d'achat.
        Puis on soustrait l'argent initialement investi du ticker s'il a été vendu.

        Attention toutefois, si on vend un ticker et qu'il possède une ancienne date de vente.
        Alors il faut calculer l'argent initialement investi entre la dernière date de vente et la date de vente actuelle.

        De plus il faut rajouter l'argent initialement investi des tickers qui sont vendus après la dernière date d'achats.

        Returns:
            int|float: La différence entre la somme des prix d'achat et la somme des prix de vente.
        """
        assert isinstance(self.datesAchats, dict), "datesAchats doit être un dictionnaire"
        assert isinstance(self.datesVentes, dict), "datesVentes doit être un dictionnaire"

        totalBuy = 0.0
        totalSell = 0.0

        # Dictionnaire pour garder la trace de l'investissement restant pour chaque ticker
        investments = {ticker: 0.0 for ticker in self.datesAchats.keys()}

        # Calcul de l'argent investi initialement pour chaque ticker
        for ticker, achats in self.datesAchats.items():
            # Somme des prix d'achat
            totalBuy += sum(achats.values())
            investments[ticker] = sum(achats.values())

        # Calcul des ventes et ajustement de l'investissement pour chaque ticker
        for ticker, dateVente in self.datesVentes.items():
            if ticker in investments:
                # Si l'action a été vendue, soustraire l'investissement
                totalSell += investments[ticker]

                # Après la vente, réinitialiser l'investissement pour cette action
                investments[ticker] = 0.0


        derniereDateAchat = max([date for tickerDates in self.datesAchats.values() for date in tickerDates.keys()])
        tickerVentes = sorted(set(ticker for ticker in self.datesVentes.keys()))
        argentEnPlus = 0
        
        for ticker, datesAchatsPrix in self.datesAchats.items():
            if ticker in tickerVentes:
                for dateVente in self.datesVentes[ticker].keys():

                    if dateVente > derniereDateAchat:
                        # Parcourir toutes les dates d'achat du ticker
                        for dateAchat, montant in datesAchatsPrix.items():
                            argentEnPlus += montant

        return (totalBuy - totalSell + argentEnPlus)
    
