from modules.recuperationDonnees import RecuperationDonnees
from .graphiques.GraphiquesDashboard import GraphiquesDashboard 
from .portefeuilles.monPortefeuille import MonPortefeuille
from .portefeuilles.dca import DCA
from .portefeuilles.replication import Replication

import pandas as pd
from datetime import datetime
import os
import copy


class Bourse(RecuperationDonnees, GraphiquesDashboard , MonPortefeuille, DCA, Replication):
    """
    La classe TradeRepublicPerformance est conçue pour analyser et visualiser la performance des transactions boursières
    à partir d’un fichier JSON contenant les données de transactions.
    Elle permet de calculer et de suivre l’évolution des investissements, des prix des actions, et de la performance globale du portefeuille.
    """

    def __init__(self, repertoireJson: str):
        """
        Args:
            repertoireJson (str): Le chemin du répertoire où les fichiers JSON sont stockés.
        """
        assert isinstance(repertoireJson, str), f"repertoireJson doit être une chaîne de caractères: ({type(repertoireJson)})"
        assert os.path.isdir(repertoireJson), f"directory doit être un répertoire valide : ({repertoireJson})"

        self.repertoireJson = repertoireJson

        self.startDate = self.PremiereDateDepot()
        self.endDate = datetime.today()

        self.datesAchats = self.RecuperationTickerBuySell((repertoireJson + "Ordres d'achats.json"))
        self.datesVentes = self.RecuperationTickerBuySell((repertoireJson + "Ordres de ventes.json"))
        self.prixTickers = self.DownloadTickersPrice(list(self.datesAchats.keys()))

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
        self.EnregistrerDataFrameEnJson(repertoireJson + "Portefeuille.json")


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

        tickersAll = sorted(set([ticker for portfolio in self.portfolioPercentage for ticker in portfolio[0].keys()]))
        tickersInitial = sorted(list(self.prixTickers.columns))
        tickerUnique = [item for item in tickersAll if item not in tickersInitial]

        prixTickersUnique = self.DownloadTickersPrice(tickerUnique)
        self.prixTickers = pd.concat([self.prixTickers, prixTickersUnique], axis=1)
    
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
    

