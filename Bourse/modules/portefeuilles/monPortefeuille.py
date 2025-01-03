from .basePortefeuille import BasePortefeuille

import pandas as pd
from datetime import datetime
import numpy as np


class MonPortefeuille(BasePortefeuille):
    
    def __init__(self):
        super().__init__()

    
    def MonPortefeuille(self):
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        nomPortefeuille = "Mon Portefeuille"

        montantsInvestis, montantsInvestisCumules = self.PrixMoyenPondereAchat()

        # Calcul des montants
        evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.PlusMoinsValueCompose(montantsInvestis, self.prixTickers)
        evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
        evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1)# + self.PlusValuesEncaisseesNet() + self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, prixTickers).cumsum(axis=0).sum(axis=1)

        # Calcul des pourcentages
        evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
        evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesPortefeuille, self.CalculateNetInvestment())
        
        # On stock les DataFrames
        self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
        self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
        self.fondsInvestis[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
        self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
        self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
        self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
        self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, self.prixTickers)
        self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), self.SommeInvestissementParDate(self.datesVentes))
        self.soldeCompteBancaire[nomPortefeuille] = (self.EvolutionDepotEspeces() + evolutionArgentsInvestisPortefeuille + self.PlusValuesEncaisseesBrut())

    def PrixMoyenPondereAchat(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat pour chaque ticker dans le portefeuille.
        Cette méthode télécharge les prix de clôture pour chaque ticker, puis calcule le montant investi cumulé
        pour chaque date d'achat.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                - montantsInvestis : DataFrame des montants investis pour chaque ticker à chaque date d'achat.
                - montantsInvestisCumules : DataFrame des montants investis cumulés pour chaque ticker.
        """

        datesInvestissementsPrix = self.datesAchats.copy()
        prixTickers = self.prixTickers

        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for ticker, datesInvestissements in datesInvestissementsPrix.items():
            # Vérifie si la date est dans le DataFrame des prix
            for date, montant in datesInvestissements.items():
                montantsInvestis.at[date, ticker] = montant

        montantsInvestisCumules = montantsInvestis.cumsum()
        return montantsInvestis, montantsInvestisCumules

    def PlusMoinsValueCompose(self, montantsInvestis: pd.DataFrame, prixTickers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calcule la plus-value ou moins-value quotidienne réalisée pour chaque ticker en utilisant une composition 
        des gains/pertes à partir du prix d'achat initial.

        Args:
            montantsInvestis (pd.DataFrame): DataFrame contenant les montants investis jusqu'au jour actuel, indexé par date.
            prixTickers (pd.DataFrame): DataFrame contenant les prix quotidiens des actions, indexé par date.

        Returns:
            tuple: (pd.DataFrame, pd.DataFrame)
                - pd.DataFrame: DataFrame avec les dates en index et les tickers en colonnes, contenant la valeur globale 
                                d'investissement composée au fil des jours pour chaque action.
                - pd.DataFrame: DataFrame avec les dates en index et les tickers en colonnes, contenant la plus-value ou 
                                moins-value composée au fil des jours pour chaque action.
        """
        assert isinstance(montantsInvestis, pd.DataFrame), "montantsInvestis doit être un DataFrame"
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame"
        
        assert montantsInvestis.index.equals(prixTickers.index), "Les dates des DataFrames doivent correspondre"
        assert montantsInvestis.columns.equals(prixTickers.columns), "Les tickers des DataFrames doivent correspondre"
        
        # Initialiser le DataFrame pour stocker les valeurs composées de plus/moins-value
        evolutionArgentsInvestisTickers = pd.DataFrame(index=prixTickers.index, columns=prixTickers.columns, dtype=float)
        evolutionGainsPertesTickers = pd.DataFrame(index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul de la plus-value composée pour chaque jour
        for ticker in prixTickers.columns:
            datesVentesPrix = self.datesVentes[ticker] if ticker in self.datesVentes else {}
            
            # Initialiser avec la valeur d'achat initiale pour chaque ticker
            evolutionArgentsInvestisTickers.loc[prixTickers.index[0], ticker] = montantsInvestis.loc[prixTickers.index[0], ticker]
            evolutionGainsPertesTickers.loc[prixTickers.index[0], ticker] = 0

            montantsInvestisCumules = montantsInvestis.loc[prixTickers.index[0], ticker]

            for i in range(1, len(prixTickers.index)):
                datePrecedente = prixTickers.index[i-1]
                dateActuelle = prixTickers.index[i]

                # Calcul de l'évolution en pourcentage entre le jour actuel et le jour précédent
                evolutionPourcentage = (prixTickers.loc[dateActuelle, ticker] / prixTickers.loc[datePrecedente, ticker]) - 1
                
                # Calcule l'évolution globale du portefeuille
                evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] = evolutionArgentsInvestisTickers.loc[datePrecedente, ticker] * (1 + evolutionPourcentage)
                # Calcule l'évolution des moins plus values
                evolutionGainsPertesTickers.loc[dateActuelle, ticker] = (evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] - montantsInvestisCumules)
                
                if montantsInvestis.loc[datePrecedente, ticker] != montantsInvestis.loc[dateActuelle, ticker]:
                    evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] += montantsInvestis.loc[dateActuelle, ticker]
                    montantsInvestisCumules += montantsInvestis.loc[dateActuelle, ticker]

                if dateActuelle in datesVentesPrix:
                    enleverArgentTicker = datesVentesPrix[dateActuelle]
                    evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] -= enleverArgentTicker

                    if ((evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] - enleverArgentTicker) <= 0) or (ticker == "SW.PA"):
                        evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] = 0
                        montantsInvestisCumules = 0

        evolutionArgentsInvestisTickers = evolutionArgentsInvestisTickers.replace(0, np.nan)
        evolutionGainsPertesTickers = evolutionGainsPertesTickers.replace(0, np.nan)

        return evolutionArgentsInvestisTickers, evolutionGainsPertesTickers

    def PlusValuesEncaisseesBrut(self) -> pd.Series:
        """
        Calcule les plus-values brut réalisées sur une période donnée en tenant compte des opérations d'achat et de vente d'investissements.

        Returns:
            pd.DataFrame: Un DataFrame indexé par une plage de dates, contenant les plus-values cumulées réalisées sur la période.
        """
        plageDates = pd.date_range(start=self.startDate, end=self.endDate)
        plusValueRealiseeBrut = pd.Series(0.0, index=plageDates)
        
        # Calcul des plus-values réalisées après la vente
        datesVentesDict = self.SommeInvestissementParDate(self.datesVentes)
        datesAchatsDict = self.SommeInvestissementParDate(self.datesAchats)
        datesVentesList = sorted(list(datesVentesDict.keys()))
        datesAchatsList = sorted(list(datesAchatsDict.keys()))
        datesAchatsVentesList = sorted(datesAchatsList + datesVentesList)

        for date in datesAchatsVentesList:
            if date in datesAchatsList:
                plusValueRealiseeBrut.loc[date:] = max(0, (plusValueRealiseeBrut.at[date] - datesAchatsDict[date]))

            if date in datesVentesList:
                plusValueRealiseeBrut.loc[date:] += datesVentesDict[date]

        return plusValueRealiseeBrut
    
    def PlusValuesEncaisseesNet(self) -> pd.Series:
        """
        Calcule les plus-values net réalisées sur une période donnée en tenant compte des opérations d'achat et de vente d'investissements.

        Returns:
            pd.DataFrame: Un DataFrame indexé par une plage de dates, contenant les plus-values cumulées réalisées sur la période.
        """

        datesAchats = self.datesAchats
        datesVentes = self.datesVentes

        plageDates = pd.date_range(start=self.startDate, end=self.endDate)
        plusValueRealiseeNet = pd.Series(0.0, index=plageDates)
        
        # Récupérer toutes les dates de vente uniques
        datesVentesList = sorted(set(dateVente for ventes in datesVentes.values() for dateVente in ventes.keys()))
        tickerVentesList = sorted(set(ticker for ticker in datesVentes.keys()))

        for dateVente in datesVentesList:
            for ticker in tickerVentesList:
                if dateVente in list(datesVentes[ticker].keys()):
                    # Trouver la somme de l'argent investi avant la vente
                    sommeInvestieAvantVente = 0
                    for dateAchat, montant in datesAchats[ticker].items():
                        if dateAchat <= dateVente:
                            sommeInvestieAvantVente += montant

                    # Calculer la plus-value nette réalisée
                    plusValueRealiseeNet.loc[dateVente:] += datesVentes[ticker][dateVente] - sommeInvestieAvantVente

        return plusValueRealiseeNet
    
    def EvolutionDepotEspeces(self) -> pd.Series:
        """
        Calcule l'évolution du solde du compte bancaire en tenant compte des dépôts d'espèces et des investissements.

        Cette fonction utilise les données de dépôts d'espèces extraites d'un fichier JSON et les prix d'achat des investissements pour 
        calculer le solde du compte bancaire sur une plage de dates. Si le solde devient négatif à une date donnée, il est ajusté à zéro 
        pour toutes les dates ultérieures.

        Returns:
            pd.Series: Série Pandas représentant l'évolution du solde du compte bancaire indexée par les dates.
        """
        dataDepotEspeces = self.ExtraireDonneeJson((self.repertoireJson + "/Dépôts d'espèces.json"))
        datesDepotEspeces = {}
        for item in dataDepotEspeces:
            date = pd.to_datetime(item['Date de valeur'], format='%Y-%m-%d')
            if date in datesDepotEspeces:
                datesDepotEspeces[date] += item['Prix dépôt net']
            else:
                datesDepotEspeces[date] = item['Prix dépôt net']
        datesDepotEspeces = {key: datesDepotEspeces[key] for key in sorted(datesDepotEspeces.keys())}

        result = {}
        for stock, datePrix in self.datesAchats.items():
            for date, prix in datePrix.items():
                if date in result:
                    result[date] += prix
                else:
                    result[date] = prix
        datesInvestissementsPrix = {key: result[key] for key in sorted(result.keys())}

        dates = sorted(list(datesDepotEspeces) + list(datesInvestissementsPrix))
        dates = list(dict.fromkeys(dates))
        startDate = min(dates)
        endDate = datetime.today().strftime('%Y-%m-%d')
        dateRange = pd.date_range(start=startDate, end=endDate) 
        argentsCompteBancaire = pd.Series(0, index=dateRange, dtype=float)

        for date in dates:
            if (date in datesDepotEspeces.keys()):
                argentsCompteBancaire.loc[date:] += datesDepotEspeces[date]

            if (date in datesInvestissementsPrix.keys()):
                argentsCompteBancaire.loc[date:] -= datesInvestissementsPrix[date]
            
            if argentsCompteBancaire.at[date] < 0:
                argentsCompteBancaire.loc[date:] = 0

        return argentsCompteBancaire
    
