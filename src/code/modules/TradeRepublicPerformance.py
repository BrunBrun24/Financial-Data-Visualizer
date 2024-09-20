import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import json
import os
from collections import defaultdict
import numpy as np


class TradeRepublicPerformance:
    """
    La classe TradeRepublicPerformance est conçue pour analyser et visualiser la performance des transactions boursières
    à partir d’un fichier JSON contenant les données de transactions.
    Elle permet de calculer et de suivre l’évolution des investissements, des prix des actions, et de la performance globale du portefeuille.

    Attributs :
        - fichierJson : Chemin vers le fichier JSON contenant les transactions.
        - buyDate : Dictionnaire des dates d’achat par ticker.
        - sellDate : Dictionnaire des dates de vente par ticker.
        - argentInvestis : Montant total de l’argent investi.
        - prixFifo, prixTickers, prixAchatTicker : DataFrames pour les prix d’achat FIFO, les prix des tickers et les coûts d’achat.
        - evolutionPourcentageTickers : DataFrame de l’évolution en pourcentage des tickers.
        - evolutionPrixTickersBrut, evolutionPrixPortefeuilleBrut : DataFrames de l’évolution des prix bruts des tickers et du portefeuille.
        - evolutionPrixTickersNet, evolutionPrixPortefeuilleNet : DataFrames de l’évolution des prix nets des tickers et du portefeuille.
        - evolutionPourcentagePortefeuille : DataFrame de l’évolution en pourcentage du portefeuille.

    Méthodes :
        - __init__(self, fichierJson: str) : Initialise la classe avec le fichier JSON.
        - GetArgentInvestis(self) -> int : Retourne le montant total de l’argent investi.
        - GetEvolutionPourcentageTickers(self) -> pd.DataFrame : Retourne l’évolution en pourcentage des tickers.
        - GetEvolutionPrixTickers(self, net=True) -> pd.DataFrame : Retourne l’évolution des prix des tickers (net ou brut).
        - GetEvolutionPrixPortefeuille(self, net=True) -> pd.DataFrame : Retourne l’évolution des prix du portefeuille (net ou brut).
        - GetEvolutionPourcentagePortefeuille(self) -> pd.DataFrame : Retourne l’évolution en pourcentage du portefeuille.
        - RecuperationTickerBuySell(self, objectif: str) -> dict : Récupère les données de transactions par ticker depuis le fichier JSON.
        - DatesBuySell(self) -> tuple : Extrait les informations sur les achats et les ventes par date.
        - ConversionMonnaie(self, df: pd.DataFrame, tauxDeConvertion="EURUSD=X") -> pd.DataFrame : Convertit les valeurs d’un DataFrame d’une devise à une autre.
        - ConvertionALaDateDAchat(prixAchatAConvertir: float, dateAchat: str, tauxDeConvertion: pd.DataFrame) -> float : Convertit un montant d’une devise en euros à la date d’achat donnée.
        - CalculerEvolutionPourcentageTickers(self) -> pd.DataFrame : Calcule l’évolution en pourcentage du prix des actions par rapport aux prix d’achat FIFO.
        - CalculerEvolutionPrixTickersPortefeuille(self, net=True) -> pd.DataFrame : Calcule l’évolution du prix des actions par rapport aux prix d’achat.
        - CalculEvolutionPourcentagePortefeuille(self) -> pd.DataFrame : Calcule l’évolution en pourcentage des gains/pertes par rapport au montant investi total.
        - CalculerPrixAchatFifo(self) -> tuple : Calcule les prix d’achat FIFO pour les actions.
        - CalculerArgentsInvestis(self) -> float : Calcule l’argent investi total en fonction des dates d’achat et de vente.
        - TotalInvesti(donnees: dict) -> float : Calcule le montant total investi à partir du dictionnaire de données.
        - ArgentInvestiAll(self) -> float : Calcule le montant total investi en agrégeant les achats et les ventes.
        - PlotlyInteractivePlot(self, df: pd.DataFrame, title="") -> None : Crée et affiche un graphique interactif avec Plotly.
    """
    def __init__(self, fichierJson: str):
        """
        Initialise la classe avec le chemin du fichier JSON contenant les transactions.
        
        Args:
            fichierJson: Chemin vers le fichier JSON contenant les transactions.
        """
        assert isinstance(fichierJson, str), f"fichierJson doit être une chaîne de caractères: ({fichierJson})"
        assert os.path.exists(fichierJson) and fichierJson.endswith('.json'), f"Le fichier {fichierJson} n'existe pas ou n'a pas l'extension .json."

        self.fichierJson = fichierJson

        self.buyDate = self.RecuperationTickerBuySell("achats")
        self.sellDate = self.RecuperationTickerBuySell("ventes")
        self.argentInvestis = self.ArgentInvestiAll()

        self.prixFifo, self.prixTickers, self.prixAchatTicker = self.CalculerPrixAchatFifo()

        self.evolutionPourcentageTickers = self.CalculerEvolutionPourcentageTickers()
        self.evolutionPrixTickersBrut, self.evolutionPrixPortefeuilleBrut = self.CalculerEvolutionPrixTickersPortefeuille(False)
        self.evolutionPrixTickersNet, self.evolutionPrixPortefeuilleNet = self.CalculerEvolutionPrixTickersPortefeuille(True)
        self.evolutionPourcentagePortefeuille = self.CalculEvolutionPourcentagePortefeuille()


    def GetArgentInvestis(self) -> int:
        """
        Retourne le montant total de l'argent investi.

        Returns:
            int: Montant total de l'argent investi.
        """
        assert isinstance(self.argentInvestis, int), f"argentsInvestis doit être un entier, mais c'est {type(self.argentInvestis).__name__}."
        return self.argentInvestis

    def GetEvolutionPourcentageTickers(self) -> pd.DataFrame:
        """
        Retourne l'évolution en pourcentage des tickers.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage des tickers.
        """
        assert isinstance(self.evolutionPourcentageTickers, pd.DataFrame), f"evolutionPourcentageTickers doit être un DataFrame, mais c'est {type(self.evolutionPourcentageTickers).__name__}."
        return self.evolutionPourcentageTickers

    def GetEvolutionPrixTickers(self, net=True) -> pd.DataFrame:
        """
        Retourne l'évolution des prix des tickers, net ou brut.

        Args:
            net (bool): Si True, retourne les prix nets, sinon les prix bruts. Par défaut True.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution des prix des tickers.
        """
        assert isinstance(self.evolutionPrixTickersNet, pd.DataFrame), f"evolutionPrixTickersNet doit être un DataFrame, mais c'est {type(self.evolutionPrixTickersNet).__name__}."
        assert isinstance(net, bool), f"net doit être un booléan, mais c'est {type(net).__name__}."
        if net:
            return self.evolutionPrixTickersNet
        else:
            return self.evolutionPrixTickersBrut

    def GetEvolutionPrixPortefeuille(self, net=True) -> pd.DataFrame:
        """
        Retourne l'évolution des prix du portefeuille, net ou brut.

        Args:
            net (bool): Si True, retourne les prix nets, sinon les prix bruts. Par défaut True.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution des prix du portefeuille.
        """
        assert isinstance(self.evolutionPrixPortefeuilleNet, pd.DataFrame), f"evolutionPrixPortefeuilleNet doit être un DataFrame, mais c'est {type(self.evolutionPrixPortefeuilleNet).__name__}."
        assert isinstance(net, bool), f"net doit être un booléan, mais c'est {type(net).__name__}."
        if net:
            return self.evolutionPrixPortefeuilleNet
        else:
            return self.evolutionPrixPortefeuilleBrut

    def GetEvolutionPourcentagePortefeuille(self) -> pd.DataFrame:
        """
        Retourne l'évolution en pourcentage du portefeuille.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage du portefeuille.
        """
        assert isinstance(self.evolutionPourcentagePortefeuille, pd.DataFrame), f"evolutionPourcentagePortefeuille doit être un DataFrame, mais c'est {type(self.evolutionPourcentagePortefeuille).__name__}."
        return self.evolutionPourcentagePortefeuille


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

    def DatesBuySell(self) -> tuple:
        """
        Extrait les informations sur les achats et les ventes à partir du fichier JSON et les organise par date.

        Returns:
            Tuple: Un tuple contenant trois éléments :
                - Dictionnaire des achats cumulés par date, trié par date.
                - Dictionnaire des ventes par date, trié par date.
                - Dictionnaire des ventes avec détails par date, où chaque entrée contient le ticker et le prix de vente.
        """
        with open(self.fichierJson, 'r') as file:
            data = json.load(file)

        assert isinstance(data, dict), f"Le fichier JSON doit contenir un dictionnaire: ({data})"
        assert len(data) > 0, "Le fichier JSON est vide ou mal formé."

        data = list(data.values())[0]

        assert isinstance(data, list), f"Les données extraites doivent être une liste: ({data})"

        achatsCumules = defaultdict(int)
        sell = defaultdict(float)
        tickerSell = {}

        for transaction in data:
            assert isinstance(transaction, dict), f"Chaque transaction doit être un dictionnaire: ({transaction})"
            assert 'ticker' in transaction, f"La clé 'ticker' est manquante dans la transaction: ({transaction})"
            ticker = transaction['ticker']

            assert 'achats' in transaction, f"La clé 'achats' est manquante dans la transaction: ({transaction})"
            assert isinstance(transaction['achats'], list), f"Les achats doivent être une liste: ({transaction['achats']})"

            for achat in transaction['achats']:
                assert isinstance(achat, dict), f"Chaque achat doit être un dictionnaire: ({achat})"
                assert 'date' in achat and 'price' in achat, f"Les clés 'date' et 'price' sont nécessaires dans l'achat: ({achat})"
                date = achat['date']
                price = achat['price']
                achatsCumules[date] += round(price)

            assert 'ventes' in transaction, f"La clé 'ventes' est manquante dans la transaction: ({transaction})"
            assert isinstance(transaction['ventes'], list), f"Les ventes doivent être une liste: ({transaction['ventes']})"

            for vente in transaction['ventes']:
                assert isinstance(vente, dict), f"Chaque vente doit être un dictionnaire: ({vente})"
                assert 'date' in vente and 'price' in vente, f"Les clés 'date' et 'price' sont nécessaires dans la vente: ({vente})"
                date = vente['date']
                price = vente['price']
                sell[date] += round(price, 2)
                tickerSell[date] = {"ticker": ticker, "price": price}

        achatsCumulesOrdonnes = dict(sorted(achatsCumules.items()))
        sellOrdonnes = dict(sorted(sell.items()))

        return achatsCumulesOrdonnes, sellOrdonnes, tickerSell

    def ConversionMonnaie(self, df: pd.DataFrame, tauxDeConvertion="EURUSD=X") -> pd.DataFrame:
        """
        Convertit les valeurs d'un DataFrame d'une devise à une autre.

        Args:
            data (pd.DataFrame): DataFrame contenant les données financières avec différents prix (EUR, USD, ...).
            tauxDeConvertion (str): Code du taux de change à utiliser pour la conversion (par défaut 'EURUSD=X').
            

        Returns:
            Un DataFrame avec les valeurs converties en utilisant le taux de change actuel.
        """
        assert isinstance(df, pd.DataFrame), f"data doit être un DataFrame: ({type(df).__name__})"
        assert isinstance(tauxDeConvertion, str), f"devise doit être une chaîne de caractères: ({type(tauxDeConvertion).__name__})"
        assert all(df.dtypes == 'float64') or all(df.dtypes == 'int64'), "Les colonnes du DataFrame doivent contenir des nombres."

        startDate = df.index.min()
        endDate = df.index.max() + timedelta(days=3)

        # Télécharger les données de la devise
        tauxDeConvertionDf = yf.download(tauxDeConvertion, start=startDate, end=endDate)
        assert 'Close' in tauxDeConvertionDf.columns, "Les données de la devise téléchargées ne contiennent pas la colonne 'Close'."
        # Réindexer le DataFrame pour inclure toutes les dates manquantes
        tauxDeConvertionDf = tauxDeConvertionDf.reindex(pd.date_range(start=tauxDeConvertionDf.index.min(), end=tauxDeConvertionDf.index.max(), freq='D'))
        tauxDeConvertionDf = tauxDeConvertionDf.fillna(method='ffill').fillna(method='bfill')

        for ticker in df.columns:
            if "." not in ticker:
                for date in df.index:
                    try:
                        df.at[date, ticker] = self.ConvertionALaDateDAchat(df.at[date, ticker], date.strftime('%Y-%m-%d'), tauxDeConvertionDf)
                    except ValueError as e:
                        print(f"Erreur pour {ticker} à la date {date}: {e}")

        return df

    @staticmethod
    def ConvertionALaDateDAchat(prixAchatAConvertir: float, dateAchat: str, tauxDeConvertion: pd.DataFrame) -> float:
        """
        Convertit un montant d'une devise en euros à la date d'achat donnée.

        Args:
            prixAchatAConvertir (float): Le montant en euros que vous souhaitez convertir en dollars américains.
            dateAchat (str): La date d'achat sous forme de chaîne de caractères au format 'YYYY-MM-DD'.
            eurUsd (pd.DataFrame): DataFrame contenant les taux de change EUR/USD avec les colonnes 'Open', 'High',
                                'Low', 'Close', 'Adj Close' et 'Volume'. Les index de la DataFrame doivent être
                                des dates correspondant aux jours de trading.

        Returns:
            float: Le montant converti.
        """
        assert isinstance(prixAchatAConvertir, (int, float)) and prixAchatAConvertir > 0, f"prixAchatAConvertir doit être un nombre positif: {prixAchatAConvertir}"
        assert isinstance(dateAchat, str), f"dateAchat doit être une chaîne de caractères: {dateAchat}"
        assert isinstance(tauxDeConvertion, pd.DataFrame), f"EurUsd doit être une DataFrame: ({type(tauxDeConvertion).__name__})"
        assert 'Close' in tauxDeConvertion.columns, f"La DataFrame doit contenir une colonne 'Close': {tauxDeConvertion.columns}"
        assert dateAchat in tauxDeConvertion.index, f"La date d'achat n'est pas dans la DataFrame: {dateAchat}"

        # Obtenir le taux de change pour la date d'achat
        tauxConverti = tauxDeConvertion.loc[dateAchat]['Close']
        # Convertir le montant
        montant = prixAchatAConvertir / tauxConverti

        return montant

    def CalculerEvolutionPourcentageTickers(self) -> pd.DataFrame:
        """
        Calcule l'évolution en pourcentage du prix des actions par rapport aux prix d'achat FIFO.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage du prix des actions par rapport aux prix d'achat FIFO.
        """
        # Récupérer les DataFrames dans des variables locales
        prixFifo = self.prixFifo
        prixTickers = self.prixTickers

        # Vérifications des types et des index
        assert isinstance(prixFifo, pd.DataFrame), f"prixFifo doit être un DataFrame: ({type(prixFifo).__name__})"
        assert isinstance(prixTickers, pd.DataFrame), f"prixTickers doit être un DataFrame: ({type(prixTickers).__name__})"
        assert prixFifo.index.equals(prixTickers.index), "Les index de prixFifo et prixTickers doivent être identiques."

        # Initialisation du DataFrame pour l'évolution en pourcentage
        evolutionPourcentageTickers = pd.DataFrame(index=prixFifo.index, columns=prixFifo.columns)

        # Calcul de l'évolution en pourcentage pour chaque ticker
        for ticker in prixFifo.columns:
            fifoPrices = prixFifo[ticker]
            currentPrices = prixTickers[ticker]

            # Éviter les calculs pour les prix FIFO à 0
            validPrices = fifoPrices != 0

            # Calcul de l'évolution en pourcentage pour les valeurs valides
            evolutionPourcentageTickers[ticker] = np.where(validPrices, (currentPrices * 100 / fifoPrices) - 100, np.nan)

        evolutionPourcentageTickers.ffill(inplace=True)

        return evolutionPourcentageTickers

    def CalculerEvolutionPrixTickersPortefeuille(self, net=True) -> pd.DataFrame:
        """
        Calcule l'évolution du prix des actions par rapport aux prix d'achat en utilisant les pourcentages fournis.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Deux DataFrames:
                - evolutionPrixTickers: Evolution des prix pour chaque ticker.
                - evolutionGlobalPrix: Somme globale des évolutions des prix pour le portefeuille.
        """
        # Récupération des données dans des variables locales
        evolutionPourcentageTickers = self.evolutionPourcentageTickers
        prixAchatTicker = self.prixAchatTicker
        sellDate = self.sellDate
        
        assert isinstance(evolutionPourcentageTickers, pd.DataFrame), f"evolutionPourcentageTickers doit être un DataFrame: ({type(evolutionPourcentageTickers).__name__})"
        assert isinstance(prixAchatTicker, pd.DataFrame), f"prixAchatTicker doit être un DataFrame: ({type(prixAchatTicker).__name__})"
        # Assurer que les index des DataFrames sont identiques
        assert evolutionPourcentageTickers.index.equals(prixAchatTicker.index), "Les index de evolutionPourcentageTickers et prixAchatTicker doivent être identiques."
        
        # Initialisation des DataFrames pour l'évolution des prix et les plus-values réalisées
        evolutionPrixTickers = pd.DataFrame(index=evolutionPourcentageTickers.index, columns=evolutionPourcentageTickers.columns)
        plusValueRealisee = pd.DataFrame(index=evolutionPourcentageTickers.index, columns=evolutionPourcentageTickers.columns)
        
        # Calculer l'évolution du prix pour chaque ticker
        for ticker in evolutionPourcentageTickers.columns:
            pourcentage = evolutionPourcentageTickers[ticker] / 100
            if net:
                # Calculer l'évolution net
                evolutionPrixTickers[ticker] = (prixAchatTicker[ticker] * (1 + pourcentage)) - prixAchatTicker[ticker]
            else:
                # Calculer l'évolution brut
                evolutionPrixTickers[ticker] = (prixAchatTicker[ticker] * (1 + pourcentage))
        
        # Remplir les valeurs manquantes par la dernière valeur connue
        evolutionPrixTickers.ffill(inplace=True)
        
        # Calcul des plus-values réalisées après la vente
        for ticker, operations in sellDate.items():
            for date, prix in operations.items():
                dateMoinsUnJour = (pd.to_datetime(date) - timedelta(days=1)).strftime('%Y-%m-%d')
                plusValueRealisee.loc[dateMoinsUnJour:, ticker] = evolutionPrixTickers.loc[dateMoinsUnJour, ticker]
        
        # Somme globale des évolutions des prix
        evolutionGlobalPrix = pd.DataFrame(index=evolutionPrixTickers.index)
        if net:
            evolutionGlobalPrix["MonPortefeuille"] = evolutionPrixTickers.sum(axis=1) + plusValueRealisee.sum(axis=1)
        else:
            evolutionGlobalPrix["MonPortefeuille"] = evolutionPrixTickers.sum(axis=1)
        
        return evolutionPrixTickers, evolutionGlobalPrix

    def CalculEvolutionPourcentagePortefeuille(self) -> pd.DataFrame:
        """
        Calcule l'évolution en pourcentage des gains/pertes par rapport au montant investi total pour chaque colonne.

        Args:
            df: DataFrame avec l'évolution des gains/pertes, où chaque colonne représente des gains/pertes pour différentes catégories.
            montantInvestiTotal: Montant total investi initialement.

        Returns:
            DataFrame avec l'évolution en pourcentage pour chaque colonne.
        """
        # Calculer l'évolution en pourcentage pour chaque colonne
        dfPourcentage = round((self.evolutionPrixPortefeuilleNet / self.argentInvestis) * 100, 2)

        return dfPourcentage

    def CalculerPrixAchatFifo(self) -> tuple:
        """
        Calcule les prix d'achat FIFO (First In First Out) pour les actions basées sur les dates d'achat et les prix de clôture.

        Returns:
            tuple: Un tuple contenant trois DataFrames :
                - prixFifo : DataFrame des prix d'achat FIFO pour chaque ticker.
                - prixTickers : DataFrame des prix de clôture des actions.
                - self.prixAchatTicker : DataFrame des coûts totaux d'achat pour chaque ticker.
        """
        buyDate = self.buyDate
        sellDate = self.sellDate

        tickerAll = list(buyDate.keys())

        # Récupérer toutes les dates d'achat et de vente et les trier
        dateInvestir = sorted(list(set(date for ele in buyDate.values() for date in ele.keys())))

        startDate = min(dateInvestir)
        endDate = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Télécharger les prix de clôture pour chaque ticker
        prixTickers = yf.download(tickerAll, start=startDate, end=endDate)["Close"].fillna(method='ffill').fillna(method='bfill')

        # Si un seul ticker, s'assurer que prixTickers est un DataFrame
        if isinstance(prixTickers, pd.Series):
            prixTickers = prixTickers.to_frame()

        # Enlever le fuseau horaire et normaliser les dates
        prixTickers.index = prixTickers.index.tz_localize(None).normalize()
        # Convertir les prix en EUR si nécessaire
        prixTickers = self.ConversionMonnaie(prixTickers)

        # Ajouter les dates manquantes et remplir avec la valeur précédente
        allDates = pd.date_range(start=startDate, end=endDate, freq='D')
        prixTickers = prixTickers.reindex(allDates).fillna(method='ffill')

        # Créer une DataFrame pour stocker les prix d'achat FIFO
        prixFifo = pd.DataFrame(index=prixTickers.index, columns=tickerAll)
        prixAchatTicker = pd.DataFrame(index=prixTickers.index, columns=tickerAll)

        # Calculer les prix d'achat FIFO pour chaque ticker
        for ticker in tickerAll:
            achats = buyDate[ticker]
            achatsSorted = dict(sorted(achats.items()))

            totalQuantite = 0
            totalCout = 0

            for date, montantAchat in achatsSorted.items():
                prixAction = prixTickers.loc[date, ticker]
                quantiteAchetee = round(montantAchat) / prixAction

                # Mettre à jour la quantité totale et le coût total
                totalQuantite += quantiteAchetee
                totalCout += round(montantAchat)

                # Calculer le prix d'achat FIFO
                prixAchatFifo = totalCout / totalQuantite

                # Appliquer le prix FIFO à partir de la date d'achat
                prixFifo.loc[date:, ticker] = prixAchatFifo
                prixAchatTicker.loc[date:, ticker] = totalCout

        
        ####################### En attendant de résoudre le problème de vente #######################
        for ticker, operation in sellDate.items():
            for date, prix in operation.items():
                prixFifo.loc[date:, ticker] = 0
                prixAchatTicker.loc[date:, ticker] = 0
                
        #############################################################################################
            

        # Remplir les éventuelles valeurs manquantes par la dernière valeur connue
        prixFifo.ffill(inplace=True)
        prixAchatTicker.ffill(inplace=True)

        return prixFifo, prixTickers, prixAchatTicker

    def CalculerArgentsInvestis(self) -> float:
        """
        Calcule l'argent investi total en fonction des dates d'achat et de vente.

        Returns:
            argentInvesti: Montant total investi après les achats et ventes.
        """
        buyDate = self.buyDate
        sellDate = self.sellDate
        
        assert isinstance(buyDate, dict), f"buyDate doit être un dictionnaire: ({type(buyDate).__name__})"
        assert isinstance(sellDate, dict), f"buyDate doit être un dictionnaire: ({type(sellDate).__name__})"

        buyDate = dict(sorted(buyDate.items()))
        sellDate = dict(sorted(sellDate.items()))

        tickerAll = [ticker for ticker in buyDate.keys()]

        dateInvestir = [date for ele in buyDate.values() for date in ele.keys()]
        dateSell = [date for ele in sellDate.values() for date in ele.keys()]

        dateInvestir = sorted(list(set(dateInvestir)))
        dateSell = sorted(list(set(dateSell)))

        startDate = min(dateInvestir)
        endDate = datetime.now().strftime("%Y-%m-%d")

        listeDates = pd.date_range(start=startDate, end=endDate).strftime("%Y-%m-%d").tolist()

        investedAmount = {ticker: 0 for ticker in tickerAll}

        for dateActuel in listeDates:
            if dateActuel in dateInvestir:
                for ticker, datePrice in buyDate.items():
                    for date, price in datePrice.items():
                        if date == dateActuel:
                            investedAmount[ticker] += round(price)

            if dateActuel in dateSell:
                for ticker, datePrice in sellDate.items():
                    for date, price in datePrice.items():
                        if date == dateActuel:
                            investedAmount[ticker] = 0

        argentInvesti = sum(argent for argent in investedAmount.values())

        return argentInvesti

    @staticmethod
    def TotalInvesti(donnees: dict) -> float:
        """
        Calcule le montant total investi à partir du dictionnaire de données.

        Args:
            donnees (dict): Dictionnaire où les clés sont les tickers et les valeurs sont des dictionnaires
                            contenant les dates et les montants investis.

        Returns:
            float: La somme totale des montants investis.
        """
        assert isinstance(donnees, dict), f"donnees doit être un dictionnaire: ({type(donnees).__name__})"
        
        total = 0.0
        for investissements in donnees.values():
            assert isinstance(investissements, dict), f"Les valeurs du dictionnaire principal doivent être des dictionnaires: ({investissements})"
            total += sum(investissement for investissement in investissements.values())
        
        return total

    def ArgentInvestiAll(self) -> float:
        """
        Calcule le montant total investi en agrégeant les achats et les ventes à partir des données d'un fichier JSON.

        Returns:
            float: Montant total investi, arrondi au montant le plus proche.
        """
        
        achats = self.buyDate
        ventes = self.sellDate
        
        totalVentes = self.TotalInvesti(ventes)

        # Calculer l'argent investi en agrégeant les achats et les ventes
        totalAchats = self.TotalInvesti(achats)
        totalVentes = self.TotalInvesti(ventes)
        argentInvesti = totalAchats - totalVentes

        return round(argentInvesti)

    @staticmethod
    def PlotlyInteractivePlot(df: pd.DataFrame, title="") -> None:
        """
        Crée et affiche un graphique interactif avec Plotly en utilisant les données fournies.

        Args:
            data: DataFrame contenant les données à tracer. Les colonnes représentent différentes séries de données.
            title: Titre du graphique.

        Returns:
            None
        """
        assert isinstance(df, pd.DataFrame), f"data doit être un DataFrame: ({type(df).__name__})"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title).__name__})"

        fig = go.Figure()
        colors = [
            '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00', '#8a2be2',
            '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a', '#dc143c',
            '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6', '#00bfff',
            '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        for i, column in enumerate(df.columns):
            colorIndex = i % len(colors)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                mode='lines',
                name=column,
                line=dict(color=colors[colorIndex], width=3.5)
            ))

        fig.update_layout(
            title=title,
            xaxis=dict(title='Date'),
            yaxis=dict(title='Valeur en %'),
            showlegend=True,
            legend=dict(x=0, y=1),
            margin=dict(l=0, r=0, t=30, b=0),
            autosize=False,
            width=1850,
            height=850,
            plot_bgcolor='rgba(36,31,79,1)'
        )

        fig.show()

    @staticmethod
    def SunburstPortefeuille(data: dict, name: str):
        """
        Génère un graphique en soleil représentant la répartition d'un portefeuille.

        Args:
            data (dict): Dictionnaire contenant comme clef les tickers et comme valeur leur pourcentage.
            name (str): Nom à afficher au centre du graphique.

        Returns:
            None: Affiche le graphique en soleil (sunburst).
        """

        assert isinstance(data, dict), f"Le paramètre 'data' doit être un dictionnaire, mais {type(data).__name__} a été donné."
        assert isinstance(name, str), f"Le paramètre 'name' doit être une chaîne de caractères, mais {type(name).__name__} a été donné."

        # Arrondir les valeurs à deux chiffres après la virgule
        dataArrondi = {k: round(v, 2) for k, v in data.items()}

        # Préparation des données pour le graphique
        labels = list(dataArrondi.keys())  # Les tickers
        values = list(dataArrondi.values())  # Les pourcentages associés


        # Créer le graphique Sunburst
        fig = go.Figure(go.Sunburst(
            labels=[name] + labels,  # Ajouter le nom au centre
            parents=[""] + [name] * len(labels),  # Le centre est parent de tous les tickers
            values=[None] + values,  # Les valeurs, avec None pour le centre
            branchvalues="total",  # Les valeurs sont les pourcentages d'un tout
        ))

        # Mise en forme
        fig.update_layout(
            sunburstcolorway=["#636efa", "#EF553B", "#00cc96", "#ab63fa", "#19d3f3", 
                            "#e763fa", "#fecb52", "#ffa15a", "#ff6692", "#b6e880"],
            margin=dict(t=40, l=0, r=0, b=0)
        )

        fig.show()





    @staticmethod
    def EnregistrerDataFrameEnJson(dataFrame: pd.DataFrame, cheminFichierJson: str) -> None:
        """
        Enregistre un DataFrame au format JSON dans le fichier spécifié, avec les dates comme clés et les montants comme valeurs.

        Args:
            dataFrame (pd.DataFrame): Le DataFrame à enregistrer. L'index doit être constitué de dates, et le DataFrame doit avoir une seule colonne avec les montants.
            cheminFichierJson (str): Le chemin du fichier JSON dans lequel enregistrer le DataFrame.

        Returns:
            None
        """
        # Vérifications des types des arguments
        assert isinstance(dataFrame, pd.DataFrame), f"dataFrame doit être un pd.DataFrame, mais c'est {type(dataFrame).__name__}."
        assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith(".json"), \
            f"cheminFichierJson doit être une chaîne se terminant par '.json', mais c'est {type(cheminFichierJson).__name__}."

        # Vérifier que l'index du DataFrame est constitué de dates
        assert pd.api.types.is_datetime64_any_dtype(dataFrame.index), "L'index du DataFrame doit être de type datetime."

        # Vérifier que le DataFrame a exactement une colonne
        assert dataFrame.shape[1] == 1, "Le DataFrame doit contenir exactement une colonne avec les montants."

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

    def RepartitionPortefeuille(self, date: str):
        """
        Calcule la répartition en pourcentage du portefeuille

        Args:
            date (str): Date à laquelle il faut calculer la répartition en pourcentage du portefeuille (%Y-%m-%d)

        Returns:
            dict: Dictionnaire contenant comme clef les tickers et comme valeur leur pourcentage,
                trié par ordre décroissant et sans les valeurs manquantes ou nulles.
        """
        
        assert isinstance(date, str), f"La date donnée n'est pas une chaîne de caractère: {type(date).__name__}"
        dateObj = datetime.strptime(date, "%Y-%m-%d")
        assert dateObj in self.evolutionPrixTickersBrut.index, f"La date {date} ne se trouve pas dans le DataFrame"
        
        # Sélection des valeurs des tickers pour la date donnée
        valeursDate = self.evolutionPrixTickersBrut.loc[dateObj]
        sommeTotale = valeursDate.sum()
        
        assert sommeTotale > 0, f"La somme des valeurs pour la date {date} est égale à zéro."
        
        # Calcul du pourcentage de chaque ticker
        repartition = (valeursDate / sommeTotale) * 100
        
        # Suppression des valeurs manquantes (NaN) et des valeurs nulles
        repartition = repartition.dropna()
        repartition = repartition[repartition > 0]
        
        # Tri des valeurs par ordre décroissant
        repartitionTrie = repartition.sort_values(ascending=False)
        
        # Retourne le résultat sous forme de dictionnaire {ticker: pourcentage}
        return repartitionTrie.to_dict()










# bourse = TradeRepublicPerformance("Bilan/Archives/Bourse/Transactions.json")
# pourcentage = bourse.RepartitionPortefeuille("2024-09-16")
# bourse.SunburstPortefeuille(pourcentage, "Portefeuille")
# bourse.PlotlyInteractivePlot(bourse.GetEvolutionPourcentagePortefeuille())