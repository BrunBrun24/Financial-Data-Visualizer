from database.compte_titre import CompteTireBdd
from .sankey_generator import SankeyGenerator

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os


class GraphiqueFinancier(CompteTireBdd):
    """
    La classe `GraphiqueFinancier` génère différents graphiques financiers à partir des opérations 
    catégorisées d'un compte bancaire. Elle hérite de `CompteTireBdd` et fournit des méthodes pour :

    - Créer des dossiers annuels pour organiser les graphiques.
    - Générer des graphiques Sankey, en barres empilées et circulaires (sunburst) pour visualiser 
    les revenus, les dépenses et leur répartition par catégorie et sous-catégorie.
    - Combiner plusieurs graphiques côte à côte si nécessaire pour éviter les doublons.
    - Produire des bilans annuels et mensuels en créant et sauvegardant automatiquement les fichiers HTML.

    Arguments du constructeur :
        - db_path (str) : chemin vers la base de données contenant les opérations financières.
        - root_path (str) : chemin vers la où seront enregistré les fichiers.

    Attributs principaux :
        - _operations_categorisees : DataFrame des opérations financières catégorisées.
        - _file_plotly : liste interne des figures Plotly générées.
        - _root_path : chemin du dossier où les fichiers HTML seront sauvegardés.
    """

    def __init__(self, db_path: str, root_path: str):
        super().__init__(db_path)
        self.__root_path = root_path
        self.__operations_categorisees = self._get_operations_categorisees()
        self.__file_plotly = []

        self.__create_year_folders()

    
    def __create_year_folders(self):
        """
        Crée les dossiers pour chaque année à partir des opérations catégorisées.

        - Crée d’abord le dossier principal `self.__root_path`.
        - Extrait l'année de chaque opération dans `self.__operations_categorisees`.
        - Crée un sous-dossier pour chaque année unique à l’intérieur du dossier principal.
        """
        # Création du dossier principal
        os.makedirs(self.__root_path, exist_ok=True)

        # On suppose que self.__operations_categorisees est un DataFrame pandas
        df = self.__operations_categorisees.copy()
        df["annee"] = df["date_operation"].dt.year

        # Liste des années uniques
        annees = sorted(df["annee"].unique())

        # Création des sous-dossiers par année
        for annee in annees:
            year_path = os.path.join(self.__root_path, str(annee))
            os.makedirs(year_path, exist_ok=True)

    @staticmethod
    def __get_month_operations_categorisees(df_all: pd.DataFrame) -> dict:
        """
        Regroupe les opérations catégorisées par mois.

        Arguments :
        - df_all (pd.DataFrame) : DataFrame contenant les opérations catégorisées, 
                                avec une colonne 'date_operation' de type datetime.

        Returns :
        - dict : dictionnaire { mois (str) : DataFrame des opérations de ce mois }
        """
        # Extraction de l'année
        df_all["month"] = df_all["date_operation"].dt.strftime('%m')

        month_dict = {}

        # Groupement par année
        for annee, df_annee in df_all.groupby("month"):
            month_dict[annee] = df_annee.reset_index(drop=True)

        return month_dict

    @staticmethod
    def __get_df_revenus(operation_categorisees: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre les opérations de la catégorie 'Revenus' et convertit la date en datetime.

        Arguments :
        - operation_categorisees (pd.DataFrame) : DataFrame des opérations catégorisées.

        Returns :
        - pd.DataFrame : DataFrame filtré des revenus.
        """
        df = operation_categorisees[operation_categorisees['categorie'] == 'Revenus'].copy()
        df["date_operation"] = pd.to_datetime(df["date_operation"])
        return df

    @staticmethod
    def __get_df_depenses(operation_categorisees: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre les opérations hors 'Revenus', convertit la date et prend la valeur absolue des montants.

        Arguments :
        - operation_categorisees (pd.DataFrame) : DataFrame des opérations catégorisées.

        Returns :
        - pd.DataFrame : DataFrame filtré des dépenses avec montants positifs.
        """
        df = operation_categorisees[operation_categorisees['categorie'] != 'Revenus'].copy()
        df["date_operation"] = pd.to_datetime(df["date_operation"])
        df['montant'] = df['montant'].abs()
        return df

    def __save_in_file(self):
        """Enregistre tous les graphiques générés dans un fichier HTML."""
        with open(self._output_file, 'w') as f:
            for fig in self.__file_plotly:
                fig.write_html(f, include_plotlyjs='cdn')
        self.__file_plotly = []

    def __graphique_sankey(self, df: pd.DataFrame, title: str = "", save: bool = True) -> go.Figure:
        """
        Crée un graphique Sankey à partir des opérations catégorisées.

        Arguments :
            df (pd.DataFrame) : DataFrame contenant les opérations catégorisées.
            title (str, optionnel) : titre du graphique (par défaut "").
            save (bool, optionnel) : indique si le graphique doit être sauvegardé dans la liste interne (par défaut True).

        Returns :
            go.Figure : objet figure Plotly contenant le graphique Sankey généré.
        """
        sankey = SankeyGenerator(
            df=df,
            title=title
        )
        fig = sankey.get_figure()
        if save:
            self.__file_plotly.append(fig)
        return fig

    def __graphique_bar(self, df: pd.DataFrame, title: str, save: bool = True) -> go.Figure:
        """
        Crée un graphique en barres empilées à partir d'un DataFrame d'opérations catégorisées.

        Arguments :
            df (pd.DataFrame) : DataFrame contenant les opérations catégorisées.
            title (str) : titre du graphique.
            save (bool, optionnel) : indique si le graphique doit être sauvegardé dans la liste interne (par défaut True).

        Returns :
            go.Figure : objet figure Plotly contenant le graphique en barres généré.
        """
        df_grouped = df.groupby(['categorie', 'sous_categorie']).agg({'montant': 'sum'}).reset_index()
        df_grouped = df_grouped.sort_values(by='montant', ascending=False)
        df_grouped['total_categorie'] = df_grouped.groupby('categorie')['montant'].transform('sum')
        df_grouped['percentage'] = df_grouped['montant'] / df_grouped['total_categorie'] * 100
        df_grouped['text'] = df_grouped.apply(lambda row: f"{row['sous_categorie']} ({row['percentage']:.1f}%)", axis=1)

        fig = px.bar(
            df_grouped,
            x='categorie',
            y='montant',
            color='sous_categorie',
            text='text',
            title=title,
            labels={'categorie': 'Catégorie', 'montant': 'Montant €'}
        )
        fig.update_traces(texttemplate='%{text}', textposition='inside')
        if save:
            self.__file_plotly.append(fig)
        return fig

    def __graphique_circulaire(self, df: pd.DataFrame, name: str, save: bool = True) -> go.Figure:
        """
        Crée un graphique circulaire (sunburst) représentant la répartition des montants par catégorie et sous-catégorie.

        Arguments :
            df (pd.DataFrame) : DataFrame contenant les opérations catégorisées.
            name (str) : nom du graphique ou du nœud racine.
            save (bool, optionnel) : indique si le graphique doit être sauvegardé dans la liste interne (par défaut True).

        Returns :
            go.Figure : objet figure Plotly contenant le graphique circulaire généré.
        """
        labels = [name]
        parents = ['']
        values = [df['montant'].sum()]

        for categorie in df['categorie'].unique():
            labels.append(categorie)
            parents.append(name)
            values.append(df[df['categorie'] == categorie]['montant'].sum())

            for type_op in df[df['categorie'] == categorie]['sous_categorie'].unique():
                labels.append(type_op)
                parents.append(categorie)
                values.append(df[(df['categorie'] == categorie) & (df['sous_categorie'] == type_op)]['montant'].sum())

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
            self.__file_plotly.append(fig)
        return fig

    def __combiner_graphiques(self, fig1: go.Figure, fig2: go.Figure, save: bool = True) -> go.Figure:
        """
        Combine deux graphiques sunburst côte à côte dans une seule figure.

        Arguments :
            fig1 (go.Figure) : premier graphique sunburst.
            fig2 (go.Figure) : second graphique sunburst.
            save (bool, optionnel) : indique si la figure combinée doit être sauvegardée dans la liste interne (par défaut True).

        Returns :
            go.Figure : objet figure Plotly contenant les deux graphiques combinés.
        """
        fig_combined = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "sunburst"}, {"type": "sunburst"}]]
        )

        for trace in fig1.data:
            fig_combined.add_trace(trace, row=1, col=1)
        for trace in fig2.data:
            fig_combined.add_trace(trace, row=1, col=2)

        fig_combined.update_layout(
            showlegend=True,
            width=1800,
            height=900,
            margin=dict(l=200, r=100, t=50, b=50)
        )
        if save:
            self.__file_plotly.append(fig_combined)
        return fig_combined

    def __compte_courant_revenus_depenses(self, df_revenus: pd.DataFrame, df_depenses: pd.DataFrame, df_all: pd.DataFrame):
        """
        Génère et organise les graphiques pour un compte courant avec revenus et dépenses.

        Arguments :
            df_revenus (pd.DataFrame) : DataFrame contenant les opérations de revenus.
            df_depenses (pd.DataFrame) : DataFrame contenant les opérations de dépenses.
            df_all (pd.DataFrame) : DataFrame combinant toutes les opérations (revenus + dépenses).

        Actions :
            - Crée un graphique Sankey pour l’ensemble des opérations.
            - Crée un histogramme empilé pour les dépenses.
            - Génère des graphiques circulaires des dépenses et des revenus,
            en séparant éventuellement les sous-catégories spécifiques (Investissement, Épargne, Virements internes).
            - Combine plusieurs graphiques côte à côte si nécessaire.
            - Sauvegarde tous les graphiques générés dans un fichier HTML.
        """
        self.__graphique_sankey(df_all, self.__titre_sankey(df_revenus, df_depenses))
        self.__graphique_histogramme_superpose(df_depenses)

        # Filtrer les lignes où la colonne 'categorie' n'est pas 'Investissement' ni "Épargne"
        df_filtre = df_depenses[
            (df_depenses['categorie'] != 'Investissement') &
            (df_depenses['categorie'] != 'Épargne')
        ]
        # Vérifier si le DataFrame complet des revenus est identique au DataFrame filtré ou que le DataFrame filtré est vide
        if (df_depenses.equals(df_filtre)) or (df_filtre.empty):
            self.__graphique_circulaire(df=df_depenses, name="Dépenses")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_depenses = self.__graphique_circulaire(df=df_filtre, name="Dépenses", save=False)
            fig_soleil = self.__graphique_circulaire(df=df_depenses, name="Dépenses + Investissement", save=False)
        
            # Création des graphiques dans l'ordre dans le fichier
            self.__combiner_graphiques(fig_soleil_depenses, fig_soleil)
        
        # Filtrer les lignes où la colonne 'sous_categorie' n'est pas 'Virements internes'
        df_filtre = df_revenus[df_revenus['sous_categorie'] != 'Virements internes']
        # Vérifier si le DataFrame filtré est identique au DataFrame complet des revenus
        if df_filtre.equals(df_revenus):
            # Si les deux DataFrames sont identiques, créer un seul graphique
            self.__graphique_circulaire(df=df_filtre, name="Revenus gagné")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_revenus = self.__graphique_circulaire(df=df_filtre, name="Revenus gagné", save=False)
            fig_soleil_all_revenus = self.__graphique_circulaire(df=df_revenus, name="Revenus gagné + Virements internes", save=False)
            
            # Création des graphiques combinés dans l'ordre
            self.__combiner_graphiques(fig_soleil_revenus, fig_soleil_all_revenus)

        self.__save_in_file()

    def __compte_courant_depenses(self, df_depenses: pd.DataFrame):
        """
        Génère et organise les graphiques pour un compte courant ne contenant que des dépenses.

        Arguments :
            df_depenses (pd.DataFrame) : DataFrame contenant les opérations de dépenses.

        Actions :
            - Crée un histogramme empilé pour les dépenses.
            - Génère un graphique circulaire des dépenses, en séparant éventuellement la catégorie 'Investissement' et 'Épargne'.
            - Combine plusieurs graphiques côte à côte si nécessaire pour éviter les doublons.
            - Sauvegarde tous les graphiques générés dans un fichier HTML.
        """
        self.__graphique_histogramme_superpose(df_depenses)

        # Filtrer les lignes où la colonne 'categorie' n'est pas 'Investissement' ni "Épargne"
        df_filtre = df_depenses[
            (df_depenses['categorie'] != 'Investissement') &
            (df_depenses['categorie'] != 'Épargne')
        ]
        
        # Vérifier si le DataFrame complet des revenus est identique au DataFrame filtré ou que le DataFrame filtré est vide
        if (df_depenses.equals(df_filtre)) or (df_filtre.empty):
            self.__graphique_circulaire(df=df_depenses, name="Dépenses")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_depenses = self.__graphique_circulaire(df=df_filtre, name="Dépenses", save=False)
            fig_soleil = self.__graphique_circulaire(df=df_depenses, name="Dépenses + Investissement", save=False)
        
            # Création des graphiques dans l'ordre dans le fichier
            self.__combiner_graphiques(fig_soleil_depenses, fig_soleil)

        self.__save_in_file()

    def __compte_courant_revenus(self, df_revenus: pd.DataFrame):
        """
        Génère et organise les graphiques pour un compte courant contenant uniquement des revenus.

        Arguments :
            df_revenus (pd.DataFrame) : DataFrame contenant les opérations de revenus.

        Actions :
            - Génère un graphique circulaire des revenus gagnés, en séparant éventuellement les 'Virements internes'.
            - Combine plusieurs graphiques côte à côte si nécessaire pour éviter les doublons.
            - Sauvegarde tous les graphiques générés dans un fichier HTML.
        """
        # Filtrer les lignes où la colonne 'sous_categorie' n'est pas 'Virements internes'
        df_filtre = df_revenus[df_revenus['sous_categorie'] != 'Virements internes']
        
        # Vérifier si le DataFrame filtré est identique au DataFrame complet des revenus
        if df_filtre.equals(df_revenus):
            # Si les deux DataFrames sont identiques, créer un seul graphique
            self.__graphique_circulaire(df=df_filtre, name="Revenus gagné")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_revenus = self.__graphique_circulaire(df=df_filtre, name="Revenus gagné", save=False)
            fig_soleil_all_revenus = self.__graphique_circulaire(df=df_revenus, name="Revenus gagné + Virements internes", save=False)
            
            # Création des graphiques combinés dans l'ordre
            self.__combiner_graphiques(fig_soleil_revenus, fig_soleil_all_revenus)
        
        # Enregistrer les graphiques dans un fichier
        self.__save_in_file()

    def __graphique_histogramme_superpose(self, df_depenses: pd.DataFrame):
        """
        Crée un histogramme empilé des dépenses par mois.

        Arguments :
            df_depenses (pd.DataFrame) : DataFrame contenant les opérations de dépenses.

        Actions :
            - Agrège les dépenses par mois et par catégorie.
            - Trie les catégories par montant pour chaque mois (les plus élevées en bas).
            - Génère un graphique en barres empilées avec Plotly et l'ajoute à la liste de graphiques à sauvegarder.
        """
        # Préparer les données
        df_depenses = df_depenses.copy()
        df_depenses['Mois'] = df_depenses['date_operation'].dt.to_period('M').astype(str)

        # Vérifier les mois uniques
        moisUniques = df_depenses['Mois'].unique()

        # Si il y a plusieurs mois alors on enregistre le graphique
        if len(moisUniques) > 1:
            # Agréger les dépenses par mois et par catégorie
            dfAggrege = df_depenses.groupby(['Mois', 'categorie'])['montant'].sum().reset_index()

            # Créer une table pivot avec les catégories triées par mois
            dfPivot = dfAggrege.pivot_table(index='Mois', columns='categorie', values='montant', fill_value=0)
            
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
                labels={"Montant": "Montant", "Catégorie": "Catégorie"}
            )

            fig.update_layout(
                barmode='stack',
                xaxis_title=None,
                yaxis_title=None,
                yaxis=dict(
                    tickprefix="€"
                )
            )
            
            self.__file_plotly.append(fig)
        
    @staticmethod
    def __titre_sankey(df_revenus: pd.DataFrame, df_depenses: pd.DataFrame) -> str:
        """
        Génère un titre descriptif pour le graphique Sankey.

        Arguments :
            df_revenus (pd.DataFrame) : DataFrame des opérations de revenus.
            df_depenses (pd.DataFrame) : DataFrame des opérations de dépenses.

        Retour :
            str : titre indiquant le taux d'épargne, le total des revenus et des dépenses.
        """
        somme_depenses = sum(df_depenses["montant"])
        somme_epargne = sum(df_depenses[df_depenses["categorie"] == "Investissement"]["montant"])

        taux_epargne = round(somme_epargne * 100 / somme_depenses, 2)
        revenus = round(sum(df_revenus[df_revenus["sous_categorie"] != "Virements internes"]["montant"]), 2)
        depenses = round(sum(df_depenses[df_depenses["categorie"] != "Investissement"]["montant"]), 2)

        return (
            f"Le taux d'épargne est de {taux_epargne}%. "
            f"Les revenus s'élèvent à {revenus}€ "
            f"et les dépenses sont de {depenses}€."
        )

    def __bilan_year(self, df_revenus: pd.DataFrame, df_depenses: pd.DataFrame, df_all: pd.DataFrame):
        """
        Crée les graphiques pour le bilan annuel selon la présence de revenus et/ou dépenses.

        Arguments :
            df_revenus (pd.DataFrame) : DataFrame des opérations de revenus.
            df_depenses (pd.DataFrame) : DataFrame des opérations de dépenses.
            df_all (pd.DataFrame) : DataFrame complet des opérations (revenus + dépenses).
        """

        if (not df_revenus.empty) and (not df_depenses.empty):
            self.__compte_courant_revenus_depenses(df_revenus, df_depenses, df_all)
        elif (not df_revenus.empty) and (df_depenses.empty):
            self.__compte_courant_revenus(df_revenus)
        else:
            self.__compte_courant_depenses(df_depenses)
            
    def __bilan_year_month(self, df_all: pd.DataFrame, year: int):
        """
        Génère les graphiques mensuels pour le bilan d'une année donnée.

        Arguments :
            df_all (pd.DataFrame) : DataFrame complet des opérations financières de l'année.
            year (int) : Année pour laquelle les graphiques mensuels sont créés.
        """
        month_operations_categorisees = self.__get_month_operations_categorisees(df_all)

        for month, operations_categorisees in month_operations_categorisees.items():
            self._output_file = f"{self.__root_path}{year}/{year}-{month}.html"
            df_revenus_month = self.__get_df_revenus(operations_categorisees)
            df_depenses_month = self.__get_df_depenses(operations_categorisees)
            df_all_month = pd.concat([df_revenus_month, df_depenses_month], ignore_index=True)

            if (not df_revenus_month.empty) and (not df_depenses_month.empty):
                self.__compte_courant_revenus_depenses(df_revenus_month, df_depenses_month, df_all_month)
            elif (not df_revenus_month.empty) and (df_depenses_month.empty):
                self.__compte_courant_revenus(df_revenus_month)
            else:
                self.__compte_courant_depenses(df_depenses_month)

    
    def main(self, last_year: bool):
        """
        Génère les bilans financiers annuels et mensuels à partir des opérations catégorisées.

        Cette méthode crée pour chaque année (ou uniquement pour les deux dernières si `last_year` est True) :
        - Des graphiques Sankey pour visualiser les flux financiers.
        - Des graphiques circulaires (sunburst) pour détailler la répartition des revenus et dépenses.
        - Des histogrammes empilés pour visualiser les dépenses par mois.

        Les fichiers HTML correspondants sont sauvegardés dans des dossiers par année.

        Arguments :
        - last_year (bool) : si True, ne génère les bilans que pour les deux dernières années disponibles.
        """
        year_operations_categorisees = self._get_year_operations_categorisees()

        # Créez les graphiques uniquement pour les 2 dernières années
        if last_year:
            two_last_years = list(year_operations_categorisees.keys())[-2:]
            year_operations_categorisees = {year: year_operations_categorisees[year] for year in two_last_years}

        for year, operation_categorisees in year_operations_categorisees.items():
            self._output_file = f"{self.__root_path}{year}/Bilan {year}.html"
            df_revenus = self.__get_df_revenus(operation_categorisees)
            df_depenses = self.__get_df_depenses(operation_categorisees)
            df_all = pd.concat([df_revenus, df_depenses], ignore_index=True)

            self.__bilan_year(df_revenus, df_depenses, df_all)
            self.__bilan_year_month(df_all, year)
