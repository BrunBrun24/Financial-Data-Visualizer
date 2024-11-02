import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import json
import os
from collections import defaultdict
import numpy as np
import copy


class TradeRepublicPerformance:
    """
    La classe TradeRepublicPerformance est conçue pour analyser et visualiser la performance des transactions boursières
    à partir d’un fichier JSON contenant les données de transactions.
    Elle permet de calculer et de suivre l’évolution des investissements, des prix des actions, et de la performance globale du portefeuille.

    Attributs :
        fichierJson (str): Chemin vers le fichier JSON contenant les transactions.
        portfolioPercentage (list): Liste des portefeuilles, où chaque portefeuille est représenté par une liste contenant un dictionnaire d'actions avec leurs pourcentages, un montant à investir et un nom de portefeuille.
        nomDossier (str): Chemin vers le dossier où sauvegarder le fichier de sortie.
        nomFichier (str): Nom du fichier de sortie (doit avoir une extension .html).
    """

    def __init__(self, fichierJson: str) -> None:
        """
        Initialise la classe avec les informations nécessaires pour la gestion des transactions et des fichiers.

        Args:
            fichierJson (str): Chemin vers le fichier JSON contenant les transactions.
        """
        assert isinstance(fichierJson, str), f"fichierJson doit être une chaîne de caractères: ({fichierJson})"
        assert os.path.exists(fichierJson) and fichierJson.endswith('.json'), f"Le fichier {fichierJson} n'existe pas ou n'a pas l'extension .json."

        self.fichierJson = fichierJson

        self.pourcentageTickers = {}
        self.prixNetTickers = {}
        self.prixBrutTickers = {}
        self.dividendesTickers = {}
        self.pourcentageMoisPortefeuille = pd.DataFrame()
        self.pourcentagePortefeuille = pd.DataFrame()
        self.prixNetPortefeuille = pd.DataFrame()
        self.prixBrutPortefeuille = pd.DataFrame()

        # Ajoute sur le graphique mon portefeuille
        self.MonPortefeuille()



    #################### SETTERS ####################
    def SetPortfolioPercentage(self, portfolioPercentage: list):
        assert isinstance(portfolioPercentage, list), "portfolioPercentage doit être une liste de portefeuilles."
        for portefeuille in portfolioPercentage:
            assert isinstance(portefeuille, list) and len(portefeuille) == 3, \
                "Chaque portefeuille doit être une liste contenant un dictionnaire, un montant, et une chaîne de caractère."
            assert isinstance(portefeuille[0], dict), "Le premier élément du portefeuille doit être un dictionnaire des actions avec leurs pourcentages."
            assert isinstance(portefeuille[1], (int, float)), "Le deuxième élément du portefeuille doit être un montant (int ou float)."
            assert isinstance(portefeuille[2], str), "Le troisième élément du portefeuille doit être une chaîne de caractères représentant le nom du portefeuille."
            for ticker, pourcentage in portefeuille[0].items():
                assert isinstance(ticker, str), f"Chaque clé du dictionnaire (ticker) doit être une chaîne de caractères, mais '{ticker}' ne l'est pas."
                assert isinstance(pourcentage, (int, float)), f"Chaque valeur du dictionnaire (pourcentage) doit être un nombre (int ou float), mais '{pourcentage}' ne l'est pas."

        self.portfolioPercentage = portfolioPercentage
    #################################################



    #################### TÉLÉCHARGEMENT DES DONNÉES BOURSIÈRES ####################
    def DownloadTickersPrice(self, tickers: list, startDate: str|datetime, endDate: str|datetime) -> pd.DataFrame:
        """
        Télécharge les prix de clôture des actions spécifiées sur une période donnée.

        Args:
            tickers (list): Liste des symboles boursiers à télécharger.
            startDate (str | datetime): Date de début du téléchargement au format 'YYYY-MM-DD'.
            endDate (str | datetime): Date de fin du téléchargement au format 'YYYY-MM-DD' ou un objet datetime.

        Returns:
            pd.DataFrame: Un DataFrame contenant les prix de clôture des actions spécifiées,
            avec les dates manquantes complétées et les prix éventuellement convertis en EUR.
        """
        assert isinstance(tickers, list) and all(isinstance(ticker, str) for ticker in tickers), "tickers doit être une liste de chaînes de caractères"
        assert isinstance(startDate, (str, datetime)), "startDate doit être une chaîne de caractères ou un objet datetime"
        assert isinstance(endDate, (str, datetime)), "endDate doit être une chaîne de caractères ou un objet datetime"

        # Téléchargement des données pour plusieurs tickers ou un seul
        if len(tickers) > 1:
            prixTickers = yf.download(tickers, start=startDate, end=endDate, interval="1d")["Close"].ffill().bfill()
        else:
            prixTickers = pd.DataFrame()
            for symbol in tickers:
                prixTickers[symbol] = yf.download(symbol, start=startDate, end=endDate, interval="1d")["Close"].ffill().bfill()

        # Normalisation de l'index pour enlever les fuseaux horaires et l'heure
        prixTickers.index = prixTickers.index.tz_localize(None).normalize()

        # Gérer les dates manquantes dans prixTickers
        allDates = pd.date_range(start=startDate, end=endDate, freq='D')
        prixTickers = prixTickers.reindex(allDates).ffill().bfill()

        # Conversion des prix en EUR si nécessaire
        prixTickers = self.ConversionMonnaieDollardEuro(prixTickers, startDate, endDate)

        return prixTickers
    
    @staticmethod
    def ConversionMonnaieDollardEuro(df: pd.DataFrame, startDate: str|datetime, endDate: str|datetime) -> pd.DataFrame:
        """
        Convertit les valeurs d'un DataFrame d'une devise à une autre sur une période spécifiée.

        Args:
            df (pd.DataFrame): DataFrame contenant les données financières en différentes devises.
            startDate (str | datetime): Date de début au format 'YYYY-MM-DD'.
            endDate (str | datetime): Date de fin au format 'YYYY-MM-DD'.

        Returns:
            pd.DataFrame: Un DataFrame avec les valeurs converties en utilisant le taux de change correspondant.
        """
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame: ({type(df).__name__})"
        assert isinstance(startDate, (str, datetime)), f"startDate doit être une chaîne de caractères: ({type(startDate).__name__})"
        assert isinstance(endDate, (str, datetime)), f"endDate doit être une chaîne de caractères: ({type(endDate).__name__})"
        assert all(df.dtypes == 'float64') or all(df.dtypes == 'int64'), "Les colonnes du DataFrame doivent contenir des valeurs numériques."

        # Télécharger les données de la devise
        tauxDeConvertionDf = yf.download("EURUSD=X", start=startDate, end=endDate, interval="1d")["Close"]

        # Gérer les dates manquantes dans tauxDeConvertionDf
        allDates = pd.date_range(start=startDate, end=endDate, freq='D')
        tauxDeConvertionDf = tauxDeConvertionDf.reindex(allDates).ffill().bfill()

        # Filtrer les colonnes de df pour ne garder que celles qui doivent être converties
        tickerConvertir = [ticker for ticker in df.columns if "." not in ticker]
        dfFiltree = df.loc[:, df.columns.intersection(tickerConvertir)]

        # Aligner et diviser les valeurs pour la conversion
        dfFiltree = dfFiltree.divide(tauxDeConvertionDf, axis=0)

        # Remplacer les valeurs dans df
        colonnesCommunes = df.columns.intersection(dfFiltree.columns)
        df[colonnesCommunes] = dfFiltree[colonnesCommunes]

        return df
    ###############################################################################



    #################### PORTEFEUILLE, TICKERS ####################
    ########## Pourcentage ##########
    @staticmethod
    def EvolutionPourcentageTickers(prixFIFO: pd.DataFrame, prixTickers: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution en pourcentage du prix des actions par rapport aux prix d'achat FIFO.

        Args:
            prixFIFO (pd.DataFrame): DataFrame contenant les prix d'achat FIFO pour chaque ticker. 
                                    Les colonnes représentent les tickers et les index représentent les dates.
            prixTickers (pd.DataFrame): DataFrame contenant les prix actuels des tickers avec les mêmes colonnes 
                                        et index que prixFIFO.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage pour chaque ticker, avec les mêmes 
                        index et colonnes que les DataFrames d'entrée.
        """
        assert isinstance(prixFIFO, pd.DataFrame), "prixFIFO doit être un DataFrame."
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."
        assert prixFIFO.index.equals(prixTickers.index), "Les index de prixFIFO et prixTickers doivent être identiques."

        # Remplacer les zéros par NaN pour éviter la division par zéro
        prixFIFO = prixFIFO.where(prixFIFO != 0, np.nan)

        # Calculer l'évolution en pourcentage vectorisé
        pourcentageTickers = (prixTickers * 100 / prixFIFO) - 100

        return pourcentageTickers

    @staticmethod
    def EvolutionPourcentagePortefeuille(prixPortefeuilleNet: pd.DataFrame, argentInvestis: int|float) -> pd.DataFrame:
        """
        Calcule l'évolution en pourcentage des gains/pertes par rapport au montant total investi.

        Args:
            prixPortefeuilleNet (pd.DataFrame): DataFrame contenant l'évolution du prix net du portefeuille.
            argentInvestis (int | float): Mntant total investi initialement.

        Returns:
            pd.DataFrame: DataFrame avec l'évolution en pourcentage des gains/pertes.
        """
        assert isinstance(prixPortefeuilleNet, pd.DataFrame), f"prixPortefeuilleNet doit être un int ou float: ({type(prixPortefeuilleNet).__name__})"
        assert isinstance(argentInvestis, (int, float)), f"argentInvestis doit être un int ou float: ({type(argentInvestis).__name__})"
        assert argentInvestis != 0, "argentInvestis ne doit pas être égal à zéro pour éviter la division par zéro."

        # Calculer l'évolution en pourcentage pour chaque colonne
        dfPourcentage = round((prixPortefeuilleNet / argentInvestis) * 100, 2)

        return dfPourcentage

    @staticmethod
    def EvolutionPourcentageMois(evolutionPrixBrutPortefeuille: pd.DataFrame, datesInvestissementsPrix: dict, datesVentesPrix: dict) -> pd.DataFrame:
        """
        Calcule l'évolution mensuelle en pourcentage du portefeuille en utilisant les dates d'investissement pour un calcul
        précis du montant total investi et retourne un DataFrame.

        Args:
            evolutionPrixBrutPortefeuille (pd.DataFrame): DataFrame contenant les valeurs journalières du portefeuille
                                                            avec une colonne 'Portefeuille' et un index de dates.
            datesInvestissementsPrix (dict): Dictionnaire avec des clés représentant des dates (de type datetime ou string 'YYYY-MM-DD')
                                            et des valeurs en entier ou flottant représentant le prix de l'investissement à cette date.
            datesVentesPrix (dict): Dictionnaire avec des clés représentant des dates (de type datetime ou string 'YYYY-MM-DD')
                                    et des valeurs en entier ou flottant représentant le prix de l'investissement à cette date.

        Returns:
            pd.DataFrame: Un DataFrame avec les dates au format 'YYYY-MM' comme index et l'évolution mensuelle
                            en pourcentage dans une colonne 'EvolutionPourcentage'.
        """
        assert isinstance(evolutionPrixBrutPortefeuille, pd.DataFrame), "evolutionPrixBrutPortefeuille doit être un DataFrame"
        assert 'Portefeuille' in evolutionPrixBrutPortefeuille.columns, "Le DataFrame doit contenir une colonne nommée 'Portefeuille'"
        assert pd.api.types.is_datetime64_any_dtype(evolutionPrixBrutPortefeuille.index), "L'index du DataFrame doit être de type datetime"
        assert isinstance(datesInvestissementsPrix, dict) and all(isinstance(date, (pd.Timestamp, str)) for date in datesInvestissementsPrix.keys()), \
            "datesInvestissementsPrix doit être un dictionnaire avec des dates (type datetime ou string 'YYYY-MM-DD') comme clés"
        assert all(isinstance(prix, (int, float)) for prix in datesInvestissementsPrix.values()), \
            "Les valeurs de datesInvestissementsPrix doivent être des entiers ou des flottants"
        assert isinstance(datesVentesPrix, dict) and all(isinstance(date, (pd.Timestamp, str)) for date in datesVentesPrix.keys()), \
            "datesVentesPrix doit être un dictionnaire avec des dates (type datetime ou string 'YYYY-MM-DD') comme clés"
        assert all(isinstance(prix, (int, float)) for prix in datesVentesPrix.values()), \
            "Les valeurs de datesVentesPrix doivent être des entiers ou des flottants"

        # Convertir les dates d'investissement en datetime si nécessaire
        datesInvestissementsPrix = {pd.to_datetime(date): prix for (date, prix) in datesInvestissementsPrix.items()}
        datesVentesPrix = {pd.to_datetime(date): prix for (date, prix) in datesVentesPrix.items()}

        # Filtrer pour retirer les valeurs où 'Portefeuille' est égal à zéro
        filteredDataFrame = evolutionPrixBrutPortefeuille[evolutionPrixBrutPortefeuille['Portefeuille'] != 0]

        # S'assurer que l'index est trié
        filteredDataFrame.sort_index(inplace=True)

        # Resampler pour obtenir la valeur de fin de mois
        prixMensuel = filteredDataFrame['Portefeuille'].resample('ME').last()

        # Initialiser le dictionnaire pour les résultats
        evolutionPourcentageDict = {}
        montantGagneMoisPasse = 0

        # Calculer l'évolution pour chaque mois
        for (date, valeurMois) in prixMensuel.items():
            # Calculer le montant total investi jusqu'à ce mois
            montantInvestiTotal = 0  # Réinitialiser avec la valeur initiale
            # Ajouter les montants investis aux dates précédentes ou égales à la fin de mois actuelle
            for dateInvest, prix in datesInvestissementsPrix.items():
                if dateInvest <= date:
                    montantInvestiTotal += prix
            # Enlever les montants vendus aux dates précédentes ou égales à la fin de mois actuelle
            for dateVente, prix in datesVentesPrix.items():
                if dateVente <= date:
                    montantInvestiTotal -= prix

            # Calcul de l'évolution en pourcentage
            pourcentageEvolution = ((valeurMois) * 100 / (montantInvestiTotal + montantGagneMoisPasse)) - 100
            # Ajouter au dictionnaire avec la clé formatée en 'YYYY-MM'
            evolutionPourcentageDict[date.strftime('%Y-%m')] = round(pourcentageEvolution, 2)

            # Mettre à jour le montant gagné du mois passé
            montantGagneMoisPasse = (valeurMois - montantInvestiTotal)

        # Transformer le dictionnaire en DataFrame
        evolutionPourcentageDf = pd.DataFrame.from_dict(evolutionPourcentageDict, orient='index', columns=['EvolutionPourcentage'])
        evolutionPourcentageDf.index.name = 'Date'

        return evolutionPourcentageDf
    #################################

    ########## Prix ##########
    @staticmethod
    def EvolutionPrixTickersPortefeuille(pourcentageTickers: pd.DataFrame, ArgentsInvestisTickers: pd.DataFrame, datesVentes: dict) -> pd.DataFrame:
        """
        Calcule l'évolution du prix des actions par rapport aux prix d'achat en utilisant les pourcentages fournis.

        Args:
            pourcentageTickers (pd.DataFrame): DataFrame contenant les évolutions en pourcentage des prix des tickers. Les colonnes représentent les tickers et les index représentent les dates.
            ArgentsInvestisTickers (pd.DataFrame): DataFrame des coûts totaux d'achat pour chaque ticker, avec les mêmes colonnes et index que pourcentageTickers.
            datesVentes (dict): Dictionnaire contenant les dates de vente et les prix associés pour chaque ticker, où chaque clé est un ticker et la valeur est un dictionnaire avec les dates comme clés et les prix comme valeurs.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                - evolutionPrixTickersNet (pd.DataFrame): Evolution des prix nets pour chaque ticker.
                - evolutionGlobalPrixNet (pd.DataFrame): Somme globale des évolutions des prix nets pour le portefeuille.
                - evolutionPrixTickersBrut (pd.DataFrame): Evolution des prix bruts pour chaque ticker.
                - evolutionGlobalPrixBrut (pd.DataFrame): Somme globale des évolutions des prix bruts pour le portefeuille.
        """

        # Vérifications des types
        assert isinstance(pourcentageTickers, pd.DataFrame), f"pourcentageTickers doit être un DataFrame: ({type(pourcentageTickers).__name__})"
        assert isinstance(ArgentsInvestisTickers, pd.DataFrame), f"ArgentsInvestisTickers doit être un DataFrame: ({type(ArgentsInvestisTickers).__name__})"
        assert isinstance(datesVentes, dict), f"datesVentes doit être un dictionnaire: ({type(datesVentes).__name__})"

        # Assurer que les index des DataFrames sont identiques
        assert pourcentageTickers.index.equals(ArgentsInvestisTickers.index), "Les index de pourcentageTickers et ArgentsInvestisTickers doivent être identiques."

        # Initialisation des DataFrames pour l'évolution des prix nets et bruts
        evolutionPrixTickersNet = pd.DataFrame(index=pourcentageTickers.index, columns=pourcentageTickers.columns)
        evolutionPrixTickersBrut = pd.DataFrame(index=pourcentageTickers.index, columns=pourcentageTickers.columns)
        plusValueRealisee = pd.DataFrame(index=pourcentageTickers.index, columns=pourcentageTickers.columns)

        # Calculer l'évolution du prix pour chaque ticker
        for ticker in pourcentageTickers.columns:
            pourcentage = pourcentageTickers[ticker] / 100

            # Calculer l'évolution net
            evolutionPrixTickersNet[ticker] = (ArgentsInvestisTickers[ticker] * (1 + pourcentage)) - ArgentsInvestisTickers[ticker]

            # Calculer l'évolution brut
            evolutionPrixTickersBrut[ticker] = (ArgentsInvestisTickers[ticker] * (1 + pourcentage))

        # Calcul des plus-values réalisées après la vente
        for ticker, operations in datesVentes.items():
            for date, prix in operations.items():
                dateMoinsUnJour = (pd.to_datetime(date) - timedelta(days=1)).strftime('%Y-%m-%d')
                plusValueRealisee.loc[dateMoinsUnJour:, ticker] = evolutionPrixTickersNet.at[dateMoinsUnJour, ticker]

        # Somme globale des évolutions des prix
        evolutionGlobalPrixNet = pd.DataFrame(index=evolutionPrixTickersNet.index)
        evolutionGlobalPrixBrut = pd.DataFrame(index=evolutionPrixTickersBrut.index)

        evolutionGlobalPrixNet["Portefeuille"] = evolutionPrixTickersNet.sum(axis=1) + plusValueRealisee.sum(axis=1)
        evolutionGlobalPrixBrut["Portefeuille"] = evolutionPrixTickersBrut.sum(axis=1)

        return evolutionPrixTickersBrut, evolutionGlobalPrixBrut, evolutionPrixTickersNet, evolutionGlobalPrixNet

    @staticmethod
    def EvolutionDividendesPortefeuille(evolutionPrixBrutTickers: pd.DataFrame, tickerPriceDf: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution des dividendes pour chaque ticker d'un portefeuille, basée sur les prix bruts et les dividendes distribués.

        Args:
            evolutionPrixBrutTickers (pd.DataFrame): DataFrame contenant l'évolution brute des prix des tickers du portefeuille.
            tickerPriceDf (pd.DataFrame): DataFrame contenant les prix des tickers correspondants.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution des dividendes pour chaque ticker, répartis sur les dates du portefeuille.
        """
        assert isinstance(evolutionPrixBrutTickers, pd.DataFrame), "evolutionPrixBrutTickers doit être un DataFrame"
        assert isinstance(tickerPriceDf, pd.DataFrame), "tickerPriceDf doit être un DataFrame"

        # Vérification des types de données dans les DataFrames
        assert all(isinstance(date, pd.Timestamp) for date in evolutionPrixBrutTickers.index), "Les index de evolutionPrixBrutTickers doivent être de type pd.Timestamp"

        # Initialiser le DataFrame des dividendes avec des zéros
        tickersDividendes = pd.DataFrame(0, index=evolutionPrixBrutTickers.index, columns=evolutionPrixBrutTickers.columns, dtype=float)

        for ticker in evolutionPrixBrutTickers.columns:
            # Téléchargement des données de dividendes
            stock = yf.Ticker(ticker)
            dividendes = stock.dividends

            # S'assurer que l'index des dividendes est timezone-naive pour comparaison
            if dividendes.index.tz is not None:
                dividendes.index = dividendes.index.tz_localize(None)

            # Filtrage des dividendes dans la plage de dates spécifiée
            dividendes = dividendes.loc[evolutionPrixBrutTickers.index.min():evolutionPrixBrutTickers.index.max()]

            # Ajout des dividendes au DataFrame, avec propagation aux dates suivantes
            for date, montantDividendes in dividendes.items():
                if date in tickersDividendes.index:
                    # Calculer et ajouter le montant du dividende
                    montantDividendesAjoute = (montantDividendes * evolutionPrixBrutTickers.at[date, ticker] / tickerPriceDf.at[date, ticker])
                    tickersDividendes.at[date, ticker] += montantDividendesAjoute

        return tickersDividendes
    ##########################

    ########## ANNEXES ##########
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
                    date = pd.to_datetime(date).strftime('%Y-%m-%d')

                # Ajouter le montant à la date correspondante
                investissementParDate[date] += montant

        # Conversion en dictionnaire classique
        return dict(investissementParDate)
    #############################
    ###############################################################



    #################### PORTEFEUILLES ####################
    ########## MON PORTEFEUILLE ##########
    def MonPortefeuille(self) -> None:
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        nomPortefeuille = "Mon Portefeuille"
        datesAchats = self.RecuperationTickerBuySell("achats")
        datesVentes = self.RecuperationTickerBuySell("ventes")

        prixFIFO, prixTickers, ArgentsInvestisTickers = self.CalculerPrixAchatFIFO_MonPortefeuille(datesAchats, datesVentes)
        evolutionPourcentageTickers = self.EvolutionPourcentageTickers(prixFIFO, prixTickers)
        evolutionPrixBrutTickers, evolutionPrixBrutPortefeuille, evolutionPrixNetTickers, evolutionPrixNetPortefeuille = self.EvolutionPrixTickersPortefeuille(evolutionPourcentageTickers, ArgentsInvestisTickers, datesVentes)

        # On stock les DataFrames
        self.pourcentagePortefeuille[nomPortefeuille] = self.EvolutionPourcentagePortefeuille(evolutionPrixNetPortefeuille, self.ArgentInvestiAll(datesAchats, datesVentes))
        self.prixNetPortefeuille[nomPortefeuille] = evolutionPrixNetPortefeuille
        self.prixBrutPortefeuille[nomPortefeuille] = evolutionPrixBrutPortefeuille
        self.pourcentageTickers[nomPortefeuille] = evolutionPourcentageTickers
        self.prixNetTickers[nomPortefeuille] = evolutionPrixNetTickers
        self.prixBrutTickers[nomPortefeuille] = evolutionPrixBrutTickers
        self.dividendesTickers[nomPortefeuille] = self.EvolutionDividendesPortefeuille(evolutionPrixBrutTickers, prixTickers)
        self.pourcentageMoisPortefeuille[nomPortefeuille] = self.EvolutionPourcentageMois(evolutionPrixBrutPortefeuille, self.SommeInvestissementParDate(datesAchats), self.SommeInvestissementParDate(datesVentes))

        return min(list(set(date for ele in datesAchats.values() for date in ele.keys())))

    def RecuperationTickerBuySell(self, objectif: str) -> dict:
        """
        Récupère les données de transactions par ticker depuis un fichier JSON.

        Args:
            objectif (str): Clé dans le fichier JSON utilisée pour extraire les prix des transactions
            (ex: 'achats', 'ventes').

        Returns:
            dict: Un dictionnaire où chaque clé est un ticker, et chaque valeur est un dictionnaire contenant les dates et les prix.
        """
        assert isinstance(objectif, str), f"objectif doit être une chaîne de caractères, mais c'est {type(objectif).__name__}."

        # Ouverture et lecture du fichier JSON
        with open(self.fichierJson, 'r') as file:
            data = json.load(file)

        result = {}
        # Parcours des transactions pour chaque ticker
        for transaction in data.get('transactions', []):
            ticker = transaction.get('ticker')
            if ticker is None:
                continue

            result[ticker] = {}
            # Extraction des données de transaction (dates et prix) en fonction de l'objectif
            for ele in transaction.get(objectif, []):
                date = ele.get('date')
                price = ele.get('price')
                if date is not None and price is not None:
                    if date in result[ticker]:
                        result[ticker][date] += price
                    else:
                        result[ticker][date] = price

        return result

    def CalculerPrixAchatFIFO_MonPortefeuille(self, datesAchats: dict, datesVentes: dict) -> tuple:
        """
        Calcule les prix d'achat FIFO (First In First Out) pour les actions basées sur les dates d'achat et les prix de clôture.

        Args:
            datesAchats (dict): Dictionnaire contenant les dates d'achat pour chaque ticker, où chaque clé est un ticker et la valeur est un dictionnaire avec des dates comme clés et montants d'achat comme valeurs.
            datesVentes (dict): Dictionnaire contenant les dates de vente et les prix associés pour chaque ticker, où chaque clé est un ticker et la valeur est un dictionnaire avec les dates comme clés et les prix comme valeurs.

        Returns:
            tuple: Un tuple contenant trois DataFrames :
                - prixFIFO : DataFrame des prix d'achat FIFO pour chaque ticker.
                - prixTickers : DataFrame des prix de clôture des actions.
                - ArgentsInvestisTickers : DataFrame des coûts totaux d'achat pour chaque ticker.
        """

        assert isinstance(datesAchats, dict), f"datesAchats doit être un dictionnaire: ({type(datesAchats).__name__})"
        assert isinstance(datesVentes, dict), f"datesVentes doit être un dictionnaire: ({type(datesVentes).__name__})"

        tickerAll = list(datesAchats.keys())
        # Récupérer toutes les dates d'achat et les trier
        startDate = min(list(set(date for ele in datesAchats.values() for date in ele.keys())))
        endDate = datetime.now()

        # Télécharger les prix de clôture pour chaque ticker
        prixTickers = self.DownloadTickersPrice(tickerAll, startDate, endDate)

        # Créer une DataFrame pour stocker les prix d'achat FIFO
        prixFIFO = pd.DataFrame(index=prixTickers.index, columns=tickerAll)
        ArgentsInvestisTickers = pd.DataFrame(index=prixTickers.index, columns=tickerAll)

        # Calculer les prix d'achat FIFO pour chaque ticker
        for ticker in tickerAll:
            datesInvestissementsPrix = datesAchats[ticker]
            datesVentesPrix = datesVentes[ticker]

            datesInvestissements = list(datesInvestissementsPrix.keys())
            datesVentesList = list(datesVentesPrix.keys())
            datesInvestissementsVentes = sorted(datesInvestissements + datesVentesList)

            totalQuantite = 0
            totalCout = 0

            for date in datesInvestissementsVentes:

                if date in datesInvestissements:
                    ajouterPrixArgentTicker = datesInvestissementsPrix[date]
                    prixAction = prixTickers.at[date, ticker]

                    quantiteAchetee = round(ajouterPrixArgentTicker) / prixAction

                    # Mettre à jour la quantité totale et le coût total
                    totalQuantite += quantiteAchetee
                    totalCout += ajouterPrixArgentTicker

                    # Calculer le prix d'achat FIFO en évitant la division par zéro
                    if totalQuantite > 0:
                        prixAchatFifo = totalCout / totalQuantite
                    else:
                        prixAchatFifo = 0

                    # Appliquer le prix FIFO à partir de la date d'achat
                    prixFIFO.loc[date:, ticker] = prixAchatFifo
                    ArgentsInvestisTickers.loc[date:, ticker] = totalCout

                # Pour la vente il faudrait calculer la plus value puis retirer l'argent vendu
                # Il faudra le faire dans une méthode à part
                # En attendant l'argent vendu correspond à 100% de l'argent investi
                if date in datesVentesList:
                    # enleverPrixArgentTicker = datesVentesPrix[date]

                    # totalCout -= enleverPrixArgentTicker

                    # # Réduis l'argent investi
                    # ArgentsInvestisTickers.loc[date:, ticker] = totalCout

                    # # Réinitialiser si tout a été vendu
                    # if ArgentsInvestisTickers.loc[date, ticker] <= 0:
                    #     totalQuantite = 0
                    #     totalCout = 0
                    #     ArgentsInvestisTickers.loc[date:, ticker] = 0

                    totalQuantite = 0
                    totalCout = 0
                    prixFIFO.loc[date:, ticker] = 0
                    ArgentsInvestisTickers.loc[date:, ticker] = 0


        return prixFIFO, prixTickers, ArgentsInvestisTickers

    @staticmethod
    def ArgentInvestiAll(datesAchats: dict, datesVentes: dict) -> float:
        """
        Calcule le montant total investi en agrégeant les achats et les ventes à partir de deux dictionnaires.

        Args:
            datesAchats (dict): Dictionnaire contenant les informations d'achat pour chaque ticker, où chaque clé est un ticker et la valeur est le montant investi.
            datesVentes (dict): Dictionnaire contenant les informations de vente pour chaque ticker, où chaque clé est un ticker et la valeur est le montant récupéré.

        Returns:
            float: Montant total investi, arrondi au montant le plus proche.
        """

        assert isinstance(datesAchats, dict), f"datesAchats doit être un dictionnaire: ({type(datesAchats).__name__})"
        assert isinstance(datesVentes, dict), f"datesVentes doit être un dictionnaire: ({type(datesVentes).__name__})"

        argentAchats = sum(argent for achatsTicker in datesAchats.values() for argent in achatsTicker.values())
        argentVentes = sum(argent for ventesTicker in datesVentes.values() for argent in ventesTicker.values())

        return round(argentAchats - argentVentes)
    ######################################

    ########## REPLICATION ##########
    def ReplicationDeMonPortefeuille(self) -> None:
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        datesAchats = self.RecuperationTickerBuySell("achats")
        datesVentes = self.RecuperationTickerBuySell("ventes")
        argentInvestiAll = self.ArgentInvestiAll(datesAchats, datesVentes)

        startDate = min(list(set(date for ele in datesAchats.values() for date in ele.keys())))
        endDate = datetime.today()
        tickersAll = [ticker for portfolio in self.portfolioPercentage for ticker in portfolio[0].keys()]
        prixTickers = self.DownloadTickersPrice(tickersAll, startDate, endDate)

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " Réplication"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            prixFIFO, ArgentsInvestisTickers = self.CalculerPrixAchatFIFO_ReplicationDeMonPortefeuille(tickers, prixTickersFiltree, portfolio, datesAchats, datesVentes)
            evolutionPourcentageTickers = self.EvolutionPourcentageTickers(prixFIFO, prixTickersFiltree)
            evolutionPrixBrutTickers, evolutionPrixBrutPortefeuille, evolutionPrixNetTickers, evolutionPrixNetPortefeuille = self.EvolutionPrixTickersPortefeuille(evolutionPourcentageTickers, ArgentsInvestisTickers, {})

            # On stock les DataFrames
            self.pourcentagePortefeuille[nomPortefeuille] = self.EvolutionPourcentagePortefeuille(evolutionPrixNetPortefeuille, argentInvestiAll)
            self.prixNetPortefeuille[nomPortefeuille] = evolutionPrixNetPortefeuille
            self.prixBrutPortefeuille[nomPortefeuille] = evolutionPrixBrutPortefeuille
            self.pourcentageTickers[nomPortefeuille] = evolutionPourcentageTickers
            self.prixNetTickers[nomPortefeuille] = evolutionPrixNetTickers
            self.prixBrutTickers[nomPortefeuille] = evolutionPrixBrutTickers
            self.dividendesTickers[nomPortefeuille] = self.EvolutionDividendesPortefeuille(evolutionPrixBrutTickers, prixTickersFiltree)
            self.pourcentageMoisPortefeuille[nomPortefeuille] = self.EvolutionPourcentageMois(evolutionPrixBrutPortefeuille, self.SommeInvestissementParDate(datesAchats), self.SommeInvestissementParDate(datesVentes))

    def CalculerPrixAchatFIFO_ReplicationDeMonPortefeuille(self, tickers: list, prixTickers: pd.DataFrame, portefeuille: list, datesAchats: dict, datesVentes: dict) -> tuple:
        """
        Calcule les prix d'achat FIFO (First In First Out) pour les actions basées sur les dates d'achat et les prix de clôture.

        Args:
            tickers (list): Liste contenant le nom des tickers au format string.
            prixTickers (pd.DataFrame): DataFrame contenant les prix actuels des tickers.
            portefeuille (list): Liste contenant deux éléments:
                - un dictionnaire avec les allocations pour chaque ticker,
                - un float ou int représentant le montant à investir.
            datesAchats (dict): Dictionnaire contenant les dates d'achat pour chaque ticker, où chaque clé est un ticker et la valeur est un dictionnaire avec des dates comme clés et montants d'achat comme valeurs.
            datesVentes (dict): Dictionnaire contenant les dates de vente et les prix associés pour chaque ticker, où chaque clé est un ticker et la valeur est un dictionnaire avec les dates comme clés et les prix comme valeurs.

        Returns:
            tuple: Un tuple contenant trois DataFrames :
                - prixFIFO : DataFrame des prix d'achat FIFO pour chaque ticker.
                - ArgentsInvestisTickers : DataFrame des coûts totaux d'achat pour chaque ticker.
        """
        assert isinstance(tickers, list), "tickers doit être une liste."
        assert all(isinstance(ticker, str) for ticker in tickers), "Chaque élément dans tickers doit être une chaîne de caractères."

        # Vérification de portefeuille
        assert isinstance(portefeuille, list) and len(portefeuille) == 3, "portefeuille doit être une liste contenant un dictionnaire, un montant et une chaîne de caractère."
        assert isinstance(portefeuille[0], dict), "Le premier élément du portefeuille doit être un dictionnaire."
        assert isinstance(portefeuille[1], (int, float)), "Le deuxième élément du portefeuille doit être un montant (int ou float)."
        assert isinstance(portefeuille[2], str), "Le troisième élément du portefeuille doit être une chaîne de caractère (str)."

        assert isinstance(prixTickers, pd.DataFrame), f"prixTickers doit être un DataFrame: ({type(prixTickers).__name__})"
        assert isinstance(datesAchats, dict), f"datesAchats doit être un dictionnaire: ({type(datesAchats).__name__})"
        assert isinstance(datesVentes, dict), f"datesVentes doit être un dictionnaire: ({type(datesVentes).__name__})"

        datesInvestissementsPrix = self.SommeInvestissementParDate(datesAchats)
        datesVentesPrix = self.SommeInvestissementParDate(datesVentes)
        datesInvestissementsPrix = dict(sorted(datesInvestissementsPrix.items()))
        datesVentesPrix = dict(sorted(datesVentesPrix.items()))

        datesInvestissements = list(datesInvestissementsPrix.keys())
        datesVentes = list(datesVentesPrix.keys())
        datesInvestissementsVentes = sorted(datesInvestissements + datesVentes)

        # Créer une DataFrame pour stocker les prix d'achat FIFO
        prixFIFO = pd.DataFrame(index=prixTickers.index, columns=tickers)
        ArgentsInvestisTickers = pd.DataFrame(index=prixTickers.index, columns=tickers)

        # Calculer les prix d'achat FIFO pour chaque ticker
        for ticker in tickers:
            totalQuantite = 0
            totalCout = 0
            argentInvestisEnTout = 0

            for date in datesInvestissementsVentes:

                if date in datesInvestissements:
                    ajouterPrixArgentTicker = (datesInvestissementsPrix[date] * portefeuille[0][ticker] / 100)
                    quantiteAchetee = round(ajouterPrixArgentTicker) / prixTickers.at[date, ticker]

                    # Mettre à jour la quantité totale et le coût total
                    totalQuantite += quantiteAchetee
                    totalCout += ajouterPrixArgentTicker
                    argentInvestisEnTout += ajouterPrixArgentTicker

                    # Calculer le prix d'achat FIFO en évitant la division par zéro
                    if totalQuantite > 0:
                        prixAchatFifo = totalCout / totalQuantite
                    else:
                        prixAchatFifo = 0

                    prixFIFO.loc[date:, ticker] = prixAchatFifo
                    ArgentsInvestisTickers.loc[date:, ticker] = argentInvestisEnTout

                if date in datesVentes:
                    enleverPrixArgentTicker = (datesVentesPrix[date] * portefeuille[0][ticker] / 100)
                    quantiteVendue = round(enleverPrixArgentTicker) / prixTickers.at[date, ticker]

                    # Mettre à jour la quantité et le coût total
                    totalQuantite -= quantiteVendue
                    totalCout -= quantiteVendue * prixAchatFifo if totalQuantite > 0 else totalCout
                    argentInvestisEnTout -= enleverPrixArgentTicker

                    if totalQuantite > 0:
                        prixAchatFifo = totalCout / totalQuantite
                    else:
                        prixAchatFifo = 0  # Reset des valeurs si la quantité devient nulle

                    prixFIFO.loc[date:, ticker] = prixAchatFifo
                    ArgentsInvestisTickers.loc[date:, ticker] = argentInvestisEnTout if argentInvestisEnTout > 0 else 0

                    # Réinitialisation si toutes les actions ont été vendues
                    if totalQuantite <= 0:
                        totalQuantite = 0
                        totalCout = 0
                        prixFIFO.loc[date:, ticker] = 0
                        ArgentsInvestisTickers.loc[date:, ticker] = 0

        return prixFIFO, ArgentsInvestisTickers
    #################################

    ########## DCA ##########
    def DollarCostAveraging(self) -> None:
        """
        Cette méthode permet de simuler un investissement en Dollar Cost Average (DCA) en fonction de différents portefeuilles.

        Explication:
            L’investissement en DCA (Dollar-Cost Averaging) est une stratégie simple mais efficace,
            qui consiste à investir régulièrement des montants fixes dans un actif financier, indépendamment de son prix.
            Plutôt que d'essayer de deviner le meilleur moment pour investir, le DCA permet d'acheter des parts de façon continue,
            réduisant l'impact des fluctuations du marché.
        """

        tickersAll = [ticker for portfolio in self.portfolioPercentage for ticker in portfolio[0].keys()]
        startDate = self.pourcentagePortefeuille.index[0] # Ayant déjà calculé mon portefeuille
        endDate = datetime.today()

        prixTickers = self.DownloadTickersPrice(tickersAll, startDate, endDate)
        datesInvestissements = self.DatesInvesissementDCA_DCV(startDate, endDate)

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " DCA"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]
            argentInvestiAll = portfolio[1] * len(datesInvestissements)

            prixFIFO, ArgentsInvestisTickers, datesInvestirPrix = self.CalculerPrixAchatFIFO_DCA(tickers, prixTickersFiltree, datesInvestissements, portfolio)

            evolutionPourcentageTickers = self.EvolutionPourcentageTickers(prixFIFO, prixTickersFiltree)
            evolutionPrixBrutTickers, evolutionPrixBrutPortefeuille, evolutionPrixNetTickers, evolutionPrixNetPortefeuille = self.EvolutionPrixTickersPortefeuille(evolutionPourcentageTickers, ArgentsInvestisTickers, {})

            # On stock les DataFrames
            self.pourcentagePortefeuille[nomPortefeuille] = self.EvolutionPourcentagePortefeuille(evolutionPrixNetPortefeuille, argentInvestiAll)
            self.prixNetPortefeuille[nomPortefeuille] = evolutionPrixNetPortefeuille
            self.prixBrutPortefeuille[nomPortefeuille] = evolutionPrixBrutPortefeuille
            self.pourcentageTickers[nomPortefeuille] = evolutionPourcentageTickers
            self.prixNetTickers[nomPortefeuille] = evolutionPrixNetTickers
            self.prixBrutTickers[nomPortefeuille] = evolutionPrixBrutTickers
            self.dividendesTickers[nomPortefeuille] = self.EvolutionDividendesPortefeuille(evolutionPrixBrutTickers, prixTickersFiltree)
            self.pourcentageMoisPortefeuille[nomPortefeuille] = self.EvolutionPourcentageMois(evolutionPrixBrutPortefeuille, datesInvestirPrix, {})

    @staticmethod
    def DatesInvesissementDCA_DCV(startDate: str|datetime, endDate: str|datetime) -> list:
        """
        Extrait les dates de début de chaque mois dans la plage donnée entre startDate et endDate.

        Args:
            startDate (str | datetime): Date de début au format 'YYYY-MM-DD' ou un objet datetime.
            endDate (str | datetime): Date de fin au format 'YYYY-MM-DD' ou un objet datetime.

        Returns:
            list: Liste des dates de début de chaque mois sous forme de chaînes formatées 'YYYY-MM-DD'.
        """
        assert isinstance(startDate, (str, datetime)), "startDate doit être une chaîne de caractères ou un datetime"
        assert isinstance(endDate, (str, datetime)), "endDate doit être une chaîne de caractères ou un datetime"

        # Conversion en format datetime si nécessaire
        startDate = pd.to_datetime(startDate)
        endDate = pd.to_datetime(endDate)

        # Initialisation de la liste pour stocker les dates de début de chaque mois
        debutMois = []
        currentDate = startDate

        while currentDate <= endDate:
            # Ajouter la date de début du mois formatée
            debutMois.append(currentDate.strftime('%Y-%m-%d'))

            # Passer au mois suivant
            next_month = currentDate.month % 12 + 1
            next_year = currentDate.year + (currentDate.month // 12)
            currentDate = currentDate.replace(month=next_month, year=next_year, day=1)

        return debutMois

    @staticmethod
    def CalculerPrixAchatFIFO_DCA(tickers: list, tickerPriceDf: pd.DataFrame, datesInvestir: list, portefeuille: list) -> tuple:
        """
        Calcule les prix d'achat FIFO (First In First Out) pour les actions basées sur les dates d'achat et les prix de clôture, d'après la méthode d'investissement DCA.

        Args:
            tickers (list): Liste contenant le nom des tickers au format string.
            tickerPriceDf (pd.DataFrame): DataFrame contenant le prix de chaque ticker avec en colonne le nom des tickers et en index des dates au format 'YYYY-MM-DD'.
            datesInvestir (list): Liste contenant des dates au format 'YYYY-MM-DD'.
            portefeuille (list): Liste contenant deux éléments:
                - un dictionnaire avec les allocations pour chaque ticker,
                - un float ou int représentant le montant à investir.

        Returns:
            tuple: Un tuple contenant deux DataFrames:
                - prixFIFO : DataFrame des prix d'achat FIFO pour chaque ticker.
                - ArgentsInvestisTickers : DataFrame des coûts totaux d'achat pour chaque ticker.
                - datesInvestirPrix (dict): Dictionnaire contenant enclés des dates et en valeur des flottant ou des entiers.
        """

        # Vérification du type de tickers
        assert isinstance(tickers, list), "tickers doit être une liste."
        assert all(isinstance(ticker, str) for ticker in tickers), "Chaque élément dans tickers doit être une chaîne de caractères."

        # Vérification de tickerPriceDf
        assert isinstance(tickerPriceDf, pd.DataFrame), "tickerPriceDf doit être un DataFrame pandas."
        assert all(ticker in tickerPriceDf.columns for ticker in tickers), "Tous les tickers doivent être des colonnes dans tickerPriceDf."
        assert isinstance(tickerPriceDf.index, pd.DatetimeIndex), "Les index de tickerPriceDf doivent être de type DatetimeIndex."
        assert tickerPriceDf.apply(lambda col: col.apply(lambda x: isinstance(x, (float, int))).all()).all(), \
            "Toutes les valeurs dans tickerPriceDf doivent être des flottants ou des entiers."

        # Vérification de datesInvestir
        assert isinstance(datesInvestir, list), "datesInvestir doit être une liste."
        assert all(isinstance(date, str) and len(date) == 10 for date in datesInvestir), \
            "Chaque élément dans datesInvestir doit être une chaîne de caractères de date au format 'YYYY-MM-DD'."
        assert all(date in tickerPriceDf.index for date in datesInvestir), "Chaque date dans datesInvestir doit être présente dans les index de tickerPriceDf."

        # Vérification de portefeuille
        assert isinstance(portefeuille, list) and len(portefeuille) == 3, "portefeuille doit être une liste contenant un dictionnaire, un montant et une chaîne de caractère."
        assert isinstance(portefeuille[0], dict), "Le premier élément du portefeuille doit être un dictionnaire."
        assert isinstance(portefeuille[1], (int, float)), "Le deuxième élément du portefeuille doit être un montant (int ou float)."
        assert isinstance(portefeuille[2], str), "Le troisième élément du portefeuille doit être une chaîne de caractère (str)."

        # On trie les dates de la plus ancienne vers la plus récente
        datesInvestir.sort()

        # Créer une DataFrame pour stocker les prix d'achat FIFO
        prixFIFO = pd.DataFrame(index=tickerPriceDf.index, columns=tickers)
        ArgentsInvestisTickers = pd.DataFrame(index=tickerPriceDf.index, columns=tickers)

        # Calculer les prix d'achat FIFO pour chaque ticker
        for ticker in tickers:
            totalQuantite = 0
            totalCout = 0
            ajouterPrixArgentTicker = (portefeuille[1] * portefeuille[0][ticker] / 100)

            for date in datesInvestir:
                prixAction = tickerPriceDf.at[date, ticker]
                quantiteAchetee = ajouterPrixArgentTicker / prixAction

                # Mettre à jour la quantité totale et le coût total
                totalQuantite += quantiteAchetee
                totalCout += ajouterPrixArgentTicker

                # Calculer le prix d'achat FIFO
                prixAchatFIFO = totalCout / totalQuantite

                # Appliquer le prix FIFO à partir de la date d'achat
                prixFIFO.loc[date:, ticker] = prixAchatFIFO
                ArgentsInvestisTickers.loc[date:, ticker] = totalCout

        # Avec un investissement en DCA on investit la même somme tous les mois
        datesInvestirPrix = {date: portefeuille[1] for date in datesInvestir}

        return prixFIFO, ArgentsInvestisTickers, datesInvestirPrix
    #########################
    #######################################################



    #################### GRAPHIQUES ####################
    def PlotlyInteractive(self, nomDossier: str, nomFichier: str) -> None:
        """
        Crée un graphique interactif utilisant Plotly pour visualiser différents aspects de l'évolution du portefeuille en l'enregistrant dans un fichier html.

        Args:
            nomDossier (str): Chemin vers le dossier où sauvegarder le fichier de sortie.
            nomFichier (str): Nom du fichier de sortie (doit avoir une extension .html).
        """
        assert isinstance(nomDossier, str), "nomDossier doit être une chaîne de caractères"
        assert os.path.exists(nomDossier), f"Le chemin '{nomDossier}' n'existe pas"

        assert isinstance(nomFichier, str), f"nomFichier doit être une chaîne de caractères: ({nomFichier})"
        assert nomFichier.endswith('.html'), f"Le fichier {nomFichier} n'a pas l'extension .html."

        portefeuillesGraphiques = []

        # Ajout des graphiques
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.pourcentagePortefeuille, "Progression en pourcentage de chaque portefeuille", "%"))
        portefeuillesGraphiques.append(self.GraphiqueHeatmapPourcentageParMois(self.pourcentageMoisPortefeuille))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.pourcentageTickers, "Progression en pourcentage pour chaque ticker", "%"))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.prixNetTickers, "Progression en euro pour chaque ticker", "€"))
        portefeuillesGraphiques.append(self.GraphiqueDividendesParAction(self.dividendesTickers))
        portefeuillesGraphiques.append(self.GraphiqueTreemapPortefeuille(self.prixBrutTickers))
        portefeuillesGraphiques.append(self.GraphiqueSunburst(self.prixBrutTickers))

        # Sauvegarde des graphiques dans un fichier HTML
        self.SaveInFile(portefeuillesGraphiques, (nomDossier + nomFichier))


    ########## Graphique en Histogramme ##########
    def GraphiqueDividendesParAction(self, portefeuilles: dict) -> go.Figure:
        """
        Trace un graphique de dividendes par action pour différents portefeuilles avec un menu pour choisir le portefeuille.

        Args:
            portefeuilles (dict): Dictionnaire contenant les noms des portefeuilles comme clés et
                                les DataFrames correspondants comme valeurs. Chaque DataFrame doit
                                contenir les années comme index, les noms des actions comme colonnes,
                                et les montants de dividendes (float) comme valeurs.

        Returns:
            go.Figure: Le graphique Plotly interactif avec un menu de sélection de portefeuilles.
        """
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        for key, df in portefeuilles.items():
            assert isinstance(df, pd.DataFrame), f"Les valeurs de 'portefeuilles' doivent être des DataFrames (erreur pour '{key}')."
            assert all(np.issubdtype(dtype, np.number) for dtype in df.dtypes), f"Toutes les colonnes du DataFrame de '{key}' doivent contenir des valeurs numériques."

        colors = [
            "#C70039",  # Rouge cerise
            "#335BFF",  # Bleu vif
            "#FF33B5",  # Rose fuchsia
            "#FF8D33",  # Orange vif
            "#FFC300",  # Jaune doré
            "#33A1FF",  # Bleu ciel
            "#81C784",  # Vert clair
            "#5733FF",  # Violet
            "#FFD54F",  # Jaune foncé
            "#BA68C8",  # Violet clair
            "#4DB6AC",  # Turquoise
            "#33FF57",  # Vert lime
            "#FFB74D",  # Orange doux
            "#FF5733",  # Rouge vif
            "#FFAB40",  # Orange vif
            "#FF7043",  # Rouge saumon
            "#64B5F6",  # Bleu pastel
            "#DCE775",  # Vert pastel
            "#A1887F",  # Marron clair
            "#F0E68C",  # Jaune kaki
        ]

        fig = go.Figure()
        title = "Dividende par action"
        buttons = []
        tracesCount = 0  # Compte du nombre total de traces ajoutées

        # Suppression des entrées avec des DataFrames contenant uniquement des zéros
        filteredDict = {key: df for key, df in portefeuilles.items() if not (df == 0).all().all()}

        # Création de traces pour chaque portefeuille
        for i, (nomPortefeuille, df) in enumerate(filteredDict.items()):
            nbVersementDividendesParAnnee = self.CountDividendsByYear(df.copy())

            # Regrouper par année et calculer la somme
            dataFrameAnnuel = df.resample('YE').sum()
            # Supprimer les lignes dont toutes les colonnes sont égales à zéro
            dataFrameAnnuel = dataFrameAnnuel[(dataFrameAnnuel != 0).any(axis=1)]
            # Modifier l'index pour qu'il ne contienne que l'année
            dataFrameAnnuel.index = dataFrameAnnuel.index.year

            # Calcul de la somme de chaque colonne
            sommeColonnes = dataFrameAnnuel.iloc[-1]
            # Tri des noms de colonnes en ordre alphabétique
            sortedColumns = sommeColonnes.index.sort_values()
            # Réorganisation du DataFrame en utilisant l'ordre trié
            dataFrameAnnuel = dataFrameAnnuel[sortedColumns]

            visibility = [False] * len(fig.data)
            # Filtrer les colonnes dont la somme est supérieure à zéro
            dataFrameAnnuel = dataFrameAnnuel.loc[:, dataFrameAnnuel.sum() > 0]
            nbTickers = len(dataFrameAnnuel.columns)
            if nbTickers <= 2:
                width = 0.4
            elif nbTickers <= 3:
                width = 0.3
            elif nbTickers <= 6:
                width = 0.2
            elif nbTickers <= 10:
                width = 0.2
            else:
                width = 0.1
                if nbTickers > 15:
                    # Calculer la somme de chaque colonne
                    sommeColonnes = dataFrameAnnuel.sum()
                    # Obtenir les 15 colonnes avec les sommes les plus élevées
                    colonnesSelectionnees = sommeColonnes.nlargest(15).index
                    # Filtrer le DataFrame pour ne garder que ces colonnes
                    dataFrameAnnuel = dataFrameAnnuel[colonnesSelectionnees]
                    title += " (seulement 15 actions)"


            for j, col in enumerate(dataFrameAnnuel.columns):
                # Vérifier si l'action a versé des dividendes
                if dataFrameAnnuel[col].sum() != 0:
                    # Ajouter une trace pour l'action courante
                    fig.add_trace(go.Bar(
                        x=dataFrameAnnuel.index,
                        y=dataFrameAnnuel[col],
                        name=f"{col}",
                        marker=dict(color=colors[j % len(colors)]),
                        width=width,
                        visible=(i == 0),  # Rendre visible seulement les traces du premier portefeuille au départ
                        text=[f"{val:.2f} €" if pd.notna(val) and val != 0 else "" for val in dataFrameAnnuel[col]],
                        textposition='outside',
                        hoverinfo='text',
                        hovertext=[
                            f"Ticker: {col}<br>Montant: {val:.2f} €<br>Nombre de dates de distribution des dividendes: {nbVersementDividendesParAnnee[year][col]}<br>Année: {year}"
                            if pd.notna(val) and val != 0 else ""
                            for year, val in zip(dataFrameAnnuel.index, dataFrameAnnuel[col])
                        ],
                        hoverlabel=dict(
                            bgcolor=colors[j % len(colors)],  # Couleur de fond
                            font=dict(color="white")  # Couleur du texte en blanc
                        ),
                        textfont=dict(color=colors[j % len(colors)], size=12, family="Arial")
                    ))
                    visibility.append(True)  # Ajouter True pour la trace actuelle
                    tracesCount += 1


            # Ajouter False pour les traces suivantes (ajoutées après ce portefeuille)
            visibility += [False] * (len(fig.data) - len(visibility))

            # Ajouter un bouton pour chaque portefeuille avec sa liste de visibilité
            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[{"visible": visibility},
                    {"title": f"Dividende par action"}],
            ))


        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(buttons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        # Mise à jour de la disposition du graphique
        fig.update_layout(
            title=title,
            xaxis=dict(
                title='Années',
                tickmode='array',
                tickvals=dataFrameAnnuel.index,  # Utiliser les années comme valeurs
                ticktext=[str(year) for year in dataFrameAnnuel.index],  # Convertir en chaîne pour l'affichage
                color='white'
            ),
            yaxis=dict(
                title='Montant des dividendes (€)',
                color='white',
                ticksuffix="€",
            ),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
            legend=dict(title="Tickers", font=dict(color='white')),
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "x": 0,
                "xanchor": "left",
                "y": 1,
                "yanchor": "top"
            }]
        )

        return fig
    ##############################################

    ########## Graphique Circulaire ##########
    @staticmethod
    def GraphiqueDiagrammeCirculairePortefeuille(portefeuilles: dict) -> go.Figure:
        """
        Génère un diagramme circulaire interactif avec un menu déroulant permettant de sélectionner
        la répartition des actions pour différents portefeuilles, basée sur les valeurs les plus récentes
        disponibles dans chaque DataFrame.

        Args:
            portefeuilles (dict): Dictionnaire où chaque clé est un nom de portefeuille (str),
                                et chaque valeur est un DataFrame contenant les valeurs des actions par entreprise,
                                avec les dates en index.

        Returns:
            go.Figure: Figure Plotly contenant un diagramme circulaire interactif avec un menu déroulant pour la sélection des portefeuilles.
        """
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans 'portefeuilles' doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame doit avoir un index de type datetime."

        # Créer une figure vide
        fig = go.Figure()

        # Itérer à travers chaque portefeuille pour ajouter les données au diagramme circulaire
        for i, (nomPortefeuille, df) in enumerate(portefeuilles.items()):
            assert not df.empty, f"Le DataFrame pour '{nomPortefeuille}' ne doit pas être vide."

            # Sélection des données les plus récentes
            derniere_valeur = df.iloc[-1]
            assert derniere_valeur.notna().all(), f"Le DataFrame pour '{nomPortefeuille}' contient des valeurs manquantes pour la ligne la plus récente."

            # Créer un DataFrame pour le diagramme circulaire
            pie_df = pd.DataFrame({
                'Entreprise': derniere_valeur.index,
                'Valeur': derniere_valeur.values
            })

            # Ajouter le diagramme circulaire pour ce portefeuille
            fig.add_trace(
                go.Pie(
                    labels=pie_df['Entreprise'],
                    values=pie_df['Valeur'],
                    name=nomPortefeuille,
                    visible=(i == 0)  # Seul le premier portefeuille est visible par défaut
                )
            )

        # Créer les boutons du menu déroulant
        buttons = []
        for i, nomPortefeuille in enumerate(portefeuilles.keys()):
            # Créer un bouton pour chaque portefeuille
            visible = [False] * len(portefeuilles)
            visible[i] = True
            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[
                    {"visible": visible},
                    {"title": f"Répartition des actions pour le portefeuille : {nomPortefeuille}"}
                ]
            ))

        # Mise à jour de la mise en page avec le menu déroulant
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title_text=f"Répartition des actions pour le portefeuille : {list(portefeuilles.keys())[0]}"
        )

        fig.update_traces(textposition='inside', textinfo='percent+label')

        return fig

    @staticmethod
    def GraphiqueSunburst(portefeuilles: dict) -> go.Figure:
        """
        Génère un graphique Sunburst pour chaque portefeuille spécifié dans le dictionnaire
        et combine tous les graphiques en une seule figure avec un menu déroulant pour sélectionner
        chaque portefeuille.

        Args:
            portefeuilles (dict): Dictionnaire de portefeuilles où chaque clé est un nom de portefeuille (str)
                                et chaque valeur est un DataFrame contenant les valeurs par entreprise avec les
                                dates en index.

        Returns:
            go.Figure: Figure Plotly avec un menu déroulant pour sélectionner les portefeuilles.
        """
        # Vérifications des arguments
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans 'portefeuilles' doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame doit avoir un index de type datetime."

        # Créer une figure vide
        figCombined = go.Figure()

        # Créer un bouton pour chaque portefeuille
        buttons = []
        for i, (name, df) in enumerate(portefeuilles.items()):
            labels = [name]
            parents = ['']
            values = [df.iloc[-1].sum()]  # Somme des valeurs du dernier jour
            hovertext = [f"{name}<br>Valeur totale: {values[0]:.2f}€"]

            # Ajouter chaque action en tant que catégorie
            totalValeur = df.iloc[-1].sum()
            for ticker, valeur in df.iloc[-1].items():
                # Pour enlever les tickers vendues entièrement
                if valeur != 0:
                    labels.append(ticker)
                    parents.append(name)
                    values.append(valeur)
                    percent = (valeur / totalValeur) * 100
                    hovertext.append(f"{ticker}<br>Valeur: {valeur:.2f}<br>Pourcentage: {percent:.2f}%")

            # Créer une trace Sunburst pour le portefeuille courant
            figCombined.add_trace(go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues='total',
                textinfo='label+percent entry',
                hoverinfo='text',
                hovertext=hovertext,
                insidetextfont=dict(color='white'),  # Texte interne (label + pourcentage) en blanc
                hoverlabel=dict(
                    font=dict(color='white')
                ),
                marker=dict(
                    line=dict(color='white', width=1)  # Ligne de séparation blanche entre les sections
                ),
                visible=(i == 0)  # Rendre visible uniquement le premier portefeuille au départ
            ))

            # Créer un bouton pour ce portefeuille
            buttons.append(
                {
                    'label': name,
                    'method': 'update',
                    'args': [
                        {'visible': [j == i for j in range(len(portefeuilles))]},  # Masquer tous sauf le sélectionné
                        {'title': f'Portefeuille: {name}'}  # Changer le titre
                    ]
                }
            )

        # Configurer le menu déroulant dans la figure combinée
        figCombined.update_layout(
            updatemenus=[{
                'buttons': buttons,
                'direction': 'down',
                'showactive': True,
            }],
            title_text=f'Sélectionnez un portefeuille',
            showlegend=False,
            margin=dict(l=30, r=30, t=50, b=50),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return figCombined
    ##########################################

    ########## Graphique Linéaire ##########
    @staticmethod
    def GraphiqueLineairePortefeuilles(df: pd.DataFrame, title="", suffixe: str="") -> go.Figure:
        """
        Génère un graphique linéaire interactif avec Plotly, basé sur les données contenues dans un DataFrame.
        Pour chaque colonne de `df`, une courbe distincte est tracée, permettant de visualiser l'évolution des
        séries de données dans le temps. Le graphique est coloré de manière esthétique avec une palette de couleurs
        prédéfinie, et le fond est personnalisé pour une meilleure lisibilité.

        Args:
            df (pd.DataFrame): DataFrame contenant les données à tracer. Les colonnes représentent différentes séries de données.
            title (str): Titre du graphique.
            suffixe (str): Suffixe à ajouté sur l'axe des ordonnées.

        Returns:
            go.Figure: Le graphique Plotly
        """
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame: ({type(df).__name__})"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title).__name__})"
        assert isinstance(suffixe, str), f"devise doit être une chaîne de caractères: ({type(suffixe).__name__})"

        fig = go.Figure()
        colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        for i, column in enumerate(df.columns):
            colorIndex = i % len(colors)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                mode='lines',
                name=column,
                line=dict(color=colors[colorIndex], width=2.5),
                hovertemplate='Date: %{x}<br>Pourcentage: %{y:.2f}' + suffixe + '<extra></extra>'
            ))

        fig.update_layout(
            title=title,
            xaxis=dict(
                title='Date',
                titlefont=dict(size=14, color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                title='Valeur en %',
                titlefont=dict(size=14, color='white'),
                ticksuffix=suffixe,
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                x=0.01, y=0.99,
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    
    @staticmethod
    def GraphiqueLineaireTickers(dataDict: dict, title="", suffixe: str="") -> go.Figure:
        """
        Génère un graphique linéaire interactif avec Plotly, permettant de visualiser l'évolution des
        données pour différents portefeuilles et tickers. Chaque portefeuille est représenté par un
        DataFrame dans le dictionnaire d'entrée, et un menu déroulant permet de sélectionner le portefeuille
        à afficher.

        Args:
            dataDict (dict): Dictionnaire contenant des DataFrames. La clé représente le nom du portefeuille,
                            et chaque DataFrame contient les données à tracer, avec les dates en index et
                            les tickers en colonnes.
            title (str): Titre du graphique.
            suffixe (str): Suffixe à ajouté sur l'axe des ordonnées.

        Returns:
            go.Figure: Le graphique Plotly avec un menu déroulant pour la sélection des portefeuilles.
        """
        assert isinstance(dataDict, dict), f"dataDict doit être un dictionnaire: ({type(dataDict).__name__})"
        assert all(isinstance(df, pd.DataFrame) for df in dataDict.values()), "Chaque valeur de dataDict doit être un DataFrame"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title).__name__})"
        assert isinstance(suffixe, str), f"devise doit être une chaîne de caractères: ({type(suffixe).__name__})"

        fig = go.Figure()
        colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        # Ajout de chaque portefeuille comme une option du menu déroulant
        dropdownButtons = []
        tracesCount = 0  # Compte du nombre total de traces ajoutées
        for portfolioIndex, (portfolioName, df) in enumerate(dataDict.items()):
            # On trie le dataFrame pour récupérer les tickers qui ne sont pas clôturés
            dfFiltré = df.loc[:, df.iloc[-1].notna()]
            visibility = [False] * len(fig.data)
            # Création des courbes pour chaque ticker de ce portefeuille
            for i, column in enumerate(dfFiltré.columns):
                colorIndex = i % len(colors)
                fig.add_trace(go.Scatter(
                    x=dfFiltré.index,
                    y=dfFiltré[column],
                    mode='lines',
                    name=f"{column}",
                    line=dict(color=colors[colorIndex], width=1.5),
                    hovertemplate='Date: %{x}<br>Pourcentage: %{y:.2f}' + suffixe + '<extra></extra>',
                    visible=(portfolioIndex == 0)  # Visible uniquement pour le premier portefeuille
                ))
                visibility.append(True)  # Ajouter True pour la trace actuelle
                tracesCount += 1

            # Ajouter False pour les traces suivantes (ajoutées après ce portefeuille)
            visibility += [False] * (len(fig.data) - len(visibility))

            dropdownButtons.append(dict(
                label=portfolioName,
                method="update",
                args=[{"visible": visibility},
                    {"title": f"{title} - {portfolioName}"}]
            ))

        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(dropdownButtons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        # Configuration du layout et des menus déroulants
        fig.update_layout(
            title=title + f" - {next(iter(dataDict))}",
            updatemenus=[{
                "buttons": dropdownButtons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            xaxis=dict(
                titlefont=dict(size=14, color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                titlefont=dict(size=14, color='white'),
                ticksuffix=suffixe,
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    ########################################

    ########## Graphique Tableaux ##########
    @staticmethod
    def GraphiqueTableauPortefeuille(df: pd.DataFrame) -> go.Figure:
        """
        Génère une figure Plotly affichant un tableau contenant les données d'un portefeuille,
        avec un menu déroulant permettant de sélectionner le portefeuille souhaité parmi les colonnes du DataFrame.

        Args:
            df (pd.DataFrame): DataFrame contenant les données des portefeuilles avec les dates en index et
                            les noms de portefeuilles en colonnes.

        Returns:
            go.Figure: Figure Plotly contenant un tableau des données du portefeuille sélectionné,
                    avec un menu déroulant pour sélectionner le portefeuille.
        """
        # Vérification des types des arguments
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame."

        # Formatage de l'index de dates en 'YYYY-MM-DD'
        df.index = df.index.strftime('%Y-%m-%d')

        # Création des traces pour chaque portefeuille
        figures_data = []
        for portefeuille in df.columns:
            # Création de la table pour le portefeuille sélectionné
            figures_data.append(
                go.Table(
                    header=dict(values=['Date', portefeuille],
                                fill_color='paleturquoise',
                                align='left'),
                    cells=dict(values=[df.index, df[portefeuille].tolist()],
                            fill_color='lavender',
                            align='left')
                )
            )

        # Création de la figure avec la première vue par défaut
        fig = go.Figure(data=[figures_data[0]])

        # Création du menu déroulant
        buttons = [
            dict(label=portefeuille,
                method="update",
                args=[{"data": [figures_data[i]]},
                    {"title": f"Tableau des données pour le portefeuille : {portefeuille}"}])
            for i, portefeuille in enumerate(df.columns)
        ]

        # Mise à jour de la disposition pour inclure le menu
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "x": 0.5,
                "y": 1.15,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title=f"Tableau des données pour le portefeuille : {df.columns[0]}"
        )

        return fig
    #######################################

    ########## Graphique Treemap ##########
    @staticmethod
    def GraphiqueTreemapPortefeuille(portefeuilles: dict) -> go.Figure:
        """
        Génère un treemap interactif avec un menu déroulant pour sélectionner la répartition des actions
        dans différents portefeuilles basés sur les valeurs les plus récentes.

        Args:
            portefeuilles (dict): Dictionnaire où chaque clé est un nom de portefeuille (str)
                                et la valeur est un DataFrame contenant les valeurs des actions par entreprise
                                avec les dates en index.

        Returns:
            fig (go.Figure): Figure Plotly avec menu déroulant.
        """
        assert isinstance(portefeuilles, dict), "portefeuilles doit être un dictionnaire."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans portefeuilles doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame dans portefeuilles doit avoir un index de type datetime."

        # Créer une figure vide
        fig = go.Figure()

        # Itérer à travers chaque portefeuille pour ajouter les données au treemap
        for i, (nomPortefeuille, df) in enumerate(portefeuilles.items()):
            # Sélection des données les plus récentes
            derniere_valeur = df.iloc[-1]

            # Calcul de la valeur totale du portefeuille
            valeurTotale = derniere_valeur.sum()

            # Créer un DataFrame pour le treemap avec les pourcentages calculés
            treemapDf = pd.DataFrame({
                'Entreprise': derniere_valeur.index,
                'Valeur': derniere_valeur.values,
                'Pourcentage': (derniere_valeur / valeurTotale * 100).round(2)  # Calculer le pourcentage avec 2 décimales
            })

            # Ajouter une colonne texte avec des informations formatées
            treemapDf['text'] = treemapDf.apply(
                lambda row: f"{row['Entreprise']}<br>Répartition: {row['Pourcentage']:.2f}% <br>Valeur: {row['Valeur']:.2f}", axis=1
            )

            # Ajouter le treemap pour ce portefeuille
            fig.add_trace(
                go.Treemap(
                    labels=treemapDf['Entreprise'],
                    parents=[''] * len(treemapDf),
                    values=treemapDf['Valeur'],
                    visible=(i == 0),  # Seul le premier portefeuille est visible par défaut
                    text=treemapDf['text'],
                    textinfo='text',  # Utiliser les informations formatées comme texte
                    insidetextfont=dict(color='white'),  # Texte des labels en blanc
                    marker=dict(
                        line=dict(color='white', width=1)  # Bordure blanche autour des sections
                    ),
                    hoverlabel=dict(
                        font=dict(color='white')  # Texte au survol en blanc
                    ),
                    hovertemplate=(
                        "<b>%{label}</b><br>" +
                        "Répartition: %{customdata[0]:.2f}%" +  # Affiche le pourcentage avec 2 décimales
                        "Valeur: %{value:.2f}<br>"  # Affiche la valeur avec 2 décimales
                    ),
                    customdata=treemapDf[['Pourcentage']].values  # Passer les pourcentages comme données de survol
                )
            )

        # Créer les boutons du menu déroulant
        buttons = []
        for i, nomPortefeuille in enumerate(portefeuilles.keys()):
            # Créer un bouton pour chaque portefeuille
            visible = [False] * len(portefeuilles)
            visible[i] = True
            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[{"visible": visible},
                    {"title": f'Répartition des actions pour le portefeuille: {nomPortefeuille}'}]
            ))

        # Mise à jour de la mise en page avec le menu déroulant
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title_text=f'Répartition des actions pour le portefeuille: {list(portefeuilles.keys())[0]}',
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    #######################################

    ########## Graphique Heatmap ##########
    @staticmethod
    def GraphiqueHeatmapPourcentageParMois(df: pd.DataFrame) -> go.Figure:
        """
        Crée une heatmap représentant les pourcentages d'évolution mensuels d'un portefeuille
        avec un menu déroulant pour sélectionner la colonne à afficher.

        Args:
            df (pd.DataFrame): DataFrame contenant les pourcentages d'évolution,
                            indexé par date au format 'YYYY-MM'.

        Returns:
            fig (go.Figure): Figure Plotly
        """
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame"
        assert not df.empty, "Le DataFrame ne doit pas être vide"

        # Convertir l'index en DateTime si ce n'est pas déjà fait
        df.index = pd.to_datetime(df.index)

        # Créer de nouvelles colonnes pour les années et les mois
        df['Année'] = df.index.year
        df['Mois'] = df.index.month_name()

        # Tri des mois pour assurer l'ordre
        moisOrder = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']
        df['Mois'] = pd.Categorical(df['Mois'], categories=moisOrder, ordered=True)

        # Obtenir la liste des colonnes à inclure dans le menu déroulant
        portefeuilleColonnes = [col for col in df.columns if col not in ['Année', 'Mois']]

        # Créer une figure vide
        fig = go.Figure()

        # Ajouter une heatmap pour chaque colonne, en les masquant par défaut sauf la première
        for i, nomColonne in enumerate(portefeuilleColonnes):
            # Pivot du DataFrame pour la colonne courante
            heatmapData = df.pivot_table(index="Année", columns="Mois", values=nomColonne, observed=False).sort_index(ascending=True)

            # Calculer les valeurs minimales et maximales pour la colorisation
            zMin = heatmapData.min().min()
            zMax = heatmapData.max().max()

            # Préparer les valeurs de texte formatées pour les pourcentages
            text_values = heatmapData.apply(lambda col: col.map(lambda x: f'{x:.2f}%' if x != 0 and pd.notnull(x) else ''), axis=0)

            # Ajouter la trace de la heatmap
            fig.add_trace(go.Heatmap(
                z=heatmapData.values,
                x=heatmapData.columns,
                y=heatmapData.index,
                colorscale=[
                    [0, 'rgba(255, 0, 0, 0.7)'],
                    [0.5, 'rgba(144, 238, 144, 1)'],
                    [1, 'rgba(0, 128, 0, 1)']
                ],
                colorbar=dict(title="Pourcentage"),
                zmin=zMin,
                zmax=zMax,
                visible=i == 0,  # Visible uniquement pour la première colonne
                hovertemplate='Mois: %{x}<br>Année: %{y}<br>Pourcentage: %{z:.2f}%<extra></extra>',  # Modifications des étiquettes au survol
                text=text_values.values,  # Pour afficher les valeurs de pourcentage au centre
                texttemplate='%{text}',  # Formatage des valeurs à afficher
                textfont=dict(color='rgba(255, 255, 255, 0.5)'),  # Texte en blanc avec 50% de transparence
            ))

        # Créer le menu déroulant pour sélectionner la colonne
        buttons = []
        for i, nomColonne in enumerate(portefeuilleColonnes):
            buttons.append(dict(
                label=nomColonne,
                method="update",
                args=[{"visible": [j == i for j in range(len(portefeuilleColonnes))]},
                    {"title": f'Evolution mensuelle du portefeuille: {nomColonne}'}]
            ))

        # Configurer le layout de la figure
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title_text=f'Evolution mensuelle du portefeuille: {portefeuilleColonnes[0]}',
            xaxis_title='Mois',
            yaxis_title='Année',
            xaxis=dict(
                tickmode='array',
                tickvals=moisOrder,
                ticktext=moisOrder,
                showgrid=False,
                tickangle=45  # Orientation des étiquettes à 45 degrés
            ),
            yaxis=dict(tickmode='array', tickvals=df['Année'].unique(), showgrid=False),  # Suppression de la grille
            showlegend=False,
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    #######################################

    ########## ANNEXES ##########
    @staticmethod
    def CountDividendsByYear(dataFrame: pd.DataFrame) -> dict:
        """
        Compte le nombre de versements de dividendes pour chaque action par année.

        Args:
            dataFrame (pd.DataFrame): DataFrame contenant des dates comme index et des noms d'entreprises comme colonnes.
                                    Les valeurs représentent les montants de dividendes.

        Returns:
            dict: Dictionnaire avec pour clé l'année, et comme valeur un dictionnaire ayant pour clé le nom de l'action
                et pour valeur le nombre de versements de dividendes.
        """
        assert isinstance(dataFrame, pd.DataFrame), "Le paramètre 'dataFrame' doit être un DataFrame avec des dates en index et des noms d'actions en colonnes."
        assert pd.api.types.is_datetime64_any_dtype(dataFrame.index), "L'index du DataFrame doit être de type datetime."

        # Convertir les index en années pour faciliter l'agrégation
        dataFrame['Year'] = dataFrame.index.year

        # Initialiser le dictionnaire de résultats
        dividendsPerYear = {}

        # Parcourir les années distinctes dans le DataFrame
        for year in dataFrame['Year'].unique():
            # Sélectionner les lignes correspondant à l'année courante
            yearlyData = dataFrame[dataFrame['Year'] == year].drop(columns='Year')

            # Compter les versements de dividendes (les valeurs non nulles ou non nulles et non zéros)
            dividendsPerYear[year] = yearlyData.apply(lambda x: x[x != 0].count(), axis=0).to_dict()

        return dividendsPerYear
    #############################
    
    ########## SAUVEGARDER ##########
    @staticmethod
    def SaveInFile(figures: list, nomFichier: str) -> None:
        """
        Enregistre les graphiques générés dans un fichier HTML.

        Args:
            figures (list): Liste d'objets graphiques Plotly à enregistrer.
            nomFichier (str): Nom du fichier dans lequel enregistrer les graphiques HTML.
        """
        # Assertions pour valider les types des paramètres
        assert isinstance(figures, list), "figures doit être une liste"
        assert all(hasattr(fig, 'write_html') for fig in figures), "Chaque élément de figures doit avoir la méthode 'write_html'"
        assert isinstance(nomFichier, str), "nomFichier doit être une chaîne de caractères"

        with open(nomFichier, 'w') as f:
            for fig in figures:
                fig.write_html(f, include_plotlyjs='cdn')
    #################################
    ####################################################



    #################### SAUVEGARDER DATA ####################
    def EnregistrerDataFrameEnJson(self, cheminFichierJson: str) -> None:
        """
        Enregistre un DataFrame au format JSON dans le fichier spécifié, avec les dates comme clés et les montants comme valeurs.

        Args:
            cheminFichierJson (str): Le chemin du fichier JSON dans lequel enregistrer le DataFrame.
        """
        assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith(".json"), \
            f"cheminFichierJson doit être une chaîne se terminant par '.json', mais c'est {type(cheminFichierJson).__name__}."
        
        dataFrame = copy.deepcopy(self.prixBrutPortefeuille["Mon Portefeuille"])

        # Convertir l'index en dates au format string et les valeurs en dictionnaire
        dictData = dataFrame.reset_index()
        dictData.columns = ['Date', 'Montant']
        dictData['Date'] = dictData['Date'].dt.strftime('%Y-%m-%d')  # Convertir les dates au format 'YYYY-MM-DD'
        dictData = dictData.set_index('Date')['Montant'].to_dict()

        # Convertir le dictionnaire en JSON et l'enregistrer
        jsonData = pd.Series(dictData).to_json(orient='index', indent=2)

        # Écrire le JSON dans le fichier
        with open(cheminFichierJson, 'w', encoding="utf-8") as f:
            f.write(jsonData)
    ##########################################################

