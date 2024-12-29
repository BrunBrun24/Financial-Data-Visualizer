import yfinance as yf
import pandas as pd
from datetime import datetime
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
        repertoireJson (str): Répertoire contenant tous les fichiers JSON contenant les données nécessaire
    """

    def __init__(self, repertoireJson: str):
        """
        Initialise la classe avec les informations nécessaires pour la gestion des transactions et des fichiers.
        """
        assert isinstance(repertoireJson, str), f"repertoireJson doit être une chaîne de caractères: ({type(repertoireJson)})"
        assert os.path.isdir(repertoireJson), f"directory doit être un répertoire valide : ({repertoireJson})"

        self.repertoireJson = repertoireJson

        self.datesAchats = self.RecuperationTickerBuySell((repertoireJson + "/Transactions.json"), "achats")
        self.datesVentes = self.RecuperationTickerBuySell((repertoireJson + "/Transactions.json"), "ventes")
        self.startDate = self.PremiereDateDepot()
        self.endDate = datetime.today()
        self.argentInvesti = self.CalculateNetInvestment()

        self.tickersTWR = {}
        self.prixNetTickers = {}
        self.prixBrutTickers = {}
        self.dividendesTickers = {}
        
        self.portefeuilleTWR = pd.DataFrame()
        self.prixNetPortefeuille = pd.DataFrame()
        self.pourcentagesMensuelsPortefeuille = pd.DataFrame()

        self.fondsInvestis = pd.DataFrame()
        self.soldeCompteBancaire = pd.DataFrame()

        # Ajoute sur le graphique mon portefeuille
        self.MonPortefeuille()
        self.EnregistrerDataFrameEnJson("Bilan/Archives/Bourse/Portefeuille.json")

    def RecuperationTickerBuySell(self, fichierJsonAchatsVentes: str, objectif: str) -> dict:
        """
        Récupère les données de transactions par ticker depuis un fichier JSON.

        Args:
            fichierJsonAchatsVentes (str): Chemin vers le fichier JSON contenant les transactions.
            objectif (str): Clé dans le fichier JSON utilisée pour extraire les prix des transactions (ex: 'achats', 'ventes').

        Returns:
            dict: Un dictionnaire où chaque clé est un ticker, et chaque valeur est un dictionnaire contenant les dates et les prix.
        """
        assert isinstance(fichierJsonAchatsVentes, str), f"fichierJsonAchatsVentes doit être une chaîne de caractères: ({fichierJsonAchatsVentes})"
        assert os.path.exists(fichierJsonAchatsVentes) and fichierJsonAchatsVentes.endswith('.json'), f"Le fichier {fichierJsonAchatsVentes} n'existe pas ou n'a pas l'extension .json."

        data = self.ExtraireDonneeJson(fichierJsonAchatsVentes)

        transactionsDict = {}
        # Parcours des transactions pour chaque ticker
        for transaction in data.get('transactions', []):
            ticker = transaction.get('ticker')
            if ticker is None:
                continue

            transactionsDict[ticker] = {}
            # Extraction des données de transaction (dates et prix) en fonction de l'objectif
            for element in transaction.get(objectif, []):
                date = element.get('date')
                price = element.get('price')
                if date is not None and price is not None:
                    if pd.to_datetime(date) in transactionsDict[ticker]:
                        transactionsDict[ticker][pd.to_datetime(date)] += price
                    else:
                        transactionsDict[ticker][pd.to_datetime(date)] = price

        return transactionsDict

    def PremiereDateDepot(self) -> datetime:
        """
        Récupère la date de valeur la plus ancienne des dépôts d'espèces à partir des données JSON.

        Returns:
            datetime: La plus ancienne date de valeur parmi les dépôts d'espèces.
        """
        dataDepotEspeces = self.ExtraireDonneeJson((self.repertoireJson + "/Dépôts d'espèces.json"))
        assert isinstance(dataDepotEspeces, list), "Les données extraites doivent être une liste."
        
        # Récupération et conversion des dates de valeur
        dates = [pd.to_datetime(item['Date de valeur'], format='%Y-%m-%d') for item in dataDepotEspeces]
        return min(dates)

    def CalculateNetInvestment(self) -> float:
        """
        Calcule la somme totale des prix d'achat en soustrayant les prix de vente.

        Returns:
            float: La différence entre la somme des prix d'achat et la somme des prix de vente.
        """
        assert isinstance(self.datesAchats, dict), "datesAchats doit être un dictionnaire"
        assert isinstance(self.datesVentes, dict), "datesVentes doit être un dictionnaire"

        totalBuy = 0.0
        totalSell = 0.0

        # Calculer le total des prix d'achat
        for ticker, transactions in self.datesAchats.items():
            assert isinstance(transactions, dict), f"Les transactions pour {ticker} doivent être un dictionnaire"
            totalBuy += sum(transactions.values())

        # Calculer le total des prix de vente
        for ticker, transactions in self.datesVentes.items():
            assert isinstance(transactions, dict), f"Les transactions pour {ticker} doivent être un dictionnaire"
            totalSell += sum(transactions.values())

        # Calculer la différence
        return totalBuy - totalSell


    #################### SETTERS ####################
    def SetPortfolioPercentage(self, portfolioPercentage: list):
        assert isinstance(portfolioPercentage, list), "portfolioPercentage doit être une liste de portefeuilles."
        for portefeuille in portfolioPercentage:
            assert isinstance(portefeuille, list) and len(portefeuille) == 2, \
                "Chaque portefeuille doit être une liste contenant un dictionnaire et une chaîne de caractère."
            assert isinstance(portefeuille[0], dict), "Le premier élément du portefeuille doit être un dictionnaire des actions avec leurs pourcentages."
            assert isinstance(portefeuille[1], str), "Le deuxième élément du portefeuille doit être une chaîne de caractères représentant le nom du portefeuille."
            for ticker, pourcentage in portefeuille[0].items():
                assert isinstance(ticker, str), f"Chaque clé du dictionnaire (ticker) doit être une chaîne de caractères, mais '{ticker}' ne l'est pas."
                assert isinstance(pourcentage, (int, float)), f"Chaque valeur du dictionnaire (pourcentage) doit être un nombre (int ou float), mais '{pourcentage}' ne l'est pas."

        self.portfolioPercentage = portfolioPercentage
    #################################################



    #################### TÉLÉCHARGEMENT DES DONNÉES BOURSIÈRES ####################
    def DownloadTickersPrice(self, tickers: list) -> pd.DataFrame:
        """
        Télécharge les prix de clôture des actions spécifiées sur une période donnée.

        Args:
            tickers (list): Liste des symboles boursiers à télécharger.

        Returns:
            pd.DataFrame: Un DataFrame contenant les prix de clôture des actions spécifiées,
            avec les dates manquantes complétées et les prix éventuellement convertis en EUR.
        """
        assert isinstance(tickers, list) and all(isinstance(ticker, str) for ticker in tickers), "tickers doit être une liste de chaînes de caractères"

        startDate = self.startDate
        endDate = self.endDate

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
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame: ({type(df)})"
        assert isinstance(startDate, (str, datetime)), f"startDate doit être une chaîne de caractères: ({type(startDate)})"
        assert isinstance(endDate, (str, datetime)), f"endDate doit être une chaîne de caractères: ({type(endDate)})"
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
        dfFiltree = dfFiltree.divide(tauxDeConvertionDf["EURUSD=X"], axis=0)

        # Remplacer les valeurs dans df
        colonnesCommunes = df.columns.intersection(dfFiltree.columns)
        df[colonnesCommunes] = dfFiltree[colonnesCommunes]

        return df
    ###############################################################################



    #################### PORTEFEUILLE, TICKERS ####################
    ########## Pourcentage ##########
    @staticmethod
    def CalculerEvolutionPourcentageMois(evolutionArgenstInvestis: pd.Series, datesInvestissementsPrix: dict, datesVentesPrix: dict) -> pd.DataFrame:
        """
        Calcule l'évolution mensuelle en pourcentage du portefeuille en utilisant les dates d'investissement pour un calcul
        précis du montant total investi et retourne un DataFrame.

        Args:
            evolutionArgenstInvestis (pd.DataFrame): DataFrame contenant les valeurs journalières du portefeuille
                                                            avec une colonne 'Portefeuille' et un index de dates.
            datesInvestissementsPrix (dict): Dictionnaire avec des clés représentant des dates (de type datetime ou string 'YYYY-MM-DD')
                                            et des valeurs en entier ou flottant représentant le prix de l'investissement à cette date.
            datesVentesPrix (dict): Dictionnaire avec des clés représentant des dates (de type datetime ou string 'YYYY-MM-DD')
                                    et des valeurs en entier ou flottant représentant le prix de l'investissement à cette date.

        Returns:
            pd.DataFrame: Un DataFrame avec les dates au format 'YYYY-MM' comme index et l'évolution mensuelle
                            en pourcentage dans une colonne 'EvolutionPourcentage'.
        """
        assert isinstance(evolutionArgenstInvestis, pd.Series), "evolutionArgenstInvestis doit être un DataFrame"
        assert pd.api.types.is_datetime64_any_dtype(evolutionArgenstInvestis.index), "L'index du DataFrame doit être de type datetime"
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
        filteredDataFrame = evolutionArgenstInvestis[evolutionArgenstInvestis != 0]

        # S'assurer que l'index est trié
        filteredDataFrame.sort_index(inplace=True)

        # Resampler pour obtenir la valeur de fin de mois
        prixMensuel = filteredDataFrame.resample('ME').last()

        # Initialiser le dictionnaire pour les résultats
        evolutionPourcentageDict = {}
        montantGagneMoisPasse = 0

        # Calculer l'évolution pour chaque mois
        for (date, valeurMois) in prixMensuel.items():
            # Calculer le montant total investi jusqu'à ce mois
            montantsInvestisTotal = 0  # Réinitialiser avec la valeur initiale
            # Ajouter les montants investis aux dates précédentes ou égales à la fin de mois actuelle
            for dateInvest, prix in datesInvestissementsPrix.items():
                if dateInvest <= date:
                    montantsInvestisTotal += prix
            # Enlever les montants vendus aux dates précédentes ou égales à la fin de mois actuelle
            for dateVente, prix in datesVentesPrix.items():
                if dateVente <= date:
                    montantsInvestisTotal -= prix

            # Calcul de l'évolution en pourcentage
            pourcentageEvolution = ((valeurMois) * 100 / (montantsInvestisTotal + montantGagneMoisPasse)) - 100
            # Ajouter au dictionnaire avec la clé formatée en 'YYYY-MM'
            evolutionPourcentageDict[date.strftime('%Y-%m')] = round(pourcentageEvolution, 2)

            # Mettre à jour le montant gagné du mois passé
            montantGagneMoisPasse = (valeurMois - montantsInvestisTotal)

        # Transformer le dictionnaire en DataFrame
        evolutionPourcentageDf = pd.DataFrame.from_dict(evolutionPourcentageDict, orient='index', columns=['EvolutionPourcentage'])
        evolutionPourcentageDf.index.name = 'Date'

        return evolutionPourcentageDf
    
    @staticmethod
    def CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers: pd.DataFrame, montantsInvestisCumules: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule l'évolution en pourcentage de chaque ticker entre le montant investi cumulé et l'évolution globale du portefeuille.

        Args:
            evolutionArgentsInvestisTickers (pd.DataFrame): DataFrame contenant les valeurs globales du portefeuille pour chaque ticker.
            montantsInvestisCumules (pd.DataFrame): DataFrame contenant les montants investis cumulés pour chaque ticker.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage pour chaque ticker.
        """
        assert isinstance(evolutionArgentsInvestisTickers, pd.DataFrame), "evolutionArgentsInvestisTickers doit être un DataFrame"
        assert isinstance(montantsInvestisCumules, pd.DataFrame), "montantsInvestisCumules doit être un DataFrame"

        # Initialiser le DataFrame pour stocker l'évolution en pourcentage
        evolutionPourcentageTickers = pd.DataFrame(index=evolutionArgentsInvestisTickers.index, columns=evolutionArgentsInvestisTickers.columns, dtype=float)
        evolutionPourcentageTickers.iloc[0] = 0

        # Calcul de l'évolution en pourcentage
        for i in range(1, len(evolutionArgentsInvestisTickers.index)):
            dateActuelle = evolutionArgentsInvestisTickers.index[i]

            # Calcul de l'évolution en pourcentage
            evolutionPourcentageTickers.loc[dateActuelle] = (
                (evolutionArgentsInvestisTickers.loc[dateActuelle] - montantsInvestisCumules.loc[dateActuelle]) /
                montantsInvestisCumules.loc[dateActuelle]
            ) * 100

        return evolutionPourcentageTickers

    @staticmethod
    def CalculerEvolutionPourcentagePortefeuille(evolutionArgentsInvestisTickers: pd.DataFrame, argentInvesti: float) -> pd.DataFrame:
        """
        Calcule l'évolution en pourcentage de la valeur totale du portefeuille par rapport à l'argent investi.

        Args:
            evolutionArgentsInvestisTickers (pd.DataFrame): DataFrame contenant les valeurs globales des tickers dans le portefeuille, indexé par date.
            argentInvesti (float): Montant total investi dans le portefeuille.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage de la valeur totale du portefeuille par rapport à l'argent investi.
        """
        assert isinstance(evolutionArgentsInvestisTickers, pd.DataFrame), "evolutionArgentsInvestisTickers doit être un DataFrame"
        assert isinstance(argentInvesti, (int, float)), "argentInvesti doit être un nombre (int ou float)"
        
        # Calcul de la somme de toutes les lignes pour obtenir la valeur totale du portefeuille
        valeurTotalePortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
 
        # Calcul de l'évolution en pourcentage par rapport à l'argent investi
        evolutionPourcentage = (((argentInvesti + valeurTotalePortefeuille) - argentInvesti) / argentInvesti) * 100

        # Création d'un DataFrame pour retourner les résultats
        evolutionPourcentagePortefeuille = pd.DataFrame(evolutionPourcentage, columns=['EvolutionPourcentage'])

        return evolutionPourcentagePortefeuille
    #################################

    ########## Prix ##########
    @staticmethod
    def CalculerPlusMoinsValueCompose(montantsInvestis: pd.DataFrame, prixTickers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
                evolutionGainsPertesTickers.loc[dateActuelle, ticker] = evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] - montantsInvestisCumules
                
                if montantsInvestis.loc[datePrecedente, ticker] != montantsInvestis.loc[dateActuelle, ticker]:
                    evolutionArgentsInvestisTickers.loc[dateActuelle, ticker] += montantsInvestis.loc[dateActuelle, ticker]
                    montantsInvestisCumules += montantsInvestis.loc[dateActuelle, ticker]

        return evolutionArgentsInvestisTickers, evolutionGainsPertesTickers

    @staticmethod
    def CalculerEvolutionDividendesPortefeuille(evolutionPrixBrutTickers: pd.DataFrame, tickerPriceDf: pd.DataFrame) -> pd.DataFrame:
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

    ########## Annexe ##########
    @staticmethod
    def ExtraireDonneeJson(fichierJson: str) -> dict:
        """
        Lit et extrait le contenu d'un fichier JSON.

        Cette fonction vérifie que le fichier spécifié existe et qu'il a une extension `.json`. 
        Ensuite, elle lit et retourne le contenu du fichier sous forme d'un dictionnaire.

        Args:
            fichierJson (str): Chemin complet vers le fichier JSON à lire.

        Returns:
            dict: Contenu du fichier JSON sous forme de dictionnaire.
        """
        assert os.path.exists(fichierJson) and fichierJson.endswith('.json'), \
            f"Le fichier {fichierJson} n'existe pas ou n'a pas l'extension .json."

        # Ouverture et lecture du fichier JSON
        with open(fichierJson, 'r', encoding="UTF-8") as file:
            data = json.load(file)

        return data
    
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
    #############################
    ###############################################################



    #################### PORTEFEUILLES ####################
    ########## MON PORTEFEUILLE ##########
    def MonPortefeuille(self):
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        nomPortefeuille = "Mon Portefeuille"

        montantsInvestis, montantsInvestisCumules, prixTickers = self.CalculerPrixMoyenPondereAchatMonPortefeuille()

        # Calcul des montants
        evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.CalculerPlusMoinsValueComposeMonPortefeuille(montantsInvestis, prixTickers)
        evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
        evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1)

        # Calcul des pourcentages
        evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
        evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesTickers, self.argentInvesti)
        
        # On stock les DataFrames
        self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
        self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
        self.fondsInvestis[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
        self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
        self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
        self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
        self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, prixTickers)
        self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), self.SommeInvestissementParDate(self.datesVentes))
        self.soldeCompteBancaire[nomPortefeuille] = (self.CalculerEvolutionDepotEspeces() + evolutionArgentsInvestisPortefeuille + self.CalculerPlusValuesEncaissees())

    def CalculerPrixMoyenPondereAchatMonPortefeuille(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Calcule le prix moyen pondéré d'achat pour chaque ticker dans le portefeuille.
        Cette méthode télécharge les prix de clôture pour chaque ticker, puis calcule le montant investi cumulé
        pour chaque date d'achat.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                - montantsInvestis : DataFrame des montants investis pour chaque ticker à chaque date d'achat.
                - montantsInvestisCumules : DataFrame des montants investis cumulés pour chaque ticker.
                - prixTickers : DataFrame des prix de clôture pour chaque ticker.
        """

        datesInvestissementsPrix = self.datesAchats.copy()

        tickers = list(datesInvestissementsPrix.keys())
        # Télécharger les prix de clôture pour chaque ticker
        prixTickers = self.DownloadTickersPrice(tickers)

        montantsInvestis = pd.DataFrame(0.0, index=prixTickers.index, columns=prixTickers.columns, dtype=float)

        # Calcul du prix moyen pondéré pour chaque date d'achat
        for ticker, datesInvestissements in datesInvestissementsPrix.items():
            # Vérifie si la date est dans le DataFrame des prix
            for date, montant in datesInvestissements.items():
                montantsInvestis.at[date, ticker] = montant

        montantsInvestisCumules = montantsInvestis.cumsum()

        return montantsInvestis, montantsInvestisCumules, prixTickers

    def CalculerPlusMoinsValueComposeMonPortefeuille(self, montantsInvestis: pd.DataFrame, prixTickers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
            datesVentesPrix = self.datesVentes[ticker]
            
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

    def CalculerPlusValuesEncaissees(self) -> pd.DataFrame:
        """
        Calcule les plus-values réalisées sur une période donnée en tenant compte des opérations d'achat et de vente d'investissements.

        Returns:
            pd.DataFrame: Un DataFrame indexé par une plage de dates, contenant les plus-values cumulées réalisées sur la période.
        """
        plageDates = pd.date_range(start=self.startDate, end=self.endDate)
        plusValueRealisee = pd.Series(0.0, index=plageDates)
        
        # Calcul des plus-values réalisées après la vente
        datesVentesDict = self.SommeInvestissementParDate(self.datesVentes)
        datesAchatsDict = self.SommeInvestissementParDate(self.datesAchats)
        datesVentesList = sorted(list(datesVentesDict.keys()))
        datesAchatsList = sorted(list(datesAchatsDict.keys()))

        datesAchatsVentesList = sorted(datesAchatsList + datesVentesList)

        for date in datesAchatsVentesList:
            if date in datesAchatsList:
                plusValueRealisee.loc[date:] = max(0, (plusValueRealisee.at[date] - datesAchatsDict[date]))

            if date in datesVentesList:
                plusValueRealisee.loc[date:] += datesVentesDict[date]

        return plusValueRealisee
    
    def CalculerEvolutionDepotEspeces(self) -> pd.Series:
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
    ######################################

    ########## REPLICATION ##########
    def ReplicationDeMonPortefeuille(self):
        """Cette méthode permet de simuler en fonction de différents portefeuilles, un investissement d'après les mêmes dates d'achats et de ventes dans mon portefeuille initiale"""

        tickersAll = [ticker for portfolio in self.portfolioPercentage for ticker in portfolio[0].keys()]
        prixTickers = self.DownloadTickersPrice(tickersAll)

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
            evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesTickers, montantsInvestisCumules.iloc[-1].sum())

            # On stock les DataFrames
            self.portefeuilleTWR[nomPortefeuille] = evolutionPourcentagePortefeuille
            self.prixNetPortefeuille[nomPortefeuille] = evolutionGainsPertesPortefeuille
            self.fondsInvestis[nomPortefeuille] = evolutionArgentsInvestisPortefeuille
            self.tickersTWR[nomPortefeuille] = evolutionPourcentageTickers
            self.prixNetTickers[nomPortefeuille] = evolutionGainsPertesTickers
            self.prixBrutTickers[nomPortefeuille] = evolutionArgentsInvestisTickers
            self.dividendesTickers[nomPortefeuille] = self.CalculerEvolutionDividendesPortefeuille(evolutionArgentsInvestisTickers, prixTickersFiltree)
            self.pourcentagesMensuelsPortefeuille[nomPortefeuille] = self.CalculerEvolutionPourcentageMois(evolutionArgentsInvestisPortefeuille, self.SommeInvestissementParDate(self.datesAchats), {})
            self.soldeCompteBancaire[nomPortefeuille] = (self.CalculerEvolutionDepotEspeces() + evolutionArgentsInvestisPortefeuille)

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
    #################################

    ########## DCA ##########
    def DollarCostAveraging(self):
        """
        Cette méthode permet de simuler un investissement en Dollar Cost Average (DCA) en fonction de différents portefeuilles.

        Explication:
            L’investissement en DCA (Dollar-Cost Averaging) est une stratégie simple mais efficace,
            qui consiste à investir régulièrement des montants fixes dans un actif financier, indépendamment de son prix.
            Plutôt que d'essayer de deviner le meilleur moment pour investir, le DCA permet d'acheter des parts de façon continue,
            réduisant l'impact des fluctuations du marché.
        """

        tickersAll = [ticker for portfolio in self.portfolioPercentage for ticker in portfolio[0].keys()]
        prixTickers = self.DownloadTickersPrice(tickersAll)
        datesInvestissements = self.DatesInvesissementDCA_DCV()
        datesInvestissementsPrix = {date: (self.argentInvesti/len(datesInvestissements)) for date in datesInvestissements}

        for portfolio in self.portfolioPercentage:
            nomPortefeuille = portfolio[-1] + " DCA"
            tickers = [ticker for ticker in portfolio[0].keys()]
            prixTickersFiltree = prixTickers.loc[:, prixTickers.columns.intersection(tickers)]

            montantsInvestis, montantsInvestisCumules = self.CalculerPrixMoyenPondereAchatDollarCostAveraging(datesInvestissementsPrix, prixTickersFiltree, portfolio)

            # Calcul des montants
            evolutionArgentsInvestisTickers, evolutionGainsPertesTickers = self.CalculerPlusMoinsValueCompose(montantsInvestis, prixTickersFiltree)
            evolutionArgentsInvestisPortefeuille = evolutionArgentsInvestisTickers.sum(axis=1)
            evolutionGainsPertesPortefeuille = evolutionGainsPertesTickers.sum(axis=1)

            # Calcul des pourcentages
            evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers(evolutionArgentsInvestisTickers, montantsInvestisCumules)
            evolutionPourcentagePortefeuille = self.CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesTickers, self.argentInvesti)

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

        Args:
            startDate (str | datetime): Date de début au format 'YYYY-MM-DD' ou un objet datetime.
            endDate (str | datetime): Date de fin au format 'YYYY-MM-DD' ou un objet datetime.

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
    def CalculerPrixMoyenPondereAchatDollarCostAveraging(datesInvestissementsPrix: dict, prixTickers: pd.DataFrame, portefeuille: list) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    #########################
    #######################################################



    #################### GRAPHIQUES ####################
    def PlotlyInteractive(self, nomDossier: str, nomFichier: str):
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
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.portefeuilleTWR, "Progression en TWR (pour l'argent investi) pour chaque portefeuille", "%"))
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.prixNetPortefeuille, "Progression en euro pour chaque portefeuille", "€"))
        portefeuillesGraphiques.append(self.GraphiqueHeatmapPourcentageParMois(self.pourcentagesMensuelsPortefeuille))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.tickersTWR, "Progression en TWR (pour l'argent investi) pour chaque ticker", "%"))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.prixNetTickers, "Progression net en euro pour chaque ticker", "€"))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.prixBrutTickers, "Progression brut en euro pour chaque ticker", "€"))
        portefeuillesGraphiques.append(self.GraphiqueDividendesParAction(self.dividendesTickers))
        portefeuillesGraphiques.append(self.GraphiqueTreemapPortefeuille(self.prixBrutTickers))
        portefeuillesGraphiques.append(self.GraphiqueSunburst(self.prixBrutTickers))
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.fondsInvestis, "Progression de l'argent investi", "€"))
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.soldeCompteBancaire, "Progression de l'argent sur le Compte Bancaire", "€"))

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
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame: ({type(df)})"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(suffixe, str), f"devise doit être une chaîne de caractères: ({type(suffixe)})"

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
                hovertemplate=f'Ticker: {column}<br>' + 'Date: %{x}<br>Pourcentage: %{y:.2f}' + suffixe + '<extra></extra>'
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
        assert isinstance(dataDict, dict), f"dataDict doit être un dictionnaire: ({type(dataDict)})"
        assert all(isinstance(df, pd.DataFrame) for df in dataDict.values()), "Chaque valeur de dataDict doit être un DataFrame"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(suffixe, str), f"devise doit être une chaîne de caractères: ({type(suffixe)})"

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
                    hovertemplate=f'Ticker: {column}<br>' + 'Date: %{x}<br>Pourcentage: %{y:.2f}' + suffixe + '<extra></extra>',
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
    def SaveInFile(figures: list, nomFichier: str):
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
    def EnregistrerDataFrameEnJson(self, cheminFichierJson: str):
        """
        Enregistre un DataFrame au format JSON dans le fichier spécifié, avec les dates comme clés et les montants comme valeurs.

        Args:
            cheminFichierJson (str): Le chemin du fichier JSON dans lequel enregistrer le DataFrame.
        """
        assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith(".json"), \
            f"cheminFichierJson doit être une chaîne se terminant par '.json', mais c'est {type(cheminFichierJson)}."

        dataFrame = copy.deepcopy(self.soldeCompteBancaire["Mon Portefeuille"])

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

