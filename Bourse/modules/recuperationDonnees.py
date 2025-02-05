import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json
import os

class RecuperationDonnees:
    """
    Cette classe permet de récupérer toutes les données nécessaires pour l'analyse. 
    Elle télécharge les données à partir d'Internet ou les charge à partir de fichiers JSON existants.
    """

    def __init__(self, repertoireJson: str):
        """
        Initialise l'objet avec un répertoire JSON pour charger ou enregistrer les données.

        Args:
            repertoireJson (str): Chemin vers le répertoire contenant les fichiers JSON.
        """
        assert isinstance(repertoireJson, str), "repertoireJson doit être une chaîne de caractères."
        self.repertoireJson = repertoireJson


    def DownloadTickersPrice(self, tickers: list, startDate: datetime, endDate: datetime) -> pd.DataFrame:
        """
        Télécharge les prix de clôture des actions spécifiées sur une période donnée.

        Args:
            tickers (list): Liste des symboles boursiers à télécharger.
            startDate (datetime): Date de début du téléchargement.
            endDate (datetime): Date de fin du téléchargement.

        Returns:
            pd.DataFrame: Un DataFrame contenant les prix de clôture des actions spécifiées,
            avec les dates manquantes complétées et les prix éventuellement convertis en EUR.
        """
        assert isinstance(tickers, list) and all(isinstance(ticker, str) for ticker in tickers), "tickers doit être une liste de chaînes de caractères"
        assert isinstance(startDate, datetime), "startDate doit être  un objet datetime"
        assert isinstance(endDate, datetime), "endDate doit être un objet datetime"

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

        return self.ConversionMonnaieDollardEuro(prixTickers, startDate, endDate)

    @staticmethod
    def ConversionMonnaieDollardEuro(df: pd.DataFrame, startDate: datetime, endDate: datetime) -> pd.DataFrame:
        """
        Convertit les valeurs d'un DataFrame d'une devise à une autre sur une période spécifiée.

        Args:
            df (pd.DataFrame): DataFrame contenant les données financières en différentes devises.
            startDate (datetime): Date de début.
            endDate (datetime): Date de fin'.

        Returns:
            pd.DataFrame: Un DataFrame avec les valeurs converties en utilisant le taux de change correspondant.
        """
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame: ({type(df)})"
        assert isinstance(startDate, datetime), f"startDate doit être un objet datetime: ({type(startDate)})"
        assert isinstance(endDate, datetime), f"endDate doit être un objet datetime: ({type(endDate)})"
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
    
    def DownloadTickersSMA(self, startDate: datetime, endDate: datetime, tickers: list, sma: list) -> pd.DataFrame:
        """
        Calcule la moyenne mobile simple (SMA) pour chaque ticker dans le DataFrame des prix des tickers
        sur une période donnée.

        Args:
            startDate (datetime): La date de début pour le calcul de la SMA.
            endDate (datetime): La date de fin pour le calcul de la SMA.
            tickers (list): Liste des symboles boursiers à télécharger.
            sma (list): Liste des périodes (en jours) pour lesquelles calculer la SMA.

        Returns:
            pd.DataFrame: DataFrame contenant les SMA calculées pour chaque période et chaque ticker.
        """
        assert isinstance(startDate, datetime), "startDate doit être  un objet datetime"
        assert isinstance(endDate, datetime), "endDate doit être un objet datetime"
        assert isinstance(tickers, list) and all(isinstance(ticker, str) for ticker in tickers), "tickers doit être une liste de chaînes de caractères"
        assert isinstance(sma, list) and all(isinstance(smaJour, int) for smaJour in sma), "sma doit être une liste d'entiers"

        prixTickers = self.DownloadTickersPrice(tickers, (startDate - timedelta(max(sma) + 50)), endDate)
        smaDf = pd.DataFrame()  # Initialiser avec les mêmes index que tickerPriceDf

        for nbJour in sma:
            # Calculer la moyenne mobile pour chaque ticker (chaque colonne de tickerPriceDf)
            moyenneMobile = prixTickers.rolling(window=nbJour).mean()
            
            # Ajouter chaque colonne SMA avec un suffixe du nombre de jours
            for col in moyenneMobile.columns:
                smaDf[f"{col}_SMA_{nbJour}"] = moyenneMobile[col]

        return smaDf



    def RecuperationTickerBuySell(self, fichierJsonAchatsVentes: str) -> dict:
        """
        Récupère les données de transactions par ticker depuis un fichier JSON.

        Args:
            fichierJsonAchatsVentes (str): Chemin vers le fichier JSON contenant les transactions.

        Returns:
            dict: Un dictionnaire où chaque clé est un ticker, et chaque valeur est un dictionnaire contenant les dates et les prix.
        """
        # Assertions pour vérifier les préconditions
        assert isinstance(fichierJsonAchatsVentes, str), f"fichierJsonAchatsVentes doit être une chaîne de caractères: ({fichierJsonAchatsVentes})"
        assert os.path.exists(fichierJsonAchatsVentes), f"Le fichier {fichierJsonAchatsVentes} n'existe pas."
        assert fichierJsonAchatsVentes.endswith('.json'), f"Le fichier {fichierJsonAchatsVentes} doit avoir l'extension .json."

        # Extraire les données du fichier JSON
        data = self.ExtraireDonneeJson(fichierJsonAchatsVentes)
        assert isinstance(data, list), f"Les données extraites doivent être une liste: ({type(data)})"

        result = {}

        # Parcours de chaque élément dans la liste de données
        for entry in data:
            assert isinstance(entry, dict), f"Chaque élément des données doit être un dictionnaire: ({type(entry)})"
            assert "Ticker" in entry, f"Chaque entrée doit contenir la clé 'Ticker': ({entry})"
            assert "Date d'exécution" in entry, f"Chaque entrée doit contenir la clé 'Date d'exécution': ({entry})"
            assert "Montant investi" in entry or "Montant gagné" in entry, f"L'entrée doit contenir 'Montant investi' ou 'Montant gagné': ({entry})"
            
            ticker = entry["Ticker"]
            dateExecution = pd.to_datetime(entry["Date d'exécution"])

            # Détermination du montant en fonction du fichier
            if fichierJsonAchatsVentes == (self.repertoireJson + "Ordres d'achats.json"):
                montant = abs(entry["Montant investi"])
            else:
                montant = abs(entry["Montant gagné"])

            # Si le ticker n'est pas encore dans le dictionnaire, on l'ajoute avec une valeur vide
            if ticker not in result:
                result[ticker] = {}

            # Mise à jour du dictionnaire pour ce ticker
            if dateExecution in result[ticker]:
                result[ticker][dateExecution] += montant
            else:
                result[ticker][dateExecution] = montant

        # Retourner les données triées par date pour chaque ticker
        return {ticker: dict(sorted(dates.items())) for ticker, dates in result.items()}

    def RecuperationTickerFrais(self, fichierJsonAchatsVentes: str) -> dict:
        """
        Récupère les données des frais de transactions par ticker depuis un fichier JSON.

        Args:
            fichierJsonAchatsVentes (str): Chemin vers le fichier JSON contenant les frais transactions.

        Returns:
            dict: Un dictionnaire où chaque clé est un ticker, et chaque valeur est un dictionnaire contenant les dates et les frais.
        """
        assert isinstance(fichierJsonAchatsVentes, str), f"fichierJsonAchatsVentes doit être une chaîne de caractères: ({fichierJsonAchatsVentes})"
        assert os.path.exists(fichierJsonAchatsVentes) and fichierJsonAchatsVentes.endswith('.json'), f"Le fichier {fichierJsonAchatsVentes} n'existe pas ou n'a pas l'extension .json."

        data = self.ExtraireDonneeJson(fichierJsonAchatsVentes)
        assert isinstance(data, list), f"Les données extraites doivent être une liste: ({type(data)})"
        result = {}

        # Parcours de chaque élément dans la liste de données
        for entry in data:
            assert isinstance(entry, dict), f"Chaque élément des données doit être un dictionnaire: ({type(entry)})"
            assert "Ticker" in entry, f"Chaque entrée doit contenir la clé 'Ticker': ({entry})"
            assert "Date d'exécution" in entry, f"Chaque entrée doit contenir la clé 'Date d'exécution': ({entry})"
            assert "Frais" in entry, f"L'entrée doit contenir 'Montant investi' ou 'Montant gagné': ({entry})"

            ticker = entry["Ticker"]
            dateExecution = pd.to_datetime(entry["Date d'exécution"])

            montant = abs(entry["Frais"])  # On prend la valeur absolue du montant investi
            
            # Si le ticker n'est pas encore dans le dictionnaire, on l'ajoute avec une valeur vide
            if ticker not in result:
                result[ticker] = {}
            
            if dateExecution in result[ticker]:
                result[ticker][dateExecution] += montant
            else:
                result[ticker][dateExecution] = montant
        
        return {ticker: dict(sorted(dates.items())) for ticker, dates in result.items()}

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
    


    def CalculateNetInvestment(self) -> float:
        """
        Calcule l'argent investi initialement.
        
        Il faut calculer la somme des montants investis pour chaque ticker à chaque date d'achat.
        Puis on soustrait l'argent initialement investi du ticker s'il a été vendu.

        Attention toutefois, si on vend un ticker et qu'il possède une ancienne date de vente.
        Alors il faut calculer l'argent initialement investi entre la dernière date de vente et la date de vente actuelle.

        Returns:
            float: La différence entre la somme des prix d'achat et la somme des prix de vente.
        """

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

        # Calcul de la différence entre l'argent investi et l'argent récupéré lors des ventes
        return totalBuy - totalSell

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
            dividendes = dividendes.loc[tickerPriceDf.index.min():tickerPriceDf.index.max()]

            # Ajout des dividendes au DataFrame, avec propagation aux dates suivantes
            for date, montantDividendes in dividendes.items():
                if date in tickersDividendes.index:
                    # Calculer et ajouter le montant du dividende
                    montantDividendesAjoute = (montantDividendes * evolutionPrixBrutTickers.at[date, ticker] / tickerPriceDf.at[date, ticker])
                    tickersDividendes.at[date, ticker] += montantDividendesAjoute

        return tickersDividendes
    
