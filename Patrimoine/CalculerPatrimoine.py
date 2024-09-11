import os
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime


class Patrimoine:
    """
    La classe `Patrimoine` est conçue pour gérer et analyser l'évolution du patrimoine financier à partir de transactions. 
    Elle permet de charger des données depuis des fichiers JSON, de calculer l'évolution du patrimoine quotidiennement, 
    de transformer les données en différents formats, et de visualiser les résultats à l'aide de graphiques interactifs.

    Attributs:
        - `argentCompteCourant` (float): Montant initial sur le compte courant.
        - `argentLivretA` (float): Montant initial sur le livret A.
        - `patrimoine` (pd.DataFrame): DataFrame contenant les données du patrimoine avec les dates comme index.

    Méthodes:
        - `__init__(self)`: Initialise les attributs de la classe avec les montants de départ pour les comptes et un DataFrame vide pour le patrimoine.
        - `GetArgentCompteCourant(self)`: Retourne le montant actuel sur le compte courant.
        - `GetArgentLivretA(self)`: Retourne le montant actuel sur le livret A.
        - `GetPatrimoine(self)`: Retourne le DataFrame contenant les données du patrimoine.
        - `GetPatrimoine(self)`: Retourne le DataFrame contenant les données de Trade Republic.
        - `EvolutionDuPatrimoine(self, nomDuCompte, argent, dossierCompte)`: Calcule l'évolution quotidienne du patrimoine en fonction des transactions JSON et met à jour le DataFrame.
        - `SelectionnerDates(self, freq)`: Ajoute des dates à une fréquence spécifiée au DataFrame, garde seulement ces dates, et complète les valeurs manquantes.
        - `CalculPatrimoineDeDepart(argent, directory)`: Calcule le patrimoine initial à partir des transactions trouvées dans les fichiers JSON.
        - `TransformerDossierJsonEnDataFrame(cheminDossier)`: Charge et combine les fichiers JSON d'un dossier en un DataFrame, trié par date d'opération.
        - `TransformerDataframe(df)`: Transforme un DataFrame large en un format long avec 'Date', 'Type', et 'Montant'.
        - `AfficheGraphiqueInteractif(self)`: Affiche un graphique interactif de l'évolution du patrimoine avec des annotations de pourcentage de variation.
        - `DetermineColor(value)`: Détermine les couleurs pour les annotations en fonction de la valeur des pourcentages de variation.
        - `ObtenirAnnotations(self, livret)`: Génère des annotations pour un graphique Plotly basées sur les pourcentages de variation moyenne.
        - `CalculEvolutionMoyenneParMois(self, patrimoine)`: Calcule l'évolution moyenne mensuelle et annuelle des données de patrimoine.
    """

    def __init__(self) -> None:
        """Initialise le patrimoine avec des montants fixes et un DataFrame vide pour enregistrer les transactions."""
        # Argent initial (2022-10-27)
        self.argentCompteCourant = 264.13
        self.argentLivretA = 10045.71
        self.patrimoine = pd.DataFrame()
        self.tradeRepublic = pd.DataFrame(columns=["Dépôts d'argent", "Argents investis", "Argents vendus", "Dividendes", "Interêts", "Dépenses"])

    def GetArgentCompteCourant(self) -> float:
        """Retourne le montant actuel du compte courant."""
        return self.argentCompteCourant

    def GetArgentLivretA(self) -> float:
        """Retourne le montant actuel du livret A."""
        return self.argentLivretA

    def GetPatrimoine(self) -> pd.DataFrame:
        """Retourne le DataFrame contenant les informations du patrimoine."""
        return self.patrimoine

    def GetTradeRepublic(self) ->pd.DataFrame:
        return self.tradeRepublic



    ################# BOURSE #################
    def EvolutionTradeRepublic(self):
        """
        Charge les données des fichiers JSON et les ajoutent à un DataFrame existant sous le nom de colonne 'Bourse'
        """
        directory = "Bilan/Archives/Bourse/"
        assert os.path.isdir(directory), "Le dossier n'exsiste pas"

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

        self.tradeRepublic.sort_index(axis=0, ascending=True, inplace=True)

    def AjouterDonneesSiNonExistent(self, dfSource, colonneIndexSource, colonneADeplacerSource, colonneDestination):
        """
        Ajoute les données de la colonne de dfSource dans self.tradeRepublic en index
        si elles n'existent pas déjà, et assigne les valeurs de prix à la colonne spécifiée.

        Args:
            dfSource (pd.DataFrame): La DataFrame source contenant les données à ajouter.
            colonneIndexSource (str): Nom de la colonne dans dfSource contenant les valeurs d'index.
            colonneADeplacerSource (str): Nom de la colonne dans dfSource contenant les prix.
            colonneDestination (str): Nom de la colonne dans self.tradeRepublic où les prix seront ajoutés.

        Returns:
            None
        """
        # Vérifications des types des arguments
        assert isinstance(dfSource, pd.DataFrame), f"dfSource doit être un pd.DataFrame, mais c'est {type(dfSource).__name__}."
        assert isinstance(colonneIndexSource, str), f"colonneIndexSource doit être une chaîne, mais c'est {type(colonneIndexSource).__name__}."
        assert isinstance(colonneADeplacerSource, str), f"colonneADeplacerSource doit être une chaîne, mais c'est {type(colonneADeplacerSource).__name__}."
        assert isinstance(colonneDestination, str), f"colonneDestination doit être une chaîne, mais c'est {type(colonneDestination).__name__}."
        
        # Vérifie que les colonnes d'intérêt existent dans dfSource
        assert colonneIndexSource in dfSource.columns, f"Colonne {colonneIndexSource} inexistante dans dfSource."
        assert colonneADeplacerSource in dfSource.columns, f"Colonne {colonneADeplacerSource} inexistante dans dfSource."
        
        # Vérifie que la colonne de destination existe dans self.tradeRepublic
        assert colonneDestination in self.tradeRepublic.columns, f"Colonne {colonneDestination} inexistante dans self.tradeRepublic."
        
        # Ajoute les données de dfSource à self.tradeRepublic
        for _, row in dfSource.iterrows():
            index = row[colonneIndexSource]
            prix = row[colonneADeplacerSource]

            # Si l'index n'existe pas encore dans self.tradeRepublic, ajoute-le
            if index not in self.tradeRepublic.index:
                self.tradeRepublic.loc[index] = [0] * len(self.tradeRepublic.columns)
            
            # Ajoute le prix à la valeur existante ou l'initialise si c'est NaN
            if pd.isna(self.tradeRepublic.at[index, colonneDestination]):
                self.tradeRepublic.at[index, colonneDestination] = prix
            else:
                self.tradeRepublic.at[index, colonneDestination] += prix

    @staticmethod
    def DownloadDataFrameInJson(path: str) -> pd.DataFrame:
        """
        Télécharge les données d'un fichier JSON et retourne un DataFrame.

        Args:
            path (str): Le chemin vers le fichier JSON.

        Returns:
            pd.DataFrame: Les données contenues dans le fichier JSON sous forme de DataFrame.
        """
        assert isinstance(path, str) and os.path.isfile(path), f"Le fichier {path} n'existe pas ou le chemin n'est pas valide."

        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        assert isinstance(data, list), "Le contenu du fichier JSON doit être une liste d'objets (dict)."
        
        # Conversion des données en DataFrame
        dataFrame = pd.DataFrame(data)
        
        return dataFrame

    
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
            f"cheminFichierJson doit être une chaîne se terminant par '.json', mais c'est {type(cheminFichierJson).__name__}."

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
        portefeuilleTradeRepublic = dataFrameJson

        # Récupérer toutes les données concernant Trade Republic
        tradeRepublicModifie = self.ModificationTradeRepublic()

        # On prend "Bilan False" pour avoir la courbe du patrimoine lisse
        portefeuilleTradeRepublic["Bourse"] += tradeRepublicModifie["Bilan false"]

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
        assert isinstance(self.tradeRepublic, pd.DataFrame), f"self.tradeRepublic doit être un DataFrame: ({type(self.tradeRepublic).__name__})"
        # S'assurer que les colonnes nécessaires existent dans le DataFrame
        required_columns = ["Dépôts d'argent", "Argents investis", "Argents vendus", "Dividendes", "Interêts", "Dépenses"]
        for column in required_columns:
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
        
        nouvelleDataFrame = pd.DataFrame(index=tradeRepublicModifie.index)
        tradeRepublicModifie.fillna(0, inplace=True)
        # Calculer le bilan en utilisant les colonnes des transactions financières
        nouvelleDataFrame['Bilan true'] = tradeRepublicModifie["Dépôts d'argent"].cumsum() + tradeRepublicModifie['Argents investis'].cumsum() + tradeRepublicModifie['Argents vendus'].cumsum() + tradeRepublicModifie['Dividendes'].cumsum() + tradeRepublicModifie['Interêts'].cumsum() - tradeRepublicModifie['Dépenses'].cumsum()

        
        ################ On décale les montants des dépôts pour que le niveau du patrimoine soit lisse au lieu d'avoir des pics ################
        nouvelleDataFrameAdapteAuPatrimoinePourEtreLisse = pd.DataFrame()
        nouvelleDataFrameAdapteAuPatrimoinePourEtreLisse['Dépôts d\'argent'] = tradeRepublicModifie['Dépôts d\'argent']
        # Ajouter 2 jours à chaque date dans l'index
        nouvelleDataFrameAdapteAuPatrimoinePourEtreLisse.index = nouvelleDataFrameAdapteAuPatrimoinePourEtreLisse.index + pd.DateOffset(days=2)
        tradeRepublicModifie["Dépôts d'argent"] = nouvelleDataFrameAdapteAuPatrimoinePourEtreLisse['Dépôts d\'argent']
        tradeRepublicModifie.fillna(0, inplace=True)
        # Calculer le bilan en utilisant les colonnes des transactions financières
        nouvelleDataFrame['Bilan false'] = tradeRepublicModifie["Dépôts d'argent"].cumsum() + tradeRepublicModifie['Argents investis'].cumsum() + tradeRepublicModifie['Argents vendus'].cumsum() + tradeRepublicModifie['Dividendes'].cumsum() + tradeRepublicModifie['Interêts'].cumsum() - tradeRepublicModifie['Dépenses'].cumsum()
        
        return nouvelleDataFrame

    # Livret, Compte, ...
    def EvolutionDuPatrimoine(self, nomDuCompte: str, argent: float, dossierCompte: str) -> pd.DataFrame:
        """
        Calcule l'évolution du patrimoine quotidiennement basé sur les transactions trouvées dans les fichiers JSON.

        Args:
            nomDuCompte (str): Nom du compte à mettre à jour.
            argent (float): Montant initial d'argent sur le compte.
            dossierCompte (str): Chemin vers le dossier contenant les fichiers JSON avec les transactions.

        Returns:
            pd.DataFrame: Le DataFrame mis à jour avec l'évolution du patrimoine.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être un DataFrame: ({type(self.patrimoine).__name__})"
        assert isinstance(nomDuCompte, str), f"La variable nomDuCompte doit être une chaîne de caractères: ({type(nomDuCompte).__name__})"
        assert isinstance(argent, (int, float)), f"La variable argent doit être un nombre: ({type(argent).__name__})"
        assert isinstance(dossierCompte, str), f"La variable dossierCompte doit être une chaîne de caractères: ({type(dossierCompte).__name__})"
        assert os.path.exists(dossierCompte), f"Le dossier spécifié n'existe pas: {dossierCompte}"

        if nomDuCompte not in self.patrimoine.columns:
            self.patrimoine[nomDuCompte] = pd.Series(dtype=float)

        transactions = self.TransformerDossierJsonEnDataFrame(dossierCompte)

        assert pd.api.types.is_datetime64_any_dtype(transactions.index), "L'index doit être de type datetime."
        assert "MONTANT" in transactions, "La colonne 'MONTANT' est manquante dans les transactions."

        for date, row in transactions.iterrows():
            argent += row["MONTANT"]
            self.patrimoine.loc[date, nomDuCompte] = argent



    @staticmethod
    def SelectionnerDates(df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Ajoute des dates à une fréquence spécifiée dans le DataFrame, garde seulement ces dates, et complète les valeurs manquantes par la date la plus proche.

        Args:
            df (pd.DataFrame): DataFrame avec des dates comme index et plusieurs colonnes de valeurs.
            freq (str): Fréquence des dates à ajouter. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.

        Returns:
            pd.DataFrame: DataFrame mis à jour avec les dates ajoutées et les valeurs manquantes complétées.
        """
        assert isinstance(df, pd.DataFrame), f"La variable df doit être une DataFrame: ({type(df).__name__})"
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], "La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q'."

        # Convertir l'index en datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # Déterminer les dates à inclure selon la fréquence choisie
        if freq == 'D':
            period_range = pd.date_range(df.index.min(), df.index.max(), freq='D')
        elif freq == 'M':
            period_range = pd.date_range(df.index.min().replace(day=1), df.index.max().replace(day=1), freq='MS')
        elif freq == 'Y':
            period_range = pd.date_range(df.index.min().replace(month=1, day=1), df.index.max().replace(month=1, day=1), freq='YS')
        elif freq == 'W':
            period_range = pd.date_range(df.index.min() - pd.DateOffset(days=df.index.min().weekday()),
                                        df.index.max() + pd.DateOffset(days=(6 - df.index.max().weekday())), freq='W-SUN')
        elif freq == 'Q':
            period_range = pd.date_range(df.index.min() - pd.DateOffset(months=(df.index.min().month - 1) % 3),
                                        df.index.max() + pd.DateOffset(months=2 - (df.index.max().month - 1) % 3), freq='Q')

        combined_dates = pd.Index(period_range).union([df.index.max()])
        newDf = df.reindex(combined_dates)

        # S'assurer que l'index est trié
        newDf = newDf.sort_index()

        # Remplir les valeurs manquantes en utilisant les valeurs les plus proches disponibles dans le DataFrame initial
        for column in df.columns:
            # Trouver les valeurs non manquantes dans la colonne
            non_nan = df[[column]].dropna()
            # Créer une série de valeurs manquantes
            missing_values = newDf[newDf[column].isna()]
            
            if not non_nan.empty:
                # Trouver les dates les plus proches pour les valeurs manquantes
                indexer = non_nan.index.get_indexer(missing_values.index, method='nearest')

                for i, missing_date in enumerate(missing_values.index):
                    closest_date = non_nan.index[indexer[i]]
                    # Remplacer la valeur manquante avec la valeur de la date la plus proche
                    newDf.loc[missing_date, column] = df.loc[closest_date, column]

        if freq == 'Y':
            newDf.index = [i.strftime('%Y') for i in newDf.index]

        return newDf

    @staticmethod
    def CalculPatrimoineDeDepart(argent: float, directory: str) -> float:
        """
        Calculer le patrimoine initial basé sur les transactions trouvées dans les fichiers JSON.

        Args:
            argent: Argent sur le compte aujourd'hui.
            directory: Chemin vers le dossier contenant les fichiers JSON.

        Returns:
            float: Montant initial du compte courant.
        """
        assert isinstance(argent, (int, float)), f"La variable argent doit être un nombre: ({type(argent).__name__})"
        assert isinstance(directory, str), f"La variable directory doit être une chaîne de caractères: ({type(directory).__name__})"
        assert os.path.exists(directory), f"Le dossier spécifié n'existe pas: {directory}"

        for fichier in os.listdir(directory):
            if fichier.endswith(".json"):
                with open(os.path.join(directory, fichier), 'r', encoding="UTF-8") as f:
                    data = json.load(f)
                    for categorie, operations in data.items():
                        for operation in operations:
                            argent += operation["MONTANT"]
        return argent

    @staticmethod
    def TransformerDossierJsonEnDataFrame(cheminDossier: str) -> pd.DataFrame:
        """
        Charge tous les fichiers JSON d'un dossier, les combine en un DataFrame, avec 'DATE D'OPÉRATION' comme index,
        et trie les données par cet index.

        Args:
            cheminDossier: Chemin vers le dossier contenant les fichiers JSON.

        Returns:
            pd.DataFrame: DataFrame combiné avec les transactions de tous les fichiers.
        """
        assert isinstance(cheminDossier, str), f"Le cheminDossier doit être une chaîne de caractères: ({type(cheminDossier).__name__})"
        assert os.path.isdir(cheminDossier), f"Le chemin spécifié n'est pas un dossier valide: ({cheminDossier})"

        lignes = []
        for fichier in os.listdir(cheminDossier):
            if fichier.endswith('.json'):
                cheminFichier = os.path.join(cheminDossier, fichier)
                with open(cheminFichier, 'r', encoding='UTF-8') as f:
                    data = json.load(f)
                    for categorie, transactions in data.items():
                        assert isinstance(transactions, list), f"Les transactions doivent être une liste: ({transactions})"
                        for transaction in transactions:
                            assert isinstance(transaction, dict), f"Chaque transaction doit être un dictionnaire: ({transaction})"
                            assert "DATE D'OPÉRATION" in transaction, f"Clé 'DATE D'OPÉRATION' manquante: ({transaction})"
                            transaction['Catégorie'] = categorie
                            lignes.append(transaction)

        df = pd.DataFrame(lignes)
        df.set_index("DATE D'OPÉRATION", inplace=True)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df

    def TransformerDataframe(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Transforme un DataFrame de large à long, réinitialisant l'index et utilisant melt pour
        convertir le DataFrame. Réorganise les colonnes pour obtenir 'Date', 'Type', et 'Montant'.

        Returns:
            pd.DataFrame: DataFrame transformé.
        """
        assert pd.api.types.is_datetime64_any_dtype(df.index), "L'index doit être de type datetime."
        assert not df.empty, "Le DataFrame est vide"

        df = self.SelectionnerDates(df, freq)

        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Date'}, inplace=True)
        # df_long = df.melt(id_vars='Date', var_name='Type', value_name='Montant')
        # df_long = df_long[['Date', 'Type', 'Montant']]
        return df
    

    def AfficherGraphiqueHistogrammeSuperpose(self, freq: str) -> None:
        """
        Affiche un histogramme superposé des montants pour toutes les colonnes du DataFrame à une fréquence donnée, 
        excepté la colonne 'Date'.

        Cette fonction utilise les données du DataFrame de patrimoine, applique la transformation en fonction de la 
        fréquence spécifiée, filtre les lignes contenant des valeurs manquantes, puis crée un histogramme superposé 
        des montants pour toutes les colonnes à l'aide de Plotly Express.

        Args:
            freq (str): Fréquence des dates à utiliser pour transformer le DataFrame. Peut être 'D' (jours), 'M' (mois), 'Y' (années), etc.

        Returns:
            None
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"self.patrimoine doit être un DataFrame, mais c'est {type(self.patrimoine).__name__}."
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], f"La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q', mais c'est '{freq}'."
        
        df = self.patrimoine.copy()
        
        if "Bourse" in df.columns:
            # Récupérer la première date de la colonne Bourse
            if freq in ["M", "Q"]:
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y-%m")
            elif freq == "Y":
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y")
            else:
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y-%m")

        df = self.ReorganiserColonnesParValeurDerniereLigne(df)

        df = self.TransformerDataframe(df, freq)

        assert 'Date' in df.columns, "La colonne 'Date' est manquante dans le DataFrame."
        df['Date'] = pd.to_datetime(df['Date'])
        # Sélectionner toutes les colonnes sauf 'Date' pour l'histogramme
        colonnes = [col for col in df.columns if col != 'Date']
        assert len(colonnes) > 0, "Aucune colonne à afficher hormis la colonne 'Date'."
        
        # Remettre la colonne 'Bourse' après avoir manipulé les autres colonnes
        if "Bourse" in df.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            df.loc[df['Date'] < firstDateBourse, 'Bourse'] = 0

        # Filtrer les lignes où les colonnes sélectionnées n'ont pas de NaN
        dfiltered = df.dropna(subset=colonnes)

        # Créer un histogramme superposé avec Plotly Express pour toutes les colonnes
        fig = px.bar(
            dfiltered,
            x='Date',
            y=colonnes,
            labels={'value': 'Montant', 'variable': 'Type de Compte'},
            title='Evolution des différents Comptes',
            height=900
        )

        # Afficher le graphique
        fig.show()

    def AfficherGraphiqueCoteACote(self, freq: str) -> None:
        """
        Affiche un graphique en barres côte à côte pour les montants de chaque colonne du DataFrame 
        sur une période déterminée par la fréquence spécifiée.

        La fonction sélectionne les données en fonction de la fréquence, filtre les lignes sans valeurs manquantes, 
        puis affiche un graphique avec des barres pour chaque colonne du DataFrame. Les barres sont colorées et affichées 
        côte à côte avec une personnalisation de l'espacement.

        Args:
            freq (str): Fréquence des dates à utiliser pour filtrer le DataFrame. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.
        
        Returns:
            None
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"self.patrimoine doit être un DataFrame, mais c'est {type(self.patrimoine).__name__}."
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], f"La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q', mais c'est '{freq}'."
        
        df = self.patrimoine.copy()
        if "Bourse" in df.columns:
            # Récupérer la première date de la colonne Bourse
            if freq in ["M", "Q"]:
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y-%m")
            elif freq == "Y":
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y")
            else:
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y-%m")

        df = self.SelectionnerDates(df, freq)
        # Remettre la colonne 'Bourse' après avoir manipulé les autres colonnes
        if "Bourse" in df.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            df.loc[df.index < firstDateBourse, 'Bourse'] = 0

        df = df.dropna()

        colors = ['rgba(99, 110, 250, 1)', 'rgba(239, 85, 59, 1)', 'rgba(0, 204, 150, 1)', 
                'rgba(171, 99, 250, 1)', 'rgba(255, 161, 90, 1)', 'rgba(25, 211, 243, 1)']

        fig = go.Figure()

        for i, nameColumn in enumerate(df.columns):
            # Ajouter les barres pour chaque colonne
            fig.add_trace(go.Bar(x=df.index, y=df[nameColumn], name=nameColumn, marker_color=colors[i % len(colors)]))

        # Mise en forme du graphique
        fig.update_layout(
            title='Evolution des différents Comptes',
            xaxis_tickfont_size=14,
            yaxis=dict(
                title='Montant (€)',
                titlefont_size=16,
                tickfont_size=14,
            ),
            barmode='group',
            bargap=-0,  # Espace entre les groupes de barres
            bargroupgap=0.1  # Espace entre les barres du même groupe
        )

        # Afficher le graphique
        fig.show()
    
    def AfficheGraphiqueInteractif(self, freq="D") -> None:
        """
        Affiche un graphique interactif avec Plotly montrant l'évolution du patrimoine.
        Un menu déroulant permet de basculer entre les différentes colonnes de patrimoine.
        Les pourcentages de variation sont affichés sous le graphique principal avec une mise en forme colorée.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({type(self.patrimoine).__name__})"
        assert not self.patrimoine.empty, f"La variable patrimoine doit contenir des colonnes."

        df = self.patrimoine.copy()

        if "Bourse" in df.columns:
            # Récupérer la première date de la colonne Bourse
            if freq in ["M", "Q"]:
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y-%m")
            elif freq == "Y":
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y")
            else:
                firstDateBourse = df['Bourse'].first_valid_index().strftime("%Y-%m")
        
        # Remplir les valeurs manquantes pour toutes les colonnes sauf 'Bourse'
        colsSaufBourse = df.columns.difference(['Bourse'])
        df[colsSaufBourse] = df[colsSaufBourse].fillna(method="ffill").fillna(method="bfill")
        
        # Remettre la colonne 'Bourse' après avoir manipulé les autres colonnes
        if "Bourse" in df.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            df.loc[df.index < firstDateBourse, 'Bourse'] = 0
        
        df.sort_index(inplace=True)
        df["Patrimoine"] = df.sum(axis=1)
        df = self.ReorganiserColonnesParValeurDerniereLigne(df)
        dfPourCalulerLePourcentage = df.copy()
        df = self.SelectionnerDates(df, freq)

        colors = ['rgba(99, 110, 250, 1)', 'rgba(239, 85, 59, 1)', 'rgba(0, 204, 150, 1)', 'rgba(171, 99, 250, 1)', 'rgba(255, 161, 90, 1)', 'rgba(25, 211, 243, 1)']
        
        # Créer la figure
        fig = go.Figure()
        buttons = []

        # Ajouter les traces pour chaque colonne
        for i, livret in enumerate(df.columns):
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[livret],
                mode='lines',
                name=livret,
                line=dict(color=colors[i % len(colors)], width=2),  # Utiliser les couleurs définies
                visible=(i == 0),
                showlegend=False
            ))

            # Définir la ligne de base pour le remplissage
            minValue = df[livret].min()
            baseline = minValue - 250
            if baseline < 0:
                baseline = 0
            
            # Ajouter la ligne de base (remplissage en dessous)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[baseline] * len(df),
                mode='lines',
                line=dict(color='rgba(0, 0, 0, 0)', width=0),  # Ligne invisible
                fill='tonexty',  # Remplir entre cette ligne et la courbe du patrimoine
                fillcolor=colors[i % len(colors)].replace('1)', '0.2)'),
                showlegend=False,
                visible=(i == 0)
            ))

            # Gérer la visibilité pour les courbes et les lignes de base
            visibility = [False] * (2 * len(df.columns))  # 2 traces (courbe et ligne de base) par livret
            visibility[i * 2] = True  # Affiche la courbe correspondante
            visibility[i * 2 + 1] = True  # Affiche la ligne de base correspondante

            # Ajout des annotations spécifiques à chaque livret lors de la sélection
            buttons.append(dict(
                label=livret,
                method='update',
                args=[{'visible': visibility},
                    {'title': f'Evolution du {livret}',
                    'annotations': self.ObtenirAnnotations(dfPourCalulerLePourcentage, livret)}]
            ))

        # Ajout des boutons de plage de date
        dateButtons = [
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=5, label="5Y", step="year", stepmode="backward"),
            dict(count=10, label="10Y", step="year", stepmode="backward"),
            dict(step="all", label="Max")
        ]

        # Mise en forme du graphique
        fig.update_layout(
            updatemenus=[
                dict(
                    type='dropdown',
                    buttons=buttons,
                    direction='down',
                    showactive=True,
                )
            ],
            xaxis=dict(
                rangeselector=dict(
                    buttons=dateButtons,
                    x=0,  # Positionnement des boutons à gauche
                    xanchor='left',
                    y=1,  # Sous le titre
                    yanchor='bottom'
                ),
                title='Date',
                type='date'
            ),
            yaxis=dict(
                title='Prix',
                automargin=True,  # Ajoute une marge automatique si nécessaire
                autorange=True,   # Permet l'adaptation dynamique de l'axe Y selon la sélection de date
                tickprefix="€",
            ),
            template='plotly_white',
            height=900,
            title=f'Evolution du {df.columns[0]}',
            barmode='group',
            annotations=self.ObtenirAnnotations(dfPourCalulerLePourcentage, df.columns[0]),
            margin=dict(b=150)
        )

        fig.show()



    @staticmethod
    def DetermineColor(value) -> tuple:
        """
        Détermine la couleur à utiliser en fonction de la valeur donnée. 
        Si la valeur est positive ou nulle, la couleur sera verte; 
        si elle est négative, la couleur sera rouge.

        Args:
            value (float): La valeur pour laquelle la couleur doit être déterminée. Peut être positive, négative, ou nulle.

        Returns:
            tuple: Une paire de chaînes représentant la couleur principale et une version transparente de celle-ci. 
            Pour une valeur positive ou nulle, cela retourne ('lightgreen', 'rgba(144, 238, 144, 0.3)'). 
            Pour une valeur négative, cela retourne ('lightcoral', 'rgba(255, 99, 71, 0.3)').
        """
        if value >= 0:
            return 'lightgreen', 'rgba(144, 238, 144, 0.3)'
        else:
            return 'lightcoral', 'rgba(255, 99, 71, 0.3)'
        
    def ObtenirAnnotations(self, df: pd.DataFrame, livret: str) -> list:
        """
        Génère des annotations pour un graphique Plotly basées sur les pourcentages de variation moyenne mensuelle et annuelle
        pour une colonne spécifique d'un DataFrame. Les annotations indiquent les évolutions en pourcentage avec des couleurs 
        différentes selon la tendance (positive ou négative) et s'adaptent dynamiquement à la taille du texte.

        Args:
            df (pd.DataFrame): DataFrame contenant les données de patrimoine pour calculer les pourcentages d'évolution.
            livret (str): Nom de la colonne du DataFrame pour laquelle les pourcentages de variation doivent être calculés.

        Returns:
            list: Liste de dictionnaires représentant les annotations pour Plotly, avec les pourcentages de variation
                et des bordures colorées en fonction de la tendance (positif = vert, négatif = rouge).
        """
        assert isinstance(df, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({type(df).__name__})"
        assert isinstance(livret, str), "Le paramètre livret doit être une chaîne de caractères."
        assert livret in df.columns, f"La colonne '{livret}' n'existe pas dans le DataFrame."

        # Pas d'annotations pour "Compte Courant" ou "Bourse"
        if livret in ["Compte Courant", "Bourse"]:
            return []

        # Calculer les pourcentages d'évolution moyenne
        pourcentages = self.CalculEvolutionMoyenneParMois(df[livret])
        annotations = []
        x = 0.472  # Position initiale des annotations sur l'axe x

        # Parcourir les lettres (W, M, Y) et leurs pourcentages respectifs
        for lettre, pourcentage in pourcentages.items():
            # Déterminer la couleur en fonction de la tendance (positive ou négative)
            color, rgba = self.DetermineColor(pourcentage)

            # Ajuster la taille de la police et les marges en fonction de la longueur du texte
            texte = f"{lettre}: {pourcentage:.2f}%"
            tailleTexte = max(13, 12 - len(texte) // 5)  # Ajustement de la taille de police selon la longueur
            annotations.append(
                dict(
                    xref='paper', yref='paper',
                    x=x, y=-0.15,
                    text=texte,
                    showarrow=False,
                    font=dict(size=tailleTexte),  # Taille de police dynamique
                    bordercolor=color,
                    borderwidth=2,
                    bgcolor=rgba,
                    opacity=1,
                    # Marges supplémentaires pour améliorer l'apparence
                    ax=0,
                    ay=0,
                    xanchor="center",  # Centrer le texte
                    yanchor="middle",  # Centrer verticalement
                    align="center",    # Aligner le texte au centre
                )
            )
            x += 0.06  # Espace ajusté dynamiquement entre les annotations

        return annotations

    def CalculEvolutionMoyenneParMois(self, patrimoine) -> dict:
        """
        Calcule l'évolution moyenne mensuelle ou annuelle pour la colonne 'Patrimoine' d'une Série.

        Args:
            patrimoine (pd.Series): Série de données avec des dates comme index et des valeurs de patrimoine.

        Returns:
            dict: Dictionnaire contenant deux DataFrames, 'Mois' pour les données mensuelles et 'Année' pour les données annuelles.
        """
        # Vérifier que le paramètre est une Série avec un index de type datetime
        assert isinstance(patrimoine, pd.Series), "Le paramètre patrimoine doit être une pd.Series."
        assert pd.api.types.is_datetime64_any_dtype(patrimoine.index), "L'index de la Série doit être de type datetime."

        # Dictionnaire pour stocker les résultats
        resultats = {}

        for freq in ["M", "Y"]:
            # Resampler les données par fréquence et calculer les premiers et derniers jours
            dfPlage = patrimoine.resample(freq).agg(['first', 'last'])
            # Calculer l'évolution moyenne pour chaque période
            dfPlage['EvolutionMoyenne'] = (dfPlage['last'] - dfPlage['first']) / dfPlage['first'] * 100

            resultats[freq] = round(dfPlage["EvolutionMoyenne"].sum(axis=0) / len(dfPlage["EvolutionMoyenne"]), 2)

        return resultats

    @staticmethod
    def ReorganiserColonnesParValeurDerniereLigne(df: pd.DataFrame) -> pd.DataFrame:
        """
        Réorganise les colonnes du DataFrame en fonction des valeurs de la dernière ligne,
        en mettant la colonne avec la valeur la plus élevée au début et celle avec la valeur la plus basse à la fin.

        Args:
            df (pd.DataFrame): DataFrame contenant les données.

        Returns:
            pd.DataFrame: DataFrame avec les colonnes réorganisées.
        """
        assert isinstance(df, pd.DataFrame), f"Le paramètre 'df' doit être un DataFrame, mais c'est {type(df).__name__}."

        # Obtenir les valeurs de la dernière ligne
        valeurs_derniere_ligne = df.iloc[-1]
        # Trier les colonnes en fonction des valeurs de la dernière ligne
        colonnes_reorganisees = valeurs_derniere_ligne.sort_values(ascending=False).index
        # Réorganiser les colonnes du DataFrame
        return df[colonnes_reorganisees]
