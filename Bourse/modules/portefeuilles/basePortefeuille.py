import pandas as pd
from collections import defaultdict


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
    ##########################

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
    