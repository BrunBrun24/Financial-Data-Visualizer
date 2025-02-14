from modules.recuperationDonnees import RecuperationDonnees
from .graphiques.graphiquesDashboard import GraphiquesDashboard
from .portefeuilles.monPortefeuille import MonPortefeuille
from .portefeuilles.dollarCostAveraging import DollarCostAveraging
from .portefeuilles.dollarCostValue import DollarCostValue
from .portefeuilles.moyenneMobile import MoyenneMobile
from .portefeuilles.replication import Replication

import pandas as pd
from datetime import datetime
import os
import json

class PortefeuilleBourse(RecuperationDonnees, GraphiquesDashboard, MonPortefeuille, DollarCostAveraging, DollarCostValue, MoyenneMobile, Replication):
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

        RecuperationDonnees.__init__(self, repertoireJson)  # Passe la valeur au parent si nécessaire
        GraphiquesDashboard.__init__(self)

        self.repertoireJson = repertoireJson

        self.startDate = self.PremiereDateDepot()
        self.endDate = datetime.today()
        self.datesAchats = self.RecuperationTickerBuySell((repertoireJson + "Ordres d'achats.json"))
        self.datesVentes = self.RecuperationTickerBuySell((repertoireJson + "Ordres de ventes.json"))

        self.prixFifoTickers = {}
        self.montantsInvestisTickers = {}
        self.montantsVentesTickers = {}
        self.tickersTWR = {}
        self.prixNetTickers = {}
        self.prixBrutTickers = {}
        self.dividendesTickers = {}
        self.fondsInvestisTickers = {}

        self.portefeuilleTWR = pd.DataFrame(dtype=float)
        self.prixNetPortefeuille = pd.DataFrame(dtype=float)
        self.pourcentagesMensuelsPortefeuille = pd.DataFrame(dtype=float)
        self.soldeCompteBancaire = pd.DataFrame(dtype=float)
        self.cash = pd.DataFrame(dtype=float)
        self.montantsInvestisPortefeuille = self.EvolutionArgentInvestis()

        # Ajoute sur le graphique mon portefeuille
        self.MonPortefeuille(repertoireJson)

        nameCompteBancaire = "Mon Portefeuille"
        # Dictionnaire pour enregistrer les DataFrame dans des fichiers JSON
        enregistrerDataFrameSerie = [
            {"data": self.prixFifoTickers[nameCompteBancaire], "file": "prixFifoTickers"},
            {"data": self.montantsInvestisTickers[nameCompteBancaire], "file": "montantsInvestisTickers"},
            {"data": self.montantsVentesTickers[nameCompteBancaire], "file": "montantsVentesTickers"},
            {"data": self.tickersTWR[nameCompteBancaire], "file": "tickersTWR"},
            {"data": self.prixNetTickers[nameCompteBancaire], "file": "prixNetTickers"},
            {"data": self.prixBrutTickers[nameCompteBancaire], "file": "prixBrutTickers"},
            {"data": self.dividendesTickers[nameCompteBancaire], "file": "dividendesTickers"},
            {"data": self.fondsInvestisTickers[nameCompteBancaire], "file": "fondsInvestisTickers"},
            {"data": self.portefeuilleTWR[nameCompteBancaire], "file": "portefeuilleTWR"},
            {"data": self.prixNetPortefeuille[nameCompteBancaire], "file": "prixNetPortefeuille"},
            {"data": self.pourcentagesMensuelsPortefeuille[nameCompteBancaire], "file": "pourcentagesMensuelsPortefeuille"},
            {"data": self.soldeCompteBancaire[nameCompteBancaire], "file": "soldeCompteBancaire"},
            {"data": self.cash[nameCompteBancaire], "file": "cash"},
        ]

        self.EnregistrerJson(enregistrerDataFrameSerie, (repertoireJson + "Mon Portefeuille/"))
        self.EnregistreSerieEnJson(self.soldeCompteBancaire[nameCompteBancaire], (repertoireJson + "Portefeuille.json"))


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

        prixTickersUnique = self.DownloadTickersPrice(tickerUnique, self.startDate, self.endDate)
        self.prixTickers = pd.concat([self.prixTickers, prixTickersUnique], axis=1)



    def EnregistrerJson(self, dataList: list, cheminFichierJson: str):
        """
        Enregistre une liste de données (Series ou DataFrame) dans des fichiers JSON.

        Args:
            dataList (list): Une liste de dictionnaires, où chaque dictionnaire contient :
                - "data": Les données à enregistrer (pd.Series ou pd.DataFrame).
                - "file": Le nom du fichier (sans l'extension) où les données seront enregistrées.
            cheminFichierJson (str): Le chemin complet du fichier JSON où la série sera sauvegardée.
        """
        assert isinstance(dataList, list), "dataList doit être une liste de dictionnaires."
        assert isinstance(cheminFichierJson, str), "Le chemin du fichier doit être une chaîne de caractères."

        for data in dataList:
            assert isinstance(data, dict), "Chaque élément de dataList doit être un dictionnaire."
            assert "data" in data and "file" in data, \
                "Chaque dictionnaire doit contenir les clés 'data' (les données) et 'file' (nom du fichier)."
            assert isinstance(data["file"], str) and data["file"].strip(), \
                "La clé 'file' doit contenir une chaîne non vide représentant le nom du fichier."

            filePath = os.path.join(cheminFichierJson, f"{data['file']}.json")

            # Vérifier le type de données et appeler les méthodes correspondantes
            if isinstance(data["data"], pd.Series):
                cleanedData = data["data"].fillna(0)
                self.EnregistreSerieEnJson(cleanedData, filePath)
            elif isinstance(data["data"], pd.DataFrame):
                cleanedData = data["data"].fillna(0)
                self.EnregistreDataFrameEnJson(cleanedData, filePath)
            else:
                raise TypeError(f"Le type des données est invalide : attendu pd.Series ou pd.DataFrame, mais obtenu {type(data['data'])}.")

    @staticmethod
    def EnregistreSerieEnJson(serie: pd.Series, cheminFichierJson: str):
        """
        Enregistre une série Pandas sous format JSON dans un fichier avec un index datetime conservé.

        Args:
            serie (pd.Series): La série Pandas à enregistrer.
            cheminFichierJson (str): Le chemin complet du fichier JSON où la série sera sauvegardée.
        """
        assert isinstance(serie, pd.Series), "La variable 'serie' doit être une instance de pd.Series."
        assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith('.json'), \
            "Le chemin du fichier doit être une chaîne de caractères se terminant par '.json'."

        # Convertir l'index en datetime si nécessaire
        if not pd.api.types.is_datetime64_any_dtype(serie.index):
            try:
                serie.index = pd.to_datetime(serie.index)
            except Exception as e:
                raise ValueError(f"Impossible de convertir l'index en datetime : {e}")

        # Préparer les données pour le format JSON
        dictData = {
            index.strftime('%Y-%m-%d'): value
            for index, value in serie.items()
        }

        # Écriture dans un fichier JSON
        os.makedirs(os.path.dirname(cheminFichierJson), exist_ok=True)  # Créer les dossiers si nécessaire
        with open(cheminFichierJson, 'w', encoding='utf-8') as f:
            json.dump(dictData, f, indent=4, ensure_ascii=False)

    @staticmethod
    def EnregistreDataFrameEnJson(dataFrame: pd.DataFrame, cheminFichierJson: str):
        """
        Enregistre un DataFrame Pandas sous format JSON dans un fichier avec un index datetime conservé.

        Args:
            dataFrame (pd.DataFrame): Le DataFrame Pandas à enregistrer.
            cheminFichierJson (str): Le chemin complet du fichier JSON où le DataFrame sera sauvegardé.
        """
        assert isinstance(dataFrame, pd.DataFrame), "La variable 'dataFrame' doit être une instance de pd.DataFrame."
        assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith('.json'), \
            "Le chemin du fichier doit être une chaîne de caractères se terminant par '.json'."

        # Conversion de l'index en chaînes ISO 8601 pour JSON
        dictData = dataFrame.reset_index()
        indexColumnName = dictData.columns[0]
        dictData[indexColumnName] = dictData[indexColumnName].apply(lambda x: x.strftime('%Y-%m-%d'))
        dictData = dictData.rename(columns={indexColumnName: 'Date'}).to_dict(orient='records')

        # Écriture dans un fichier JSON
        os.makedirs(os.path.dirname(cheminFichierJson), exist_ok=True)  # Créer les dossiers si nécessaire
        with open(cheminFichierJson, 'w', encoding='utf-8') as f:
            json.dump(dictData, f, indent=4, ensure_ascii=False)


