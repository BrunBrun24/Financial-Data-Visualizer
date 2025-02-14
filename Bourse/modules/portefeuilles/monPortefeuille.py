from .basePortefeuille import BasePortefeuille

import pandas as pd
from datetime import datetime
import numpy as np
from collections import defaultdict
import os
import time

class MonPortefeuille(BasePortefeuille):
    
    def MonPortefeuille(self, repertoireJson: str):
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        repertoireMonPortefeuille = (repertoireJson + "Mon Portefeuille/")
        if not os.path.isdir(repertoireMonPortefeuille):
            raise FileNotFoundError(f"Le dossier '{repertoireMonPortefeuille}' n'existe pas")
        if any(f.endswith('.json') for f in os.listdir(repertoireMonPortefeuille)):
            # Récupère les données de mon ancien portefeuille s'il en existe
            startDate = self.DownloadDataJson("montantsInvestisTickers", repertoireMonPortefeuille).index[-2]
        else:
            startDate = self.startDate

        nomPortefeuille = "Mon Portefeuille"

        montantsInvestisTickers, montantsInvestisCumules = self.PrixMoyenPondereAchat(self.prixTickers.loc[startDate:])

        # Calcul des montants
        evolutionArgentsInvestisTickers, evolutionVentesTickers, evolutionGainsPertesTickers = self.PlusMoinsValueCompose(montantsInvestisTickers.loc[startDate:], self.prixTickers.loc[startDate:])
        evolutionArgentsInvestisTickers = evolutionArgentsInvestisTickers.loc[startDate:]
        evolutionGainsPertesTickers = evolutionGainsPertesTickers.loc[startDate:]

        evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
        evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1) + self.PlusValuesEncaisseesNet().loc[startDate:] + self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, self.prixTickers.loc[startDate:]).cumsum(axis=0).sum(axis=1)


        if any(f.endswith('.json') for f in os.listdir(repertoireMonPortefeuille)):
            evolutionArgentsInvestisTickers.fillna(self.DownloadDataJson("prixBrutTickers", repertoireMonPortefeuille), inplace=True)
            evolutionVentesTickers.fillna(self.DownloadDataJson("montantsVentesTickers", repertoireMonPortefeuille), inplace=True)

            evolutionGainsPertesTickers = pd.concat([
                evolutionGainsPertesTickers, 
                self.DownloadDataJson("prixNetTickers", repertoireMonPortefeuille)
            ]).sort_index()
            evolutionGainsPertesTickers = evolutionGainsPertesTickers[~evolutionGainsPertesTickers.index.duplicated(keep='first')]
            evolutionGainsPertesTickers.replace(0, np.nan, inplace=True)

            evolutionArgentsInvestisTickers = pd.concat([
                evolutionArgentsInvestisTickers, 
                self.DownloadDataJson("prixBrutTickers", repertoireMonPortefeuille)
            ]).sort_index()
            evolutionArgentsInvestisTickers = evolutionArgentsInvestisTickers[~evolutionArgentsInvestisTickers.index.duplicated(keep='first')]
            
            montantsInvestisCumules = pd.concat([
                montantsInvestisCumules, 
                self.DownloadDataJson("montantsInvestisTickers", repertoireMonPortefeuille).cumsum()
            ]).sort_index()
            montantsInvestisCumules = montantsInvestisCumules[~montantsInvestisCumules.index.duplicated(keep='first')]
            
            montantsInvestisTickers = pd.concat([
                montantsInvestisTickers, 
                self.DownloadDataJson("montantsInvestisTickers", repertoireMonPortefeuille)
            ]).sort_index()
            montantsInvestisTickers = montantsInvestisTickers[~montantsInvestisTickers.index.duplicated(keep='first')]


            ### Pour mon portefeuille ###

            newData = self.DownloadDataJson("prixNetPortefeuille", repertoireMonPortefeuille)
            newData.index = pd.to_datetime(newData.index)
            evolutionGainsPertesPortefeuille = pd.concat([
                evolutionGainsPertesPortefeuille.loc[startDate:], 
                newData
            ]).sort_index()
            evolutionGainsPertesPortefeuille = evolutionGainsPertesPortefeuille[~evolutionGainsPertesPortefeuille.index.duplicated(keep='first')]
            
            newData = self.DownloadDataJson("soldeCompteBancaire", repertoireMonPortefeuille)
            newData.index = pd.to_datetime(newData.index)
            evolutionArgentsInvestisPortefeuille = pd.concat([
                self.EvolutionDepotEspeces().loc[startDate:] + evolutionArgentsInvestisPortefeuille + self.PlusValuesEncaisseesBrut().loc[startDate:], 
                newData
            ]).sort_index()
            evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisPortefeuille[~evolutionArgentsInvestisPortefeuille.index.duplicated(keep='first')]

            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), self.SommeInvestissementParDate(self.datesVentes))
        else:
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), self.SommeInvestissementParDate(self.datesVentes))
            evolutionArgentsInvestisPortefeuille = self.EvolutionDepotEspeces().loc[startDate:] + evolutionArgentsInvestisPortefeuille + self.PlusValuesEncaisseesBrut().loc[startDate:]
        
        # Calcul des pourcentages
        evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
        evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesPortefeuille, self.montantsInvestisPortefeuille.iloc[-1])
        
        # On stock les DataFrames
        self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
        self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
        self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
        self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
        self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
        self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, self.prixTickers)
        self.prixFifoTickers[nomPortefeuille] = self.CalculerPrixFifoTickers(montantsInvestisTickers)
        self.fondsInvestisTickers[nomPortefeuille] = montantsInvestisCumules
        self.montantsInvestisTickers[nomPortefeuille] = montantsInvestisTickers
        self.montantsVentesTickers[nomPortefeuille] = evolutionVentesTickers
        self.soldeCompteBancaire[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
        self.cash[nomPortefeuille] = self.PlusValuesEncaisseesBrut()

    def PrixMoyenPondereAchat(self, prixTickers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for ticker, datesInvestissements in datesInvestissementsPrix.items():
            # Vérifie si la date est dans le DataFrame des prix
            for date, montant in datesInvestissements.items():
                montantsInvestis.at[date, ticker] = montant

        montantsInvestis.fillna(0.0, inplace=True)
        montantsInvestis.sort_index(inplace=True)
        montantsInvestisCumules = montantsInvestis.cumsum()
        return montantsInvestis, montantsInvestisCumules

    def PlusMoinsValueCompose(self, montantsInvestis: pd.DataFrame, prixTickers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        
        assert isinstance(montantsInvestis, pd.DataFrame), "montantsInvestis doit être un DataFrame"
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame"
        
        evolutionArgentsInvestisTickers = self.RecuperationDataFrame("prixBrutTickers", prixTickers)
        evolutionVentesTickers = self.RecuperationDataFrame("montantsVentesTickers", prixTickers)
        evolutionGainsPertesTickers = self.RecuperationDataFrame("prixNetTickers", prixTickers)
        frais = self.RecuperationTickerFrais(self.repertoireJson + "Ordres de ventes.json")

        if (montantsInvestis.index[0] != evolutionGainsPertesTickers.index[0]):
            # Récupère les tickers qui ont toujours de l'argent investis
            tickers = [ticker for ticker in evolutionGainsPertesTickers.columns if evolutionGainsPertesTickers[ticker].iloc[-1] != 0.0]
        else:
            tickers = list(prixTickers.columns)

        derniereDate = evolutionArgentsInvestisTickers.index[-1]

        # Calcul de la plus-value composée pour chaque jour
        for ticker in tickers:
            datesVentesPrix = self.datesVentes[ticker] if ticker in self.datesVentes else {}
            
            # Vérifier si la première ligne ne contient pas des valeurs pour le ticker actuel
            if (montantsInvestis.index[0] == evolutionGainsPertesTickers.index[0]):
                # Initialiser avec la valeur d'achat initiale pour chaque ticker
                evolutionArgentsInvestisTickers.loc[prixTickers.index[0], ticker] = montantsInvestis.loc[prixTickers.index[0], ticker]
                evolutionGainsPertesTickers.loc[prixTickers.index[0], ticker] = 0

                montantsInvestisCumules = montantsInvestis.loc[prixTickers.index[0], ticker]
            else:
                temp, _ = self.PrixMoyenPondereAchat(self.prixTickers)
                montantsInvestisCumules = temp[ticker].loc[:derniereDate].sum()

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
                    enleverArgentTicker = (datesVentesPrix[dateActuelle] + frais[ticker][dateActuelle])
                    evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] -= enleverArgentTicker
                    evolutionVentesTickers.loc[dateActuelle, ticker] = (enleverArgentTicker - frais[ticker][dateActuelle])

                    if ((evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] - enleverArgentTicker) <= 0):
                        evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] = 0
                        montantsInvestisCumules = 0

        evolutionArgentsInvestisTickers = evolutionArgentsInvestisTickers.replace(0, np.nan)
        evolutionGainsPertesTickers = evolutionGainsPertesTickers.replace(0, np.nan)

        return evolutionArgentsInvestisTickers, evolutionVentesTickers, evolutionGainsPertesTickers
    
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
    
    @staticmethod
    def SommeInvestissementParDate(dictionnaireInvestissements: dict) -> dict:
        """
        Crée un nouveau dictionnaire avec les dates comme clés et la somme des montants investis à chaque date comme valeurs.

        Args:
            dictionnaireInvestissements (dict): Dictionnaire où chaque clé représente un actif et les valeurs sont
                                                des sous-dictionnaires avec des dates et les montants investis à ces dates.

        Returns:
            dict: Dictionnaire avec les dates comme clés (format 'YYYY-MM-DD') et les sommes des montants investis à chaque date.
        """
        # Assertion pour vérifier les types des entrées
        assert isinstance(dictionnaireInvestissements, dict), "Le paramètre dictionnaireInvestissements doit être un dictionnaire."

        # Utilisation de defaultdict pour gérer la somme par date
        investissementParDate = defaultdict(float)

        # Parcours du dictionnaire d'investissements
        for actif, investissements in dictionnaireInvestissements.items():
            assert isinstance(actif, str), "Les clés du dictionnaire principal doivent être des chaînes de caractères représentant les actifs."
            assert isinstance(investissements, dict), f"Les valeurs associées à l'actif '{actif}' doivent être des dictionnaires."

            for date, montant in investissements.items():
                assert isinstance(date, (pd.Timestamp, str)), f"La clé '{date}' dans les investissements de l'actif '{actif}' doit être une date (datetime ou string 'YYYY-MM-DD')."
                assert isinstance(montant, (int, float)), f"Le montant associé à la date '{date}' doit être un nombre (int ou float)."

                # Si la date est une chaîne de caractères, la convertir en datetime
                if isinstance(date, str):
                    date = pd.to_datetime(date)

                # Ajouter le montant à la date correspondante
                investissementParDate[date] += montant

        # Conversion en dictionnaire classique et tri par les clés
        return dict(sorted(investissementParDate.items()))
    
    
    def DownloadDataJson(self, nameFile: str, repertoireMonPortefeuille: str):
        filePath = os.path.join(repertoireMonPortefeuille, f"{nameFile}.json")
        data = self.ExtraireDonneeJson(filePath)  # Extraction des données JSON

        try:
            data = pd.DataFrame(data)
            # Vérifier si une colonne 'Date' existe
            if "Date" in data.columns:
                data["Date"] = pd.to_datetime(data["Date"], errors="coerce")  # Convertir la colonne 'Date' au format datetime
                data.set_index("Date", inplace=True)  # Définir 'Date' comme index
        except:
            # Si les données ne sont pas convertibles en DataFrame, essayer de les transformer en Series
            data = pd.Series(data)

        return data
        
    def RecuperationDataFrame(self, nameFile: str, prixTickers: pd.DataFrame):
        filePath = os.path.join((self.repertoireJson + "Mon Portefeuille/"), f"{nameFile}.json")
        if not os.path.exists(filePath):
            return pd.DataFrame(index=prixTickers.index, columns=prixTickers.columns, dtype=float)
        
        data = self.ExtraireDonneeJson(filePath)  # Extraction des données JSON
        data = pd.DataFrame(data)
        # Vérifier si une colonne 'Date' existe
        if "Date" in data.columns:
            data["Date"] = pd.to_datetime(data["Date"], errors="coerce")  # Convertir la colonne 'Date' au format datetime
            data.set_index("Date", inplace=True)  # Définir 'Date' comme index

        return data
    
