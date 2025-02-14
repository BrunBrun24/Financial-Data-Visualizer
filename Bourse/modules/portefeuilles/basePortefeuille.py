import yfinance as yf
import pandas as pd
from datetime import timedelta

class BasePortefeuille:
    
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

            if montantsInvestisTotal + montantGagneMoisPasse == 0:
                pourcentageEvolution = 0
            else:
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
    def CalculerEvolutionPourcentagePortefeuille(evolutionGainsPertesPortefeuille: pd.Series, argentInvesti: float) -> pd.Series:
        """
        Calcule l'évolution en pourcentage de la valeur totale du portefeuille par rapport à l'argent investi.

        Args:
            evolutionGainsPertesPortefeuille (pd.Serie): Serie contenant les valeurs globales du portefeuille, indexé par date.
            argentInvesti (float): Montant total investi dans le portefeuille.

        Returns:
            pd.DataFrame: DataFrame contenant l'évolution en pourcentage de la valeur totale du portefeuille par rapport à l'argent investi.
        """
        assert isinstance(evolutionGainsPertesPortefeuille, pd.Series), "evolutionGainsPertesPortefeuille doit être une Serie"
        assert isinstance(argentInvesti, (int, float)), "argentInvesti doit être un nombre (int ou float)"
 
        # Calcul de l'évolution en pourcentage par rapport à l'argent investi
        evolutionPourcentage = (((argentInvesti + evolutionGainsPertesPortefeuille) - argentInvesti) / argentInvesti) * 100

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
        
        # Initialiser le DataFrame pour stocker les valeurs composées de plus/moins-value
        evolutionArgentsInvestisTickers = pd.DataFrame(index=montantsInvestis.index, columns=montantsInvestis.columns, dtype=float)
        evolutionGainsPertesTickers = pd.DataFrame(index=montantsInvestis.index, columns=montantsInvestis.columns, dtype=float)

        # Calcul de la plus-value composée pour chaque jour
        for ticker in montantsInvestis.columns:
            
            # Initialiser avec la valeur d'achat initiale pour chaque ticker
            evolutionArgentsInvestisTickers.loc[montantsInvestis.index[0], ticker] = montantsInvestis.loc[montantsInvestis.index[0], ticker]
            evolutionGainsPertesTickers.loc[montantsInvestis.index[0], ticker] = 0

            montantsInvestisCumules = montantsInvestis.loc[montantsInvestis.index[0], ticker]

            for i in range(1, len(montantsInvestis.index)):
                datePrecedente = montantsInvestis.index[i-1]
                dateActuelle = montantsInvestis.index[i]

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
            evolutionPrixBrutTickers (pd.DataFrame): Évolution brute des prix des tickers.
            tickerPriceDf (pd.DataFrame): Prix des tickers correspondants.

        Returns:
            pd.DataFrame: Évolution des dividendes pour chaque ticker, répartis sur les dates du portefeuille.
        """
        assert isinstance(evolutionPrixBrutTickers, pd.DataFrame), "evolutionPrixBrutTickers doit être un DataFrame"
        assert isinstance(tickerPriceDf, pd.DataFrame), "tickerPriceDf doit être un DataFrame"
        assert evolutionPrixBrutTickers.index.equals(tickerPriceDf.index), "Les index des DataFrames doivent être identiques"

        # Initialisation du DataFrame des dividendes
        tickersDividendes = pd.DataFrame(0, index=evolutionPrixBrutTickers.index, columns=evolutionPrixBrutTickers.columns, dtype=float)

        for ticker in evolutionPrixBrutTickers.columns:
            # Récupération des dividendes
            dividendes = yf.Ticker(ticker).dividends

            # Suppression de la timezone si nécessaire
            dividendes.index = dividendes.index.tz_localize(None) if dividendes.index.tz else dividendes.index

            # Aligner les dividendes sur l'index des prix du portefeuille
            dividendes = dividendes.reindex(evolutionPrixBrutTickers.index, method='ffill').fillna(0)

            # Calculer le montant des dividendes en fonction des prix
            tickersDividendes[ticker] = round(dividendes * evolutionPrixBrutTickers[ticker] / tickerPriceDf[ticker], 2)

        return tickersDividendes
    
    def CalculerPrixFifoTickers(self, montantsInvestis: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule le prix d'achat moyen (FIFO) pour chaque action basée sur les montants investis et les prix des tickers.

        Args:
            montantsInvestis (pd.DataFrame): DataFrame contenant les montants investis pour chaque action en colonnes,
                                            avec les dates en index.

        Returns:
            pd.DataFrame: DataFrame contenant les prix d'achat moyens (FIFO) pour chaque action.
        """
        assert isinstance(montantsInvestis, pd.DataFrame), "montantsInvestis doit être un DataFrame"

        # Nettoyage des données : conserver uniquement les lignes où les montants investis ne sont pas tous nuls
        montantsInvestis = montantsInvestis.loc[montantsInvestis.sum(axis=1) != 0]
        prixTickers = self.prixTickers.loc[montantsInvestis.index]

        # Initialisation du DataFrame pour stocker les prix FIFO
        prixFifo = pd.DataFrame(index=montantsInvestis.index, columns=montantsInvestis.columns, dtype=float)

        # Boucle sur chaque ticker pour calculer le prix d'achat moyen
        for ticker in montantsInvestis.columns:
            montants = montantsInvestis[ticker]
            prix = prixTickers[ticker]
            
            quantiteTotale = 0
            totalInvesti = 0
            
            for date in montants.index:
                montantInvesti = montants[date]
                prixDuJour = prix[date]
                
                if montantInvesti > 0:  # Investissement effectué ce jour-là
                    quantiteAchetee = montantInvesti / prixDuJour
                    quantiteTotale += quantiteAchetee
                    totalInvesti += montantInvesti

                # Calcul du prix moyen FIFO si une quantité totale existe
                prixFifo.loc[date, ticker] = totalInvesti / quantiteTotale if quantiteTotale > 0 else 0

        # Compléter les données entre startDate et endDate
        dateRange = pd.date_range(start=self.startDate, end=self.endDate, freq='D')
        prixFifo = prixFifo.reindex(dateRange)  # Ajouter les dates manquantes
        prixFifo = prixFifo.ffill()  # Propager les dernières valeurs disponibles
        firstInvestmentDate = montantsInvestis.index.min() - timedelta(days=1)
        prixFifo.loc[:firstInvestmentDate] = 0

        return prixFifo
    ##########################
    
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
    
    