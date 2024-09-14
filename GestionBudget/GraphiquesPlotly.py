from Sankey import SankeyGenerator

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os


class GraphiqueFinancier():
    """
    La classe `GraphiqueFinancier` est conçue pour générer divers types de graphiques financiers à partir de données de transactions. Elle permet la création de graphiques Sankey, en barres, circulaires, et leur combinaison, en utilisant la bibliothèque Plotly. La classe gère également la sauvegarde des graphiques dans un fichier HTML.

    Attributs:
        - `data` (dict): Dictionnaire contenant les données de transactions, où chaque clé est le nom de la catégorie et chaque valeur est une liste de transactions représentées par des dictionnaires.
        - `outputFile` (str): Nom du fichier HTML où les graphiques générés seront sauvegardés.
        - `filePlotly` (list): Liste des graphiques Plotly générés pour être sauvegardés.
        - `dfs` (dict): Dictionnaire de DataFrames pandas créés à partir des données de transactions, regroupés par catégorie.
        - `dfRevenus` (pd.DataFrame): DataFrame des revenus.
        - `dfDepenses` (pd.DataFrame): DataFrame des dépenses.

    Méthodes:
        - `__init__(self, data: dict, outputFile: str)`: Initialise le générateur de graphiques avec les données de transactions et le nom du fichier HTML pour sauvegarder les graphiques.
        - `SetData(self, newData: dict)`: Modifie les données de transactions et met à jour les DataFrames en conséquence.
        - `SetOutputFile(self, newOutputFile: str)`: Modifie le nom du fichier de sortie pour les graphiques.
        - `GraphiqueSankey(self, title: str ="", save=True) -> go.Figure`: Crée un graphique Sankey à partir des données de transactions et le sauvegarde dans la liste des graphiques générés si `save` est True.
        - `GraphiqueBar(self, df: pd.DataFrame, title: str, save=True) -> go.Figure`: Crée un graphique en barres empilées à partir d'un DataFrame et le sauvegarde dans la liste des graphiques générés si `save` est True.
        - `GraphiqueCirculaire(self, df: pd.DataFrame, name: str, save=True) -> go.Figure`: Crée un graphique circulaire à partir d'un DataFrame et le sauvegarde dans la liste des graphiques générés si `save` est True.
        - `CombinerGraphiques(self, fig1: go.Figure, fig2: go.Figure, save=True) -> go.Figure`: Combine deux graphiques de type sunburst côte à côte dans une seule figure et le sauvegarde dans la liste des graphiques générés si `save` est True.
        - `GraphiqueAutomatique(self, compteCourant: bool)`: Gère la génération automatique des graphiques en fonction du type de compte (courant ou non) et des données disponibles.
        - `LivretA(self)`: Gère la génération des graphiques pour un Livret A.
        - `CompteCourantRevenusDepenses(self)`: Gère la génération des graphiques pour un compte courant avec revenus et dépenses.
        - `CompteCourantUniquementDepenses(self)`: Gère la génération des graphiques pour un compte courant avec uniquement des dépenses.
        - `CompteCourantUniquementRevenus(self)`: Gère la génération des graphiques pour un compte courant avec uniquement des revenus.
        - `TitreSankey(self)`: Génère un titre pour le graphique Sankey basé sur les données de revenus et de dépenses.
        - `SaveInFile(self)`: Enregistre les graphiques générés dans le fichier HTML spécifié.
        - `CreateDirectories(self)`: Vérifie l'existence des dossiers dans le chemin spécifié et les crée si nécessaire.
    """

    def __init__(self, data: dict, outputFile: str):
        """
        Initialise le générateur de graphiques avec des données de transactions.

        Args:
            data: Dictionnaire contenant les données de transactions, où chaque clé est le nom de la catégorie et chaque valeur est une liste de dictionnaires représentant les transactions.
            outputFile: Nom du fichier HTML pour sauvegarder les graphiques générés.

        Raises:
            AssertionError: Si les données ou le fichier ne sont pas dans le bon format.
        """
        assert isinstance(data, dict) and all(isinstance(key, str) and isinstance(value, list) for key, value in data.items()), \
            "Les données doivent être un dictionnaire avec des clés en chaînes de caractères et des valeurs en list."
        
        requiredKeys = ['MONTANT']
        assert isinstance(data, dict) and all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(d, dict) and all(key in d for key in requiredKeys) for d in v) for k, v in data.items()
        ), f"Chaque dictionnaire dans les listes doit contenir les clés suivantes : {', '.join(requiredKeys)}."

        assert (isinstance(outputFile, str)) and (outputFile.endswith(".html")), f"Le fichier outputFile doit être une chaîne de caractère dont l'extension est .html"


        self.data = data
        self.outputFile = outputFile

        self.filePlotly = []

        self.dfs = {key: pd.DataFrame(value) for key, value in self.data.items() if value}
        self.dfRevenus = self.dfs.get('Revenus', pd.DataFrame())
        
        # Si dans Le data Frame revenu sont positifs il faut les mettre en négatif
        if (not self.dfRevenus.empty) and (self.dfRevenus["MONTANT"].iloc[0] > 0):
            self.dfRevenus["MONTANT"] *= -1

        self.dfDepenses = pd.DataFrame()

        # Préparer les données de dépenses
        for category, df in self.dfs.items():
            df["category"] = category
            df["MONTANT"] *= -1

            if "Type" not in df.columns:
                df["Type"] = category

            if category != "Revenus":
                self.dfDepenses = pd.concat([self.dfDepenses, df], ignore_index=True)


    def SetData(self, newData):
        """
        Modifie l'attribut 'data' avec les nouvelles données fournies et prépare les DataFrames pour les revenus 
        et les dépenses.

        Args:
            newData (dict): Un dictionnaire contenant des données où chaque clé est une chaîne de caractères 
                            et chaque valeur est une liste de dictionnaires. Chaque dictionnaire dans la liste 
                            doit contenir au moins la clé 'MONTANT'.
        """
        assert isinstance(newData, dict) and all(isinstance(key, str) and isinstance(value, list) for key, value in newData.items()), \
            "Les données doivent être un dictionnaire avec des clés en chaînes de caractères et des valeurs en list."
        
        requiredKeys = ['MONTANT']
        assert isinstance(newData, dict) and all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(d, dict) and all(key in d for key in requiredKeys) for d in v) for k, v in newData.items()
        ), f"Chaque dictionnaire dans les listes doit contenir les clés suivantes : {', '.join(requiredKeys)}."

        self.data = newData

        self.dfs = {key: pd.DataFrame(value) for key, value in self.data.items() if value}
        self.dfRevenus = self.dfs.get('Revenus', pd.DataFrame())
        
        # Si dans Le data Frame revenu sont positifs il faut les mettre en négatif
        if (not self.dfRevenus.empty) and (self.dfRevenus["MONTANT"].iloc[0] > 0):
            self.dfRevenus["MONTANT"] *= -1

        self.dfDepenses = pd.DataFrame()

        # Préparer les données de dépenses
        for category, df in self.dfs.items():
            df["category"] = category
            df["MONTANT"] *= -1

            if "Type" not in df.columns:
                df["Type"] = category

            if category != "Revenus":
                self.dfDepenses = pd.concat([self.dfDepenses, df], ignore_index=True)
    
    def SetOutputFile(self, newOutputFile):
        """
        Modifie outputFile
        """
        assert (isinstance(newOutputFile, str)) and (newOutputFile.endswith(".html")), f"Le fichier outputFile doit être une chaîne de caractère dont l'extension est .html"

        self.outputFile = newOutputFile


    def GraphiqueSankey(self, title: str ="", save=True) -> go.Figure:
        """
        Crée un graphique Sankey à partir des données de transactions en utilisant la classe SankeyGenerator.

        Args:
            title: Titre du graphique Sankey.
            save: Indique si le graphique doit être sauvegardé dans la liste des graphiques générés.

        Returns:
            go.Figure: La figure Sankey générée.
        """
        assert isinstance(title, str), "title doit être une chaîne de caractères."

        sankey = SankeyGenerator(dictionnaire=self.data, title=title)
        sankeyFig = sankey.GetFigure()

        if save:
            self.filePlotly.append(sankeyFig)

        return sankeyFig

    def GraphiqueBar(self, df: pd.DataFrame, title: str, save=True) -> go.Figure:
        """
        Crée un graphique en barres empilées à partir d'un DataFrame.

        Args:
            df: DataFrame contenant les données à visualiser.
            title: Titre du graphique.
            save: Indique si le graphique doit être sauvegardé dans la liste des graphiques générés.

        Returns:
            go.Figure: La figure du graphique en barres empilées.
        """
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame."
        assert isinstance(title, str), "title doit être une chaîne de caractères."

        dfGrouped = df.groupby(['category', 'Type']).agg({'MONTANT': 'sum'}).reset_index()
        dfGrouped = dfGrouped.sort_values(by='MONTANT', ascending=False)
        dfGrouped['TotalCategory'] = dfGrouped.groupby('category')['MONTANT'].transform('sum')
        dfGrouped['Percentage'] = (dfGrouped['MONTANT'] / dfGrouped['TotalCategory']) * 100
        dfGrouped['Text'] = dfGrouped.apply(lambda row: f"{row['Type']} ({row['Percentage']:.1f}%)", axis=1)

        fig = px.bar(
            dfGrouped,
            x='category',
            y='MONTANT',
            color='Type',
            title=title,
            labels={'category': 'Catégories', 'MONTANT': 'Prix €'},
            text='Text'
        )

        fig.update_traces(texttemplate='%{text}', textposition='inside')
        fig.update_layout(
            showlegend=True,
            width=1800,
            height=900,
            margin=dict(l=200, r=100, t=50, b=50)
        )

        if save:
            self.filePlotly.append(fig)
        return fig

    def GraphiqueCirculaire(self, df: pd.DataFrame, name: str, save=True) -> go.Figure:
        """
        Crée un graphique circulaire à partir d'un DataFrame.

        Args:
            df: DataFrame contenant les données à visualiser.
            name: Nom pour le centre du graphique.
            save: Indique si le graphique doit être sauvegardé dans la liste des graphiques générés.

        Returns:
            go.Figure: La figure du graphique circulaire.
        """
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame."
        assert isinstance(name, str), "name doit être une chaîne de caractères."

        labels = [name]
        parents = ['']
        values = [df['MONTANT'].sum()]

        for category in df['category'].unique():
            labels.append(category)
            parents.append(name)
            values.append(df[df['category'] == category]['MONTANT'].sum())

            for typeOp in df[df['category'] == category]['Type'].unique():
                labels.append(typeOp)
                parents.append(category)
                values.append(df[(df['category'] == category) & (df['Type'] == typeOp)]['MONTANT'].sum())

        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues='total',
            textinfo='label+percent entry'
        ))

        fig.update_layout(
            showlegend=True,
            width=1800,
            height=900,
            margin=dict(l=200, r=100, t=50, b=50)
        )
        
        if save:
            self.filePlotly.append(fig)
        return fig

    def CombinerGraphiques(self, fig1: go.Figure, fig2: go.Figure, save=True) -> go.Figure:
        """
        Combine deux graphiques de type sunburst côte à côte dans une seule figure.

        Args:
            fig1: Premier graphique sunburst.
            fig2: Deuxième graphique sunburst.
            save: Indique si le graphique combiné doit être sauvegardé.

        Returns:
            go.Figure: La figure combinée.
        """
        assert isinstance(fig1, go.Figure) and isinstance(fig2, go.Figure), \
            "Les arguments doivent être des objets go.Figure."

        # Crée une figure avec deux sous-graphes côte à côte pour les graphiques sunburst
        figCombined = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "sunburst"}, {"type": "sunburst"}]]
        )

        # Ajouter les traces du premier graphique sunburst au premier sous-graphe
        for trace in fig1.data:
            figCombined.add_trace(trace, row=1, col=1)

        # Ajouter les traces du deuxième graphique sunburst au deuxième sous-graphe
        for trace in fig2.data:
            figCombined.add_trace(trace, row=1, col=2)

        # Mettre à jour la mise en page pour la figure combinée
        figCombined.update_layout(
            showlegend=True,
            width=1800,
            height=900,
            margin=dict(
                l=200,  # marge gauche
                r=100,  # marge droite
                t=50,   # marge supérieure
                b=50    # marge inférieure
            )
        )

        if save:
            self.filePlotly.append(figCombined)
        return figCombined

    def GraphiqueHistogrammeSuperpose(self):
        """
        Génère un graphique en histogramme empilé pour visualiser les dépenses par mois.
        Les catégories avec les dépenses les plus élevées sont placées en bas du graphique pour chaque mois.
        """

        # Préparer les données
        dfDepenses = self.dfDepenses.copy()

        dfDepenses['DATE D\'OPÉRATION'] = pd.to_datetime(dfDepenses['DATE D\'OPÉRATION'])
        dfDepenses['Mois'] = dfDepenses['DATE D\'OPÉRATION'].dt.to_period('M').astype(str)

        # Vérifier les mois uniques
        moisUniques = dfDepenses['Mois'].unique()

        # Si il y a plusieurs mois alors on enregistre le graphique
        if len(moisUniques) > 1:
            # Agréger les dépenses par mois et par catégorie
            dfAggrege = dfDepenses.groupby(['Mois', 'category'])['MONTANT'].sum().reset_index()

            # Créer une table pivot avec les catégories triées par mois
            dfPivot = dfAggrege.pivot_table(index='Mois', columns='category', values='MONTANT', fill_value=0)
            
            # Trier les colonnes pour chaque mois
            dfSorted = pd.DataFrame(index=dfPivot.index)
            for mois in dfPivot.index:
                sorted_categories = dfPivot.loc[mois].sort_values(ascending=False).index
                dfSorted.loc[mois, sorted_categories] = dfPivot.loc[mois, sorted_categories]

            # Transposer le DataFrame pour Plotly
            dfSorted = dfSorted.reset_index().melt(id_vars='Mois', var_name='Catégorie', value_name='Montant')

            # Créer le graphique en histogramme empilé
            fig = px.bar(
                dfSorted,
                x='Mois',
                y='Montant',
                color='Catégorie',
                title="Dépenses par Catégorie par Mois",
                labels={"Montant": "Montant", "Catégorie": "Catégorie"}
            )

            fig.update_layout(barmode='stack')
            
            self.filePlotly.append(fig)
        

    def GraphiqueAutomatique(self, compteCourant):
        """
        Gère la génération automatique de graphiques en fonction du type de compte et des données disponibles.

        Args:
            compteCourant: Booléen indiquant s'il s'agit d'un compte courant.
        """
        assert isinstance(compteCourant, bool), f"compteCourant doit être un booléean: {type(compteCourant).__name__}"

        if not compteCourant:
            self.LivretA()
        elif (not self.dfRevenus.empty) and (not self.dfDepenses.empty):
            self.CompteCourantRevenusDepenses()
        elif (not self.dfRevenus.empty) and (self.dfDepenses.empty):
            self.CompteCourantUniquementRevenus()
        else:
            self.CompteCourantUniquementDepenses()

    def LivretA(self):
        """
        Gère la génération des graphiques pour le Livret A.
        """
        
        # Changement de l'appellation car ce n'est pas de l'investissement mais c'est des virements sur d'autres comptes
        if "Investissement" in self.data:
            self.data["Virement sur les comptes"] = self.data.pop("Investissement")
            for tab in self.data.values():
                for ele in tab:
                    if ele["Type"] == "Livret A":
                        ele["Type"] = "Compte Courant"
                        
        # Si on a des revenus mais pas de dépenses
        if self.dfDepenses.empty and not self.dfRevenus.empty:
            self.GraphiqueSankey()
            self.GraphiqueCirculaire(df=self.dfRevenus, name="Revenus du Livret A")
        # Si on a des des dépenses mais pas de revenus
        elif not self.dfDepenses.empty and self.dfRevenus.empty:
            self.GraphiqueSankey()
            self.GraphiqueCirculaire(df=self.dfDepenses, name="Virement")
        # Si on a des des dépenses et des revenus
        elif not self.dfDepenses.empty and not self.dfRevenus.empty:
            self.GraphiqueSankey()
            self.GraphiqueCirculaire(df=self.dfDepenses, name="Virement")
            self.GraphiqueCirculaire(df=self.dfRevenus, name="Revenus du Livret A")

        self.SaveInFile()

    def CompteCourantRevenusDepenses(self):
        """
        Gère la génération des graphiques pour un compte courant avec revenus et dépenses.
        """
        self.GraphiqueSankey(self.TitreSankey())
        self.GraphiqueHistogrammeSuperpose()

        
        # Filtrer les lignes où la colonne 'category' n'est pas 'Investissement'
        dfFiltre = self.dfDepenses[self.dfDepenses['category'] != 'Investissement']
        # Vérifier si le DataFrame complet des revenus est identique au DataFrame filtré ou que le DataFrame filtré est vide
        if (self.dfDepenses.equals(dfFiltre)) or (dfFiltre.empty):
            self.GraphiqueCirculaire(df=self.dfDepenses, name="Dépenses")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            figSoleilDepenses = self.GraphiqueCirculaire(df=dfFiltre, name="Dépenses", save=False)
            figSoleil = self.GraphiqueCirculaire(df=self.dfDepenses, name="Dépenses + Investissement", save=False)
        
            # Création des graphiques dans l'ordre dans le fichier
            self.CombinerGraphiques(figSoleilDepenses, figSoleil)
        

        # Filtrer les lignes où la colonne 'Type' n'est pas 'Virement interne'
        dfFiltre = self.dfRevenus[self.dfRevenus['Type'] != 'Virement interne']
        # Vérifier si le DataFrame filtré est identique au DataFrame complet des revenus
        if dfFiltre.equals(self.dfRevenus):
            # Si les deux DataFrames sont identiques, créer un seul graphique
            self.GraphiqueCirculaire(df=dfFiltre, name="Revenus gagné")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            figSoleilRevenus = self.GraphiqueCirculaire(df=dfFiltre, name="Revenus gagné", save=False)
            figSoleilAllRevenus = self.GraphiqueCirculaire(df=self.dfRevenus, name="Revenus gagné + Virement interne", save=False)
            
            # Création des graphiques combinés dans l'ordre
            self.CombinerGraphiques(figSoleilRevenus, figSoleilAllRevenus)


        self.SaveInFile()

    def CompteCourantUniquementDepenses(self):
        """
        Gère la génération des graphiques pour un compte courant avec uniquement des dépenses.
        Crée un graphique circulaire pour les dépenses avec et sans la catégorie Investissement,
        mais évite de dupliquer les graphiques si la catégorie Investissement n'est pas présents.
        """

        self.GraphiqueHistogrammeSuperpose()

        # Filtrer les lignes où la colonne 'category' n'est pas 'Investissement'
        dfFiltre = self.dfDepenses[self.dfDepenses['category'] != 'Investissement']
        
        # Vérifier si le DataFrame complet des revenus est identique au DataFrame filtré ou que le DataFrame filtré est vide
        if (self.dfDepenses.equals(dfFiltre)) or (dfFiltre.empty):
            self.GraphiqueCirculaire(df=self.dfDepenses, name="Dépenses")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            figSoleilDepenses = self.GraphiqueCirculaire(df=dfFiltre, name="Dépenses", save=False)
            figSoleil = self.GraphiqueCirculaire(df=self.dfDepenses, name="Dépenses + Investissement", save=False)
        
            # Création des graphiques dans l'ordre dans le fichier
            self.CombinerGraphiques(figSoleilDepenses, figSoleil)

        self.SaveInFile()

    def CompteCourantUniquementRevenus(self):
        """
        Gère la génération des graphiques pour un compte courant avec uniquement des revenus.
        Crée un graphique circulaire pour les revenus gagnés avec et sans virements internes,
        mais évite de dupliquer les graphiques si les virements internes ne sont pas présents.
        """
        # Filtrer les lignes où la colonne 'Type' n'est pas 'Virement interne'
        dfFiltre = self.dfRevenus[self.dfRevenus['Type'] != 'Virement interne']
        
        # Vérifier si le DataFrame filtré est identique au DataFrame complet des revenus
        if dfFiltre.equals(self.dfRevenus):
            # Si les deux DataFrames sont identiques, créer un seul graphique
            self.GraphiqueCirculaire(df=dfFiltre, name="Revenus gagné")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            figSoleilRevenus = self.GraphiqueCirculaire(df=dfFiltre, name="Revenus gagné", save=False)
            figSoleilAllRevenus = self.GraphiqueCirculaire(df=self.dfRevenus, name="Revenus gagné + Virement interne", save=False)
            
            # Création des graphiques combinés dans l'ordre
            self.CombinerGraphiques(figSoleilRevenus, figSoleilAllRevenus)
        
        # Enregistrer les graphiques dans un fichier
        self.SaveInFile()

    def TitreSankey(self):
        """
        Génère un titre pour le graphique Sankey.
        """
        sommeDepenses = sum(self.dfDepenses["MONTANT"])
        sommeEpargne = sum(self.dfDepenses[self.dfDepenses["category"] == "Investissement"]["MONTANT"])

        tauxEpargne = round(sommeEpargne * 100 / sommeDepenses, 2)
        revenus = round(sum(self.dfRevenus["MONTANT"]), 2)
        depenses = round(sum(self.dfDepenses[self.dfDepenses["category"] != "Investissement"]["MONTANT"]), 2)

        return f"Le taux d'épargne est de {tauxEpargne}%. Les revenus s'élèves à {revenus}€ et les dépenses sont de {depenses}€"



    def SaveInFile(self):
        """
        Enregistre les graphiques générés dans un fichier HTML.
        """
        # Crée un fichier HTML pour enregistrer les graphiques
        self.CreateDirectories()

        with open(self.outputFile, 'w') as f:
            for fig in self.filePlotly:
                fig.write_html(f, include_plotlyjs='cdn')

        # On réinitialise l'importation des graphiques dans le fichier
        self.filePlotly = []

    def CreateDirectories(self):
        """
        Vérifie l'existence des dossiers et sous-dossiers dans le chemin spécifié et les crée si nécessaire.
        """
        # Obtenez le répertoire parent du fichier pour créer les dossiers
        directory = os.path.dirname(self.outputFile)
        
        # Vérifiez si le répertoire existe, sinon créez-le
        if not os.path.exists(directory):
            os.makedirs(directory)
