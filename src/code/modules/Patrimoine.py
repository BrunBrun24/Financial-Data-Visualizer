import os
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import plotly.figure_factory as ff


class Patrimoine:
    """
    La classe `Patrimoine` est conçue pour gérer et analyser l'évolution du patrimoine financier à partir de transactions.
    Elle permet de charger des données depuis des fichiers JSON, de calculer l'évolution du patrimoine quotidiennement,
    de transformer les données en différents formats, et de visualiser les résultats à l'aide de graphiques interactifs.
    """

    def __init__(self):
        """Initialise le patrimoine avec des montants fixes et un DataFrame vide pour enregistrer les transactions"""
        
        argentCompteCourantInitial = 0
        argentLivretAInitial = 3816.42  # Argent initial (2014-10-27)
        self.patrimoine = pd.DataFrame(dtype=float)

        self.EvolutionDuPatrimoine("Compte Courant", argentCompteCourantInitial, "Bilan/Archives/Compte Chèques")
        self.EvolutionDuPatrimoine("Livret A", argentLivretAInitial, "Bilan/Archives/livret A")
        self.EvolutionDuPatrimoineBourse("Bilan/Archives/Bourse/Portefeuille.json")



    #################### BOURSE ####################
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

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, list), "Le contenu du fichier JSON doit être une liste d'objets (dict)."

        return pd.DataFrame(data)

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
        assert isinstance(argent, (int, float)), f"La variable argent doit être un nombre: ({type(argent)})"
        assert isinstance(directory, str), f"La variable directory doit être une chaîne de caractères: ({type(directory)})"
        assert os.path.exists(directory), f"Le dossier spécifié n'existe pas: {directory}"

        for fichier in os.listdir(directory):
            if fichier.endswith(".json"):
                with open(os.path.join(directory, fichier), 'r', encoding="UTF-8") as f:
                    data = json.load(f)
                    for categorie, operations in data.items():
                        for operation in operations:
                            argent += operation["MONTANT"]
        return argent
    ################################################



    #################### Livret, Compte, ####################
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
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être un DataFrame: ({type(self.patrimoine)})"
        assert isinstance(nomDuCompte, str), f"La variable nomDuCompte doit être une chaîne de caractères: ({type(nomDuCompte)})"
        assert isinstance(argent, (int, float)), f"La variable argent doit être un nombre: ({type(argent)})"
        assert isinstance(dossierCompte, str), f"La variable dossierCompte doit être une chaîne de caractères: ({type(dossierCompte)})"
        assert os.path.exists(dossierCompte), f"Le dossier spécifié n'existe pas: {dossierCompte}"

        if nomDuCompte not in self.patrimoine.columns:
            self.patrimoine[nomDuCompte] = pd.Series(dtype=float)

        transactions = self.TransformerDossierJsonEnDataFrame(dossierCompte)

        assert pd.api.types.is_datetime64_any_dtype(transactions.index), "L'index doit être de type datetime."
        assert "MONTANT" in transactions, "La colonne 'MONTANT' est manquante dans les transactions."

        for date, row in transactions.iterrows():
            argent += row["MONTANT"]
            self.patrimoine.at[pd.to_datetime(date), nomDuCompte] = argent

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
        assert isinstance(cheminDossier, str), f"Le cheminDossier doit être une chaîne de caractères: ({type(cheminDossier)})"
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
    #########################################################



    #################### GRAPHIQUES ####################
    def PlotlyInteractive(self, nomDossier: str, nomFichier: str):
        """
        Crée un graphique interactif utilisant Plotly pour visualiser différents aspects de l'évolution du patrimoine en l'enregistrant dans un fichier html.

        Args:
            nomDossier (str): Chemin vers le dossier où sauvegarder le fichier de sortie.
            nomFichier (str): Nom du fichier de sortie (doit avoir une extension .html).
        """
        assert isinstance(nomDossier, str), "nomDossier doit être une chaîne de caractères"
        assert os.path.exists(nomDossier), f"Le chemin '{nomDossier}' n'existe pas"

        assert isinstance(nomFichier, str), f"nomFichier doit être une chaîne de caractères: ({nomFichier})"
        assert nomFichier.endswith('.html'), f"Le fichier {nomFichier} n'a pas l'extension .html."

        patrimoineGraphique = []

        # Ajout des graphiques
        patrimoineGraphique.append(self.GraphiqueLineaireEvolutionPatrimoine())
        patrimoineGraphique.append(self.GraphiqueLineaireAera())
        patrimoineGraphique.append(self.GraphiqueHistogrammeSuperpose("M"))
        patrimoineGraphique.append(self.GraphiqueDiagrammeCirculaire())
        patrimoineGraphique.append(self.GraphiqueTreemap())
        
        patrimoineGraphique.append(self.GraphiqueCorrelationMap())

        # Sauvegarde des graphiques dans un fichier HTML
        self.SaveInFile(patrimoineGraphique, (nomDossier + nomFichier))

    ########## Graphique en Histogramme ##########
    def GraphiqueHistogrammeSuperpose(self, freq: str):
        """
        Affiche un histogramme superposé des montants pour toutes les colonnes du DataFrame à une fréquence donnée,
        excepté la colonne 'Date'.

        Cette fonction utilise les données du DataFrame de patrimoine, applique la transformation en fonction de la
        fréquence spécifiée, filtre les lignes contenant des valeurs manquantes, puis crée un histogramme superposé
        des montants pour toutes les colonnes à l'aide de Plotly Express.

        Args:
            freq (str): Fréquence des dates à utiliser pour transformer le DataFrame. Peut être 'D' (jours), 'M' (mois), 'Y' (années), etc.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"self.patrimoine doit être un DataFrame: {type(self.patrimoine)}."
        assert freq in ['M', 'Y'], f"La fréquence doit être 'M' ou 'Y': '{freq}'."

        df = self.patrimoine.copy()
        df = self.ReorganiserColonnesParValeurDerniereLigne(df)
        df = self.TransformerDataframe(df, freq)

        assert 'Date' in df.columns, "La colonne 'Date' est manquante dans le DataFrame."
        df['Date'] = pd.to_datetime(df['Date'])
        # Sélectionner toutes les colonnes sauf 'Date' pour l'histogramme
        colonnes = [col for col in df.columns if col != 'Date']
        assert len(colonnes) > 0, "Aucune colonne à afficher hormis la colonne 'Date'."

        # Filtrer les lignes où les colonnes sélectionnées n'ont pas de NaN
        dfiltered = df.dropna(subset=colonnes)

        # Trier les colonnes par la valeur de la dernière ligne de manière décroissante
        colonnes = sorted(colonnes, key=lambda col: df[col].iloc[-1], reverse=True)

        # Créer un histogramme superposé avec Plotly Express pour toutes les colonnes
        fig = px.bar(
            dfiltered,
            x='Date',
            y=colonnes,
            labels={'value': 'Montant', 'variable': 'Type de Compte'},
            title="Évolution du patrimoine par type de compte (montant en fin d'année)"
        )

        fig.update_layout(
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig

    def GraphiqueHistogrammeCoteACote(self, freq: str):
        """
        Affiche un graphique en barres côte à côte pour les montants de chaque colonne du DataFrame
        sur une période déterminée par la fréquence spécifiée.

        La fonction sélectionne les données en fonction de la fréquence, filtre les lignes sans valeurs manquantes,
        puis affiche un graphique avec des barres pour chaque colonne du DataFrame. Les barres sont colorées et affichées
        côte à côte avec une personnalisation de l'espacement.

        Args:
            freq (str): Fréquence des dates à utiliser pour filtrer le DataFrame. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"self.patrimoine doit être un DataFrame: {type(self.patrimoine)}."
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], f"La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q': '{freq}'."

        df = self.patrimoine.copy()
        df = self.SelectionnerDates(df, freq)
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
            bargroupgap=0.1,  # Espace entre les barres du même groupe
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig
    ##############################################

    ########## Graphique Linéaire ##########
    def GraphiqueLineaireEvolutionPatrimoine(self, freq="D"):
        """
        Affiche un graphique interactif avec Plotly montrant l'évolution du patrimoine.
        Un menu déroulant permet de basculer entre les différentes colonnes de patrimoine.
        Les pourcentages de variation sont affichés sous le graphique principal avec une mise en forme colorée.

        Args:
            freq (str): Fréquence de sélection des données (ex: 'D', 'M', 'Y'). Par défaut, 'D' pour quotidien.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({type(self.patrimoine)})"
        assert not self.patrimoine.empty, f"La variable patrimoine doit contenir des colonnes."

        df = self.patrimoine.copy()

        # Remplir les valeurs manquantes pour toutes les colonnes sauf certaines d'entre elles
        colsSauf = df.columns.difference(['Bourse'])
        df[colsSauf] = df[colsSauf].ffill()

        df.sort_index(inplace=True)
        df["Patrimoine"] = df.sum(axis=1)
        dfPourCalulerLePourcentage = df.copy()
        df = self.SelectionnerDates(df, freq)
        
        # On enlève le patrimoine pour pouvoir le remettre avec les données actuelles
        del df["Patrimoine"]
        df["Patrimoine"] = df.sum(axis=1)
        df = self.ReorganiserColonnesParValeurDerniereLigne(df)

        colors = ['rgba(99, 110, 250, 1)', 'rgba(239, 85, 59, 1)', 'rgba(0, 204, 150, 1)', 
                'rgba(171, 99, 250, 1)', 'rgba(255, 161, 90, 1)', 'rgba(25, 211, 243, 1)']

        # Créer la figure
        fig = go.Figure()
        buttons = []

        # Ajouter les traces pour chaque colonne et calculer la plage de dates non nulles
        dateRanges = {}
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

            # Calculer les dates non nulles
            datesNonNull = df[df[livret] > 0].index
            if not datesNonNull.empty:
                dateRanges[livret] = (datesNonNull.min(), datesNonNull.max())
            else:
                dateRanges[livret] = (df.index.min(), df.index.max())  # Si toutes les valeurs sont nulles

            # Gérer la visibilité pour les courbes et les lignes de base
            visibility = [False] * (2 * len(df.columns))  # 2 traces (courbe et ligne de base) par livret
            visibility[i * 2] = True  # Affiche la courbe correspondante
            visibility[i * 2 + 1] = True  # Affiche la ligne de base correspondante

            # Ajout des annotations spécifiques à chaque livret lors de la sélection
            buttons.append(dict(
                label=livret,
                method='update',
                args=[
                    {'visible': visibility},
                    {
                        'title': f'Evolution du {livret}',
                        'annotations': self.ObtenirAnnotations(dfPourCalulerLePourcentage, livret),
                        'xaxis.range': dateRanges[livret]  # Mise à jour de la plage de dates
                    }
                ]
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
            title=f'Evolution du {df.columns[0]}',
            barmode='group',
            annotations=self.ObtenirAnnotations(dfPourCalulerLePourcentage, df.columns[0]),
            margin=dict(b=150),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig

    def GraphiqueLineaireAera(self, freq="D"):
        """
        Affiche un graphique empilé montrant l'évolution du patrimoine sous forme d'aires empilées.
        Chaque compte est empilé en dessous, en commençant par le compte avec le plus d'argent et en descendant.
        Les couleurs sont fixes et associées correctement à chaque livret, sans afficher la courbe du patrimoine total.

        Args:
            freq (str): Fréquence de sélection des données (ex: 'D', 'M', 'Y'). Par défaut, 'D' pour quotidien.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({type(self.patrimoine)})"
        assert not self.patrimoine.empty, f"La variable patrimoine doit contenir des colonnes."

        df = self.patrimoine.copy()

        # Remplir les valeurs manquantes pour les autres colonnes
        df.ffill(inplace=True)
        df.bfill(inplace=True)

        # Trier les colonnes par valeur finale (ordre décroissant pour l'empilement correct)
        colonnesTriees = df.iloc[-1].sort_values(ascending=False).index.tolist()
        df = df[colonnesTriees]

        # Sélectionner les données selon la fréquence demandée (quotidienne, mensuelle, annuelle...)
        df = self.SelectionnerDates(df, freq)
        df = self.SupprimerValeursRepeteesSpecifiques(df)

        # Définir les couleurs pour chaque colonne avec une transparence ajustée
        colors = [
            'rgba(99, 110, 250, 0.2)',  # Bleu clair
            'rgba(239, 85, 59, 0.2)',   # Rouge clair
            'rgba(0, 204, 150, 0.2)',   # Vert clair
            'rgba(171, 99, 250, 0.2)',  # Violet clair
            'rgba(255, 161, 90, 0.2)',  # Orange clair
            'rgba(25, 211, 243, 0.2)'   # Cyan clair
        ]

        # Tracer le graphique en aires empilées avec Plotly Express
        fig = px.area(
            df,
            x=df.index,
            y=df.columns,
            title="Evolution du patrimoine",
            labels={"value": "Prix (€)", "variable": "Livret", "Date": "Date"},
            template="plotly_white",
            color_discrete_sequence=colors  # Appliquer les couleurs définies
        )

        # Mettre à jour la mise en page
        fig.update_layout(
            xaxis_title=None,
            yaxis=dict(title='Prix (€)', tickprefix="€"),
            margin=dict(b=150),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig
    ########################################

    ########## Graphique Circulaire ##########
    def GraphiqueDiagrammeCirculaire(self) -> go.Figure:
        """
        Génère un diagramme circulaire interactif représentant la répartition des valeurs des actions pour le patrimoine,
        basé sur les données les plus récentes disponibles dans le DataFrame.
        
        Le diagramme circulaire est créé à partir des valeurs les plus récentes de chaque compte, et il est stylisé avec
        un fond sombre et des textes en blanc. La figure résultante est interactive et permet de visualiser les proportions
        des différentes valeurs des comptes.

        Returns:
            go.Figure: Une figure Plotly contenant un diagramme circulaire interactif représentant la répartition des valeurs des comptes.
        """

        patrimoine = self.patrimoine.copy()
        patrimoine.ffill(inplace=True)

        # Créer une figure vide
        fig = go.Figure()

        # Sélection des données les plus récentes
        derniere_valeur = patrimoine.iloc[-1]
        assert derniere_valeur.notna().all(), f"Le DataFrame pour '{patrimoine}' contient des valeurs manquantes pour la ligne la plus récente."

        # Créer un DataFrame pour le diagramme circulaire
        pie_df = pd.DataFrame({
            'Compte': derniere_valeur.index,
            'Valeur': derniere_valeur.values
        })

        # Ajouter le diagramme circulaire pour ce portefeuille
        fig.add_trace(
            go.Pie(
                labels=pie_df['Compte'],
                values=pie_df['Valeur'],
                name="Patrimoine",
                textinfo='percent+label',
                insidetextfont=dict(color='white')  # Texte en blanc
            )
        )

        fig.update_layout(
            margin=dict(l=30, r=30, t=50, b=50),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    ##########################################

    ########## Graphique Treemap ##########
    def GraphiqueTreemap(self) -> go.Figure:
        """
        Génère un treemap interactif représentant la répartition des valeurs des actions pour le patrimoine,
        basé sur les données les plus récentes disponibles dans le DataFrame.

        Le treemap est créé à partir des valeurs les plus récentes de chaque compte, et il est stylisé avec
        un fond sombre et des textes en blanc. La figure résultante est interactive et permet de visualiser les proportions
        des différentes valeurs des comptes.

        Returns:
            go.Figure: Une figure Plotly contenant un treemap interactif représentant la répartition des valeurs des comptes.
        """

        patrimoine = self.patrimoine.copy()
        patrimoine.ffill(inplace=True)

        # Sélection des données les plus récentes
        derniere_valeur = patrimoine.iloc[-1]
        assert derniere_valeur.notna().all(), f"Le DataFrame pour '{patrimoine}' contient des valeurs manquantes pour la ligne la plus récente."

        valeurTotale = derniere_valeur.sum()
        
        # Créer un DataFrame pour le treemap
        treemapDf = pd.DataFrame({
            'Compte': derniere_valeur.index,
            'Valeur': derniere_valeur.values,
            'Pourcentage': (derniere_valeur / valeurTotale * 100).round(2)  # Calculer le pourcentage avec 2 décimales
        })

        # Ajouter une colonne texte avec des informations formatées
        treemapDf['text'] = treemapDf.apply(
            lambda row: f"{row['Compte']}<br>Répartition: {row['Pourcentage']:.2f}% <br>Valeur: {row['Valeur']:.2f}", axis=1
        )

        # Créer une figure Treemap
        fig = go.Figure(go.Treemap(
            labels=treemapDf['Compte'],
            parents=[""] * len(treemapDf),  # Pas de parents pour un seul niveau
            values=treemapDf['Valeur'],
            text=treemapDf['text'],
            textinfo='text',
            insidetextfont=dict(color='white'),  # Texte en blanc
            marker=dict(
                line=dict(color='white', width=1)  # Ligne de séparation blanche entre les sections
            )
        ))

        fig.update_layout(
            margin=dict(l=30, r=30, t=50, b=50),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
            title_text='Répartition des valeurs des comptes'
        )

        return fig
    #######################################

    def GraphiqueCorrelationMap(self) -> go.Figure:
        """
        Crée et affiche une carte de corrélation interactive pour un DataFrame donné avec Plotly.
        Affiche uniquement la moitié inférieure de la carte de corrélation avec les annotations.

        Args:
            df (pd.DataFrame): DataFrame contenant les données numériques des actions.
                            Les colonnes représentent les noms des actions.

        Returns:
            go.Figure: Le graphique Plotly avec la carte des corrélations.
        """

        # Calculer les variations en pourcentage
        df = self.patrimoine.copy()
        df = df.pct_change()

        # Calcul de la matrice de corrélation
        correlationMap = df.corr()

        # Créer un masque pour la moitié supérieure
        mask = np.triu(np.ones_like(correlationMap, dtype=bool))

        # Appliquer le masque à la matrice de corrélation et définir les valeurs masquées sur une valeur arbitraire hors de la plage (-2)
        correlationMasked = correlationMap.where(~mask, other=-2)

        # Créer les annotations (affichage des valeurs) en remplaçant les valeurs masquées par une chaîne vide
        annotations = np.round(correlationMap, 2).astype(str)
        annotations = np.where(mask, "", annotations)

        # Définir une palette de couleurs incluant le noir pour les valeurs masquées
        colorscale = [
            [0.0, "#241f1e"],
            [0.01, "blue"],
            [0.6, "blue"],
            [1.0, "red"]
        ]

        # Création de la carte de corrélation avec Plotly
        fig = ff.create_annotated_heatmap(
            z=correlationMasked.values,
            x=correlationMap.columns.tolist(),
            y=correlationMap.index.tolist(),
            annotation_text=annotations,
            colorscale=colorscale,
            zmin=-1,
            zmax=1,
            showscale=True,
            font_colors=["white"]
        )

        # Calcul de la corrélation moyenne
        averageCorr = np.mean(np.abs(correlationMap.values[np.triu_indices_from(correlationMap, k=1)]))

        # Ajouter la corrélation moyenne comme annotation de texte
        fig.add_annotation(
            text=f"Corrélation moyenne : {averageCorr:.2f}",
            xref="paper", yref="paper",
            x=1.05, y=1.05,
            showarrow=False,
            font=dict(size=12, color="black", family="Arial")
        )

        # Mise à jour du titre de la carte
        fig.update_layout(
            title="Carte des Corrélations",
            title_x=0.5,
            title_font=dict(size=15, family="Arial", color="black")
        )

        return fig

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

    ########## ANNEXES ##########
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
        assert isinstance(df, pd.DataFrame), f"Le paramètre 'df' doit être un DataFrame: {type(df)}."

        # Obtenir les valeurs de la dernière ligne
        valeursDerniereLigne = df.iloc[-1]
        # Trier les colonnes en fonction des valeurs de la dernière ligne
        colonnesReorganisees = valeursDerniereLigne.sort_values(ascending=False).index
        # Réorganiser les colonnes du DataFrame
        return df[colonnesReorganisees]
    
    @staticmethod
    def SupprimerValeursRepeteesSpecifiques(df: pd.DataFrame) -> pd.DataFrame:
        """
        Supprime les valeurs répétées au début de certaines colonnes d'un DataFrame.
        - Pour 'Bourse', remplace toutes les valeurs répétées au début par NaN.

        Args:
            df (pd.DataFrame): Le DataFrame à traiter.

        Returns:
            pd.DataFrame: Le DataFrame modifié avec les premières valeurs répétées remplacées par NaN.
        """
        dfModifie = df.copy()

        # Traiter la colonne 'Bourse'
        column = ['Bourse', "Compte Courant"]
        for col in column:
            if col in dfModifie.columns:
                # Trouver les valeurs répétées au début
                dfBourse = dfModifie[col]
                firstDiff = dfBourse.ne(dfBourse.shift()).cumsum()
                dfModifie[col] = dfBourse.where(firstDiff != 1, 0)

        return dfModifie
    
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
        assert isinstance(df, pd.DataFrame), f"La variable patrimoine doit être un DataFrame: ({type(df)})"
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
            if pourcentage >= 0:
                color, rgba = 'lightgreen', 'rgba(144, 238, 144, 0.3)'
            else:
                color, rgba = 'lightcoral', 'rgba(255, 99, 71, 0.3)'

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
    
    @staticmethod
    def CalculEvolutionMoyenneParMois(patrimoine: pd.Series) -> dict:
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
            freq += "E"
            # Resampler les données par fréquence et calculer les premiers et derniers jours
            dfPlage = patrimoine.resample(freq).agg(['first', 'last'])
            # Calculer l'évolution moyenne pour chaque période
            dfPlage['EvolutionMoyenne'] = (dfPlage['last'] - dfPlage['first']) / dfPlage['first'] * 100

            resultats[freq] = round(dfPlage["EvolutionMoyenne"].sum(axis=0) / len(dfPlage["EvolutionMoyenne"]), 2)

        return resultats
    
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
        assert isinstance(df, pd.DataFrame), f"La variable df doit être une DataFrame: ({type(df)})"
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], "La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q'."

        # Convertir l'index en datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        if "Bourse" in df.columns:
            firstDateBourse = df['Bourse'].first_valid_index()
        if "Compte Courant" in df.columns:
            firstDateCompteCourant = df['Compte Courant'].first_valid_index()

        # Déterminer les dates à inclure selon la fréquence choisie
        if freq == 'D':
            periodRange = pd.date_range(df.index.min(), df.index.max(), freq='D')
        elif freq == 'M':
            periodRange = pd.date_range(df.index.min().replace(day=1), df.index.max().replace(day=1), freq='MS')
        elif freq == 'Y':
            periodRange = pd.date_range(df.index.min().replace(month=1, day=1), df.index.max().replace(month=1, day=1), freq='YS')
        elif freq == 'W':
            periodRange = pd.date_range(df.index.min() - pd.DateOffset(days=df.index.min().weekday()),
                                        df.index.max() + pd.DateOffset(days=(6 - df.index.max().weekday())), freq='W-SUN')
        elif freq == 'Q':
            periodRange = pd.date_range(df.index.min() - pd.DateOffset(months=(df.index.min().month - 1) % 3),
                                        df.index.max() + pd.DateOffset(months=2 - (df.index.max().month - 1) % 3), freq='Q')

        combined_dates = pd.Index(periodRange).union([df.index.max()])
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

        # if freq == 'Y':
        #     newDf.index = [i.strftime('%Y') for i in newDf.index]

        if "Bourse" in newDf.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            newDf.loc[newDf.index < firstDateBourse, 'Bourse'] = 0
        if "Compte Courant" in newDf.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            newDf.loc[newDf.index < firstDateCompteCourant, 'Compte Courant'] = 0

        return newDf

    def TransformerDataframe(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Transforme un DataFrame de large à long, réinitialisant l'index et utilisant melt pour
        convertir le DataFrame. Réorganise les colonnes pour obtenir 'Date', 'Type', et 'Montant'.

        Args:
            df (pd.DataFrame): DataFrame avec des dates comme index et plusieurs colonnes de valeurs.
            freq (str): Fréquence des dates à ajouter. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.

        Returns:
            pd.DataFrame: DataFrame transformé.
        """
        assert pd.api.types.is_datetime64_any_dtype(df.index), "L'index doit être de type datetime."
        assert not df.empty, "Le DataFrame est vide"
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], "La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q'."

        df = self.SelectionnerDates(df, freq)
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Date'}, inplace=True)

        if freq == "Y":
            # Décaler les dates d'un an
            df['Date'] = df['Date'] - pd.DateOffset(years=1)

        return df
    #############################
    ####################################################



pat = Patrimoine()
pat.PlotlyInteractive("src/tests/", "patrimoine.html")