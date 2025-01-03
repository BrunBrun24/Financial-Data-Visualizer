import plotly.graph_objects as go
import pandas as pd
import numpy as np


class GraphiqueBar:

    def GraphiqueDividendesParAction(self, portefeuilles: dict) -> go.Figure:
        """
        Trace un graphique de dividendes par action pour différents portefeuilles avec un menu pour choisir le portefeuille.

        Args:
            portefeuilles (dict): Dictionnaire contenant les noms des portefeuilles comme clés et
                                les DataFrames correspondants comme valeurs. Chaque DataFrame doit
                                contenir les années comme index, les noms des actions comme colonnes,
                                et les montants de dividendes (float) comme valeurs.

        Returns:
            go.Figure: Le graphique Plotly interactif avec un menu de sélection de portefeuilles.
        """
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        for key, df in portefeuilles.items():
            assert isinstance(df, pd.DataFrame), f"Les valeurs de 'portefeuilles' doivent être des DataFrames (erreur pour '{key}')."
            assert all(np.issubdtype(dtype, np.number) for dtype in df.dtypes), f"Toutes les colonnes du DataFrame de '{key}' doivent contenir des valeurs numériques."

        colors = [
            "#C70039",  # Rouge cerise
            "#335BFF",  # Bleu vif
            "#FF33B5",  # Rose fuchsia
            "#FF8D33",  # Orange vif
            "#FFC300",  # Jaune doré
            "#33A1FF",  # Bleu ciel
            "#81C784",  # Vert clair
            "#5733FF",  # Violet
            "#FFD54F",  # Jaune foncé
            "#BA68C8",  # Violet clair
            "#4DB6AC",  # Turquoise
            "#33FF57",  # Vert lime
            "#FFB74D",  # Orange doux
            "#FF5733",  # Rouge vif
            "#FFAB40",  # Orange vif
            "#FF7043",  # Rouge saumon
            "#64B5F6",  # Bleu pastel
            "#DCE775",  # Vert pastel
            "#A1887F",  # Marron clair
            "#F0E68C",  # Jaune kaki
        ]

        fig = go.Figure()
        title = "Dividende par action"
        buttons = []
        tracesCount = 0  # Compte du nombre total de traces ajoutées

        # Suppression des entrées avec des DataFrames contenant uniquement des zéros
        filteredDict = {key: df for key, df in portefeuilles.items() if not (df == 0).all().all()}

        # Création de traces pour chaque portefeuille
        for i, (nomPortefeuille, df) in enumerate(filteredDict.items()):
            nbVersementDividendesParAnnee = self.CountDividendsByYear(df.copy())

            # Regrouper par année et calculer la somme
            dataFrameAnnuel = df.resample('YE').sum()
            # Supprimer les lignes dont toutes les colonnes sont égales à zéro
            dataFrameAnnuel = dataFrameAnnuel[(dataFrameAnnuel != 0).any(axis=1)]
            # Modifier l'index pour qu'il ne contienne que l'année
            dataFrameAnnuel.index = dataFrameAnnuel.index.year

            # Calcul de la somme de chaque colonne
            sommeColonnes = dataFrameAnnuel.iloc[-1]
            # Tri des noms de colonnes en ordre alphabétique
            sortedColumns = sommeColonnes.index.sort_values()
            # Réorganisation du DataFrame en utilisant l'ordre trié
            dataFrameAnnuel = dataFrameAnnuel[sortedColumns]

            visibility = [False] * len(fig.data)
            # Filtrer les colonnes dont la somme est supérieure à zéro
            dataFrameAnnuel = dataFrameAnnuel.loc[:, dataFrameAnnuel.sum() > 0]
            nbTickers = len(dataFrameAnnuel.columns)
            if nbTickers <= 2:
                width = 0.4
            elif nbTickers <= 3:
                width = 0.3
            elif nbTickers <= 6:
                width = 0.2
            elif nbTickers <= 10:
                width = 0.2
            else:
                width = 0.1
                if nbTickers > 15:
                    # Calculer la somme de chaque colonne
                    sommeColonnes = dataFrameAnnuel.sum()
                    # Obtenir les 15 colonnes avec les sommes les plus élevées
                    colonnesSelectionnees = sommeColonnes.nlargest(15).index
                    # Filtrer le DataFrame pour ne garder que ces colonnes
                    dataFrameAnnuel = dataFrameAnnuel[colonnesSelectionnees]
                    title += " (seulement 15 actions)"


            for j, col in enumerate(dataFrameAnnuel.columns):
                # Vérifier si l'action a versé des dividendes
                if dataFrameAnnuel[col].sum() != 0:
                    # Ajouter une trace pour l'action courante
                    fig.add_trace(go.Bar(
                        x=dataFrameAnnuel.index,
                        y=dataFrameAnnuel[col],
                        name=f"{col}",
                        marker=dict(color=colors[j % len(colors)]),
                        width=width,
                        visible=(i == 0),  # Rendre visible seulement les traces du premier portefeuille au départ
                        text=[f"{val:.2f} €" if pd.notna(val) and val != 0 else "" for val in dataFrameAnnuel[col]],
                        textposition='outside',
                        hoverinfo='text',
                        hovertext=[
                            f"Ticker: {col}<br>Montant: {val:.2f} €<br>Nombre de dates de distribution des dividendes: {nbVersementDividendesParAnnee[year][col]}<br>Année: {year}"
                            if pd.notna(val) and val != 0 else ""
                            for year, val in zip(dataFrameAnnuel.index, dataFrameAnnuel[col])
                        ],
                        hoverlabel=dict(
                            bgcolor=colors[j % len(colors)],  # Couleur de fond
                            font=dict(color="white")  # Couleur du texte en blanc
                        ),
                        textfont=dict(color=colors[j % len(colors)], size=12, family="Arial")
                    ))
                    visibility.append(True)  # Ajouter True pour la trace actuelle
                    tracesCount += 1


            # Ajouter False pour les traces suivantes (ajoutées après ce portefeuille)
            visibility += [False] * (len(fig.data) - len(visibility))

            # Ajouter un bouton pour chaque portefeuille avec sa liste de visibilité
            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[{"visible": visibility},
                    {"title": f"Dividende par action"}],
            ))


        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(buttons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        # Mise à jour de la disposition du graphique
        fig.update_layout(
            title=title,
            xaxis=dict(
                title='Années',
                tickmode='array',
                tickvals=dataFrameAnnuel.index,  # Utiliser les années comme valeurs
                ticktext=[str(year) for year in dataFrameAnnuel.index],  # Convertir en chaîne pour l'affichage
                color='white'
            ),
            yaxis=dict(
                title='Montant des dividendes (€)',
                color='white',
                ticksuffix="€",
            ),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
            legend=dict(title="Tickers", font=dict(color='white')),
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "x": 0,
                "xanchor": "left",
                "y": 1,
                "yanchor": "top"
            }]
        )

        return fig
    
    @staticmethod
    def CountDividendsByYear(dataFrame: pd.DataFrame) -> dict:
        """
        Compte le nombre de versements de dividendes pour chaque action par année.

        Args:
            dataFrame (pd.DataFrame): DataFrame contenant des dates comme index et des noms d'entreprises comme colonnes.
                                    Les valeurs représentent les montants de dividendes.

        Returns:
            dict: Dictionnaire avec pour clé l'année, et comme valeur un dictionnaire ayant pour clé le nom de l'action
                et pour valeur le nombre de versements de dividendes.
        """
        assert isinstance(dataFrame, pd.DataFrame), "Le paramètre 'dataFrame' doit être un DataFrame avec des dates en index et des noms d'actions en colonnes."
        assert pd.api.types.is_datetime64_any_dtype(dataFrame.index), "L'index du DataFrame doit être de type datetime."

        # Convertir les index en années pour faciliter l'agrégation
        dataFrame['Year'] = dataFrame.index.year

        # Initialiser le dictionnaire de résultats
        dividendsPerYear = {}

        # Parcourir les années distinctes dans le DataFrame
        for year in dataFrame['Year'].unique():
            # Sélectionner les lignes correspondant à l'année courante
            yearlyData = dataFrame[dataFrame['Year'] == year].drop(columns='Year')

            # Compter les versements de dividendes (les valeurs non nulles ou non nulles et non zéros)
            dividendsPerYear[year] = yearlyData.apply(lambda x: x[x != 0].count(), axis=0).to_dict()

        return dividendsPerYear
    
    