from .recuperationDonnees import RecuperationDonnees

import pandas as pd
from datetime import datetime
import os
import json


class Bourse(RecuperationDonnees):

    def EvolutionTradeRepublic(self):
        """Charge les données des fichiers JSON et les ajoutent à un DataFrame existant sous le nom de colonne 'Bourse'"""

        directory = "Bilan/Archives/Bourse/"
        assert os.path.isdir(directory), f"Le dossier n'exsiste pas: {directory}"

        # L'ordre dans le dictionnaire définit la continuité des feuilles dans le fichier Excel
        operations = [
            {"nomFichier": directory + "Argents investis.json", "colonneIndexSource": "Date de valeur", "colonneADeplacerSource": "Montant investi", "colonneDestination": "Argents investis"},
            {"nomFichier": directory + "Argents vendus.json", "colonneIndexSource": "Date de valeur", "colonneADeplacerSource": "Montant gagné", "colonneDestination": "Argents vendus"},
            {"nomFichier": directory + "Dépôts d'espèces.json", "colonneIndexSource": "Date de valeur", "colonneADeplacerSource": "Prix dépôt net", "colonneDestination": "Dépôts d'argent"},
            {"nomFichier": directory + "Dividendes.json", "colonneIndexSource": "Date de valeur", "colonneADeplacerSource": "Dividendes net", "colonneDestination": "Dividendes"},
            {"nomFichier": directory + "Interêts.json", "colonneIndexSource": "Date d'effet", "colonneADeplacerSource": "Interêts net", "colonneDestination": "Interêts"},
            {"nomFichier": directory + "Retraits.json", "colonneIndexSource": "Date de la commande", "colonneADeplacerSource": "Retraits net", "colonneDestination": "Dépenses"},
        ]

        for operation in operations:
            df = self.DownloadDataFrameInJson(operation["nomFichier"])
            self.AjouterDonneesSiNonExistent(df, operation["colonneIndexSource"], operation["colonneADeplacerSource"], operation["colonneDestination"])

    def AjouterDonneesSiNonExistent(self, dfSource: pd.DataFrame, colonneIndexSource: str, colonneADeplacerSource: str, colonneDestination: str):
        """
        Ajoute les données de la colonne de dfSource dans self.tradeRepublic en index.

        Args:
            dfSource (pd.DataFrame): La DataFrame source contenant les données à ajouter.
            colonneIndexSource (str): Nom de la colonne dans dfSource contenant les valeurs d'index.
            colonneADeplacerSource (str): Nom de la colonne dans dfSource contenant les prix.
            colonneDestination (str): Nom de la colonne dans self.tradeRepublic où les prix seront ajoutés.
        """
        # Vérifications des types des arguments
        assert isinstance(dfSource, pd.DataFrame), f"dfSource doit être un pd.DataFrame: {type(dfSource)}."
        assert isinstance(colonneIndexSource, str), f"colonneIndexSource doit être une chaîne: {type(colonneIndexSource)}."
        assert isinstance(colonneADeplacerSource, str), f"colonneADeplacerSource doit être une chaîne: {type(colonneADeplacerSource)}."
        assert isinstance(colonneDestination, str), f"colonneDestination doit être une chaîne: {type(colonneDestination)}."

        # Vérifie que les colonnes d'intérêt existent dans dfSource
        assert colonneIndexSource in dfSource.columns, f"Colonne {colonneIndexSource} inexistante dans dfSource."
        assert colonneADeplacerSource in dfSource.columns, f"Colonne {colonneADeplacerSource} inexistante dans dfSource."

        # Vérifie que la colonne de destination existe dans self.tradeRepublic
        assert colonneDestination in self.tradeRepublic.columns, f"Colonne {colonneDestination} inexistante dans self.tradeRepublic."

        # Conversion de l'index de type entier (timestamp en millisecondes) en datetime et formatage au format '%Y%m%d'
        if pd.api.types.is_integer_dtype(dfSource[colonneIndexSource]):
            # Convertir les entiers en dates
            dfSource[colonneIndexSource] = pd.to_datetime(dfSource[colonneIndexSource], unit='ms', errors='coerce')
            # Formatage de la date au format '%Y%m%d'
            dfSource[colonneIndexSource] = dfSource[colonneIndexSource].dt.strftime('%Y-%m-%d')
            assert not dfSource[colonneIndexSource].isnull().any(), "Certaines valeurs d'index n'ont pas pu être converties en date."

        # Itérer sur les lignes de dfSource pour ajouter des données si elles n'existent pas déjà
        for index, row in dfSource.iterrows():
            valeurIndex = row[colonneIndexSource]
            valeurPrix = row[colonneADeplacerSource]

            # Vérifie si la valeur n'existe pas déjà dans self.tradeRepublic
            if valeurIndex not in self.tradeRepublic.index:
                self.tradeRepublic.at[valeurIndex, colonneDestination] = valeurPrix
            else:
                self.tradeRepublic.at[valeurIndex, colonneDestination] += valeurPrix

        self.tradeRepublic.fillna(0, inplace=True)
        self.tradeRepublic.sort_index(axis=0, ascending=True, inplace=True)

    def EvolutionDuPatrimoineBourse(self, cheminFichierJson: str) -> pd.DataFrame:
        """
        Charge les données d'un fichier JSON et les ajoutent à un DataFrame existant sous le nom de colonne 'Bourse'.

        Args:
            cheminFichierJson (str): Le chemin du fichier JSON à lire.
            self.patrimoine (pd.DataFrame): Le DataFrame existant auquel ajouter les nouvelles données. Le DataFrame doit avoir une colonne nommée 'Bourse'.

        Returns:
            pd.DataFrame: Le DataFrame mis à jour avec les nouvelles données sous la colonne 'Bourse'.
        """
        # Vérifications des types des arguments
        assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith(".json"), \
            f"cheminFichierJson doit être une chaîne se terminant par '.json': {type(cheminFichierJson)}."

        # Lire le fichier JSON
        with open(cheminFichierJson, 'r', encoding="utf-8") as f:
            jsonData = f.read()

        # Convertir le JSON en dictionnaire
        dictData = json.loads(jsonData)

        # Convertir le dictionnaire en DataFrame
        dataFrameJson = pd.DataFrame(list(dictData.items()), columns=['Date', 'Bourse'])
        dataFrameJson['Date'] = pd.to_datetime(dataFrameJson['Date'])  # Convertir la colonne 'Date' en type datetime

        # Assurer que les dates du nouveau DataFrame sont uniques et triées
        dataFrameJson = dataFrameJson.set_index('Date').sort_index()
        
        # # Ajouter 2 jours à chaque date dans l'index
        # dataFrameJson.index = dataFrameJson.index - pd.DateOffset(days=2)

        portefeuilleTradeRepublic = dataFrameJson

        # # Récupérer toutes les données concernant Trade Republic
        # tradeRepublicModifie = self.ModificationTradeRepublic()

        # # On prend "Bilan False" pour avoir la courbe du patrimoine lisse
        # portefeuilleTradeRepublic["Bourse"] += tradeRepublicModifie["Bilan false"]

        portefeuilleTradeRepublic.sort_index(axis=0, ascending=True, inplace=True)
        self.patrimoine = self.patrimoine.combine_first(dataFrameJson)

    def ModificationTradeRepublic(self) -> pd.DataFrame:
        """
        Modifie le DataFrame de Trade Republic en ajoutant les dates manquantes, puis calcule le bilan avec et sans ajustement
        pour lisser les dépôts d'argent.

        La méthode crée un nouvel index avec des dates continues, fusionne le DataFrame original avec cet index, remplit les
        valeurs manquantes avec zéro, puis calcule deux colonnes de bilan : une avec les dépôts ajustés (décalés de deux jours)
        et une sans ajustement.

        Returns:
            pd.DataFrame: Un DataFrame contenant deux colonnes de bilan ('Bilan true' et 'Bilan false').
        """
        # Assertions pour vérifier les types des objets et leur validité
        assert hasattr(self, 'tradeRepublic'), "L'objet self doit contenir l'attribut 'tradeRepublic'."
        assert isinstance(self.tradeRepublic, pd.DataFrame), f"self.tradeRepublic doit être un DataFrame: ({type(self.tradeRepublic)})"
        # S'assurer que les colonnes nécessaires existent dans le DataFrame
        requiredColumns = ["Dépôts d'argent", "Argents investis", "Argents vendus", "Dividendes", "Interêts", "Dépenses"]
        for column in requiredColumns:
            assert column in self.tradeRepublic.columns, f"La colonne '{column}' doit être présente dans le DataFrame tradeRepublic."

        # Créer le DataFrame self.tradeRepublic
        self.EvolutionTradeRepublic()
        # Copier le DataFrame pour éviter de modifier l'original
        tradeRepublicModifie = self.tradeRepublic.copy()

        # Assurez-vous que l'index est en datetime
        if not pd.api.types.is_datetime64_any_dtype(tradeRepublicModifie.index):
            tradeRepublicModifie.index = pd.to_datetime(tradeRepublicModifie.index)

        minDate = tradeRepublicModifie.index.min()
        maxDate = datetime.today()
        dateRange = pd.date_range(start=minDate, end=maxDate, freq='D')
        newIndex = pd.DataFrame(index=dateRange)
        # Fusionner le DataFrame avec les dates manquantes avec l'ancien DataFrame
        tradeRepublicModifie = newIndex.join(tradeRepublicModifie, how='left')

        nouveauDataFrame = pd.DataFrame(index=tradeRepublicModifie.index)
        tradeRepublicModifie.fillna(0, inplace=True)
        # Calculer le bilan en utilisant les colonnes des transactions financières
        nouveauDataFrame['Bilan true'] = tradeRepublicModifie["Dépôts d'argent"].cumsum() + tradeRepublicModifie['Argents investis'].cumsum() + tradeRepublicModifie['Argents vendus'].cumsum() + tradeRepublicModifie['Dividendes'].cumsum() + tradeRepublicModifie['Interêts'].cumsum() - tradeRepublicModifie['Dépenses'].cumsum()


        ################ On décale les montants des dépôts pour que le niveau du patrimoine soit lisse au lieu d'avoir des pics ################
        nouveauDataFrameAdapteAuPatrimoinePourEtreLisse = pd.DataFrame()
        nouveauDataFrameAdapteAuPatrimoinePourEtreLisse['Dépôts d\'argent'] = tradeRepublicModifie['Dépôts d\'argent']
        # Ajouter 2 jours à chaque date dans l'index
        nouveauDataFrameAdapteAuPatrimoinePourEtreLisse.index = nouveauDataFrameAdapteAuPatrimoinePourEtreLisse.index + pd.DateOffset(days=2)
        tradeRepublicModifie["Dépôts d'argent"] = nouveauDataFrameAdapteAuPatrimoinePourEtreLisse['Dépôts d\'argent']
        tradeRepublicModifie.fillna(0, inplace=True)
        # Calculer le bilan en utilisant les colonnes des transactions financières
        nouveauDataFrame['Bilan false'] = tradeRepublicModifie["Dépôts d'argent"].cumsum() + tradeRepublicModifie['Argents investis'].cumsum() + tradeRepublicModifie['Argents vendus'].cumsum() + tradeRepublicModifie['Dividendes'].cumsum() + tradeRepublicModifie['Interêts'].cumsum() - tradeRepublicModifie['Dépenses'].cumsum()

        return nouveauDataFrame
    
