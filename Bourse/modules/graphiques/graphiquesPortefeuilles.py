from .graphiquesBase import GraphiquesBase

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd

class GraphiquesPortefeuilles(GraphiquesBase):

    def CreateSunburst(self, nomPortefeuille: str, df: pd.DataFrame) -> go.Sunburst:
        """
        Crée un graphique Sunburst pour un portefeuille donné.

        Args:
            nomPortefeuille (str): Nom du portefeuille.
            df (pd.DataFrame): Données du portefeuille.

        Returns:
            go.Sunburst: Objet Sunburst de Plotly.
        """
        assert isinstance(nomPortefeuille, str), "nomPortefeuille doit être une chaîne de caractères."
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame."
        assert not df.empty, "df ne doit pas être vide."

        labelsSunburst = [nomPortefeuille]
        parentsSunburst = ['']
        valuesSunburst = [df.iloc[-1].sum()]
        hovertextSunburst = [f"{nomPortefeuille}<br>Valeur totale: {valuesSunburst[0]:,.2f}€"]

        for ticker, valeur in df.iloc[-1].items():
            if valeur != 0:
                labelsSunburst.append(ticker)
                parentsSunburst.append(nomPortefeuille)
                valuesSunburst.append(valeur)
                percentSunburst = (valeur / valuesSunburst[0]) * 100
                hovertextSunburst.append(
                    f"{ticker}<br>Valeur: {valeur:.2f}€<br>Pourcentage: {percentSunburst:.2f}%"
                )

        return go.Sunburst(
            labels=labelsSunburst,
            parents=parentsSunburst,
            values=valuesSunburst,
            branchvalues='total',
            hovertext=hovertextSunburst,
            textinfo='label+percent entry',
            hoverinfo='text',
            insidetextfont=dict(color='white'),
            marker=dict(line=dict(color='white', width=1))
        )

    def CreateTreemap(self, df: pd.DataFrame) -> go.Treemap:
        """
        Crée un graphique Treemap pour un portefeuille donné.

        Args:
            df (pd.DataFrame): Données du portefeuille.

        Returns:
            go.Treemap: Objet Treemap de Plotly.
        """
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame."
        assert not df.empty, "df ne doit pas être vide."

        derniereValeur = df.iloc[-1]
        valeurTotale = derniereValeur.sum()
        treemapDf = pd.DataFrame({
            'Entreprise': derniereValeur.index,
            'Valeur': derniereValeur.values,
            'Pourcentage': (derniereValeur / valeurTotale * 100).round(2)
        })
        treemapDf['text'] = treemapDf.apply(
            lambda row: f"{row['Entreprise']}<br>Répartition: {row['Pourcentage']:.2f}%<br>Valeur: {row['Valeur']:.2f}€",
            axis=1
        )

        return go.Treemap(
            labels=treemapDf['Entreprise'],
            parents=[''] * len(treemapDf),
            values=treemapDf['Valeur'],
            text=treemapDf['text'],
            textinfo='text',
            hoverinfo='skip',
            insidetextfont=dict(color='white'),
            marker=dict(line=dict(color='white', width=1))
        )

    def CreateHeatmap(self, nomPortefeuille: str, pourcentageMensuel: pd.DataFrame) -> go.Heatmap:
        """
        Crée un graphique Heatmap pour un portefeuille donné.

        Args:
            nomPortefeuille (str): Nom du portefeuille.
            pourcentageMensuel (pd.DataFrame): Données des pourcentages mensuels.

        Returns:
            go.Heatmap: Objet Heatmap de Plotly.
        """
        assert isinstance(nomPortefeuille, str), "nomPortefeuille doit être une chaîne de caractères."
        assert isinstance(pourcentageMensuel, pd.DataFrame), "pourcentageMensuel doit être un DataFrame."
        assert not pourcentageMensuel.empty, "pourcentageMensuel ne doit pas être vide."

        heatmapData = pourcentageMensuel.pivot_table(
            index="Année", columns="Mois", values=nomPortefeuille, observed=False
        ).sort_index(ascending=True)

        return go.Heatmap(
            z=heatmapData.values,
            x=heatmapData.columns,
            y=heatmapData.index,
            zmin=heatmapData.min().min(),
            zmax=heatmapData.max().max(),
            colorscale=[
                [0, 'rgba(255, 0, 0, 0.7)'],
                [0.5, 'rgba(144, 238, 144, 1)'],
                [1, 'rgba(0, 128, 0, 1)']
            ],
            hovertemplate='Mois: %{x}<br>Année: %{y}<br>Pourcentage: %{z:.2f}%<extra></extra>',
            text=heatmapData.apply(lambda col: col.map(lambda x: f'{x:.2f}%' if x != 0 and pd.notnull(x) else ''), axis=0).values,
            texttemplate='%{text}', 
            textfont=dict(color='rgba(255, 255, 255, 0.5)'),  # Texte en blanc avec 50% de transparence
        )

    def GraphiqueCombineSunburstTreemapHeatmap(self, portefeuilles: dict, pourcentageMensuel: pd.DataFrame, cash: pd.DataFrame, width=1600, height=1200) -> go.Figure:
        """
        Génère une figure combinée avec trois graphiques :
        - Sunburst à gauche (haut).
        - Treemap à droite (haut).
        - Heatmap en dessous.
        Tous les graphiques sont synchronisés avec un menu déroulant unique pour sélectionner un portefeuille.

        Args:
            portefeuilles (dict): Dictionnaire contenant les portefeuilles avec les valeurs d'actions par entreprise.
            pourcentageMensuel (pd.DataFrame): DataFrame contenant les pourcentages d'évolution mensuels indexés par date.
            cash (pd.DataFrame): DataFrame contenant les valeurs de cash par portefeuille.
            width (int): Largeur totale de la figure.
            height (int): Hauteur totale de la figure.

        Returns:
            go.Figure: Figure Plotly combinée.
        """
        # Vérifications des arguments
        assert isinstance(portefeuilles, dict), "portefeuilles doit être un dictionnaire."
        assert isinstance(pourcentageMensuel, pd.DataFrame), "pourcentageMensuel doit être un DataFrame."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans portefeuilles doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame dans portefeuilles doit avoir un index de type datetime."
        assert isinstance(cash, pd.DataFrame), "cash doit être un DataFrame."

        # Convertir l'index de pourcentageMensuel en DateTime et préparer les données
        pourcentageMensuel.index = pd.to_datetime(pourcentageMensuel.index)
        pourcentageMensuel['Année'] = pourcentageMensuel.index.year
        pourcentageMensuel['Mois'] = pourcentageMensuel.index.month_name()
        moisOrder = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']
        pourcentageMensuel['Mois'] = pd.Categorical(pourcentageMensuel['Mois'], categories=moisOrder, ordered=True)

        # Créer une figure avec trois sous-parcelles
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{'type': 'domain'}, {'type': 'domain'}], [{'colspan': 2}, None]],
            row_heights=[0.5, 0.5],
            column_widths=[0.5, 0.5],
            subplot_titles=["", "", "Évolution mensuelle en TWR"],
            horizontal_spacing=0.05,
            vertical_spacing=0.1
        )

        # Boutons du menu déroulant
        buttons = []
        allTracesVisibility = []  # Stocke la visibilité globale des traces

        # Ajouter les graphiques pour chaque portefeuille
        for i, (nomPortefeuille, df) in enumerate(portefeuilles.items()):
            df["Cash"] = cash[nomPortefeuille]

            # Ajouter le graphique Sunburst
            sunburst = self.CreateSunburst(nomPortefeuille, df)
            fig.add_trace(sunburst, row=1, col=1)

            # Ajouter le graphique Treemap
            treemap = self.CreateTreemap(df)
            fig.add_trace(treemap, row=1, col=2)

            # Ajouter le graphique Heatmap
            heatmap = self.CreateHeatmap(nomPortefeuille, pourcentageMensuel)
            fig.add_trace(heatmap, row=2, col=1)

            # Configurer la visibilité des graphiques pour le menu déroulant
            visible = [False] * (3 * len(portefeuilles))
            visible[3 * i] = True  # Sunburst
            visible[3 * i + 1] = True  # Treemap
            visible[3 * i + 2] = True  # Heatmap

            allTracesVisibility.extend(visible if i == 0 else [False] * 3)  # Par défaut, seul le premier portefeuille est visible

            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[{"visible": visible}]
            ))

        # Configuration spécifique pour les graphiques Heatmap
        fig.update_layout(
            xaxis=dict(
                title_text='Mois',
                tickmode='array',
                tickvals=moisOrder,
                ticktext=moisOrder,
                showgrid=False,
                tickangle=45
            ),
            yaxis=dict(
                title_text='Année',
                tickmode='array',
                tickvals=pourcentageMensuel['Année'].unique(),
                showgrid=False
            ),
            showlegend=False
        )

        # Configurer la figure principale
        super().GenerateGraph(fig)
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            width=width,
            height=height,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        # Appliquer la visibilité par défaut pour le premier portefeuille
        for trace, visibility in zip(fig.data, allTracesVisibility):
            trace.visible = visibility

        return fig


    def GraphiqueLineairePortefeuillesMonnaie(self, dfPrix: pd.DataFrame, dfArgentInvestis: pd.DataFrame, title="", width=1600, height=650) -> go.Figure:
        """
        Génère un graphique linéaire interactif avec Plotly, basé sur les données contenues dans un DataFrame.
        Pour chaque colonne de `df`, une courbe distincte est tracée, permettant de visualiser l'évolution des
        séries de données dans le temps. Le graphique est coloré de manière esthétique avec une palette de couleurs
        prédéfinie, et le fond est personnalisé pour une meilleure lisibilité.

        Args:
            dfPrix (pd.Series): Series contenant les données à tracer.
            title (str): Titre du graphique.
            suffixe (str): Suffixe à ajouté sur l'axe des ordonnées.
            width (int, optional): Largeur du graphique. Default 1600.
            height (int, optional): Hauteur du graphique. Default 650.

        Returns:
            go.Figure: Le graphique Plotly
        """
        assert isinstance(dfPrix, pd.DataFrame), f"dfPrix doit être un DataFrame: ({type(dfPrix)})"
        assert isinstance(dfArgentInvestis, pd.Series), f"dfArgentInvestis doit être une Series: ({type(dfArgentInvestis)})"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(width, int), f"width doit être un entier: ({type(width)})"
        assert isinstance(height, int), f"height doit être un entier: ({type(height)})"

        fig = go.Figure()
        colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        for i, column in enumerate(dfPrix.columns):
            colorIndex = i % len(colors)
            fig.add_trace(go.Scatter(
                x=dfPrix.index,
                y=dfPrix[column],
                mode='lines',
                name=column,
                line=dict(color=colors[colorIndex], width=2.5),
                hovertemplate=f'Ticker: {column}<br>' + 'Date: %{x}<br>Prix: %{y:.2f}' + '<extra></extra>'
            ))

        # Ajout de la ligne en pointillé pour les montants investis
        fig.add_trace(go.Scatter(
            x=dfArgentInvestis.index,
            y=dfArgentInvestis,
            mode='lines',
            name="Montants Investis",
            line=dict(color='white', width=2.5, dash='dot'),  # Pointillé et blanc pour bien contraster
            opacity=0.5, 
            hovertemplate='Date: %{x}<br>Montant Investi: %{y:.2f} €<extra></extra>'
        ))

        super().GenerateGraph(fig)
        fig.update_layout(
            xaxis=dict(
                title='Date',
                titlefont=dict(size=14, color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                title='Valeur en %',
                titlefont=dict(size=14, color='white'),
                ticksuffix="€",
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                x=0.01, y=0.99,
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            title=title,
            width=width,
            height=height,
        )

        return fig

    def GraphiqueDfPourcentageMonnaie(self, dfPourcentage: pd.DataFrame, dfMonnaie: pd.DataFrame, title="", width=1600, height=650) -> go.Figure:
        """
        Génère un graphique interactif avec Plotly, basé sur deux DataFrames. L'un contient l'évolution en pourcentage,
        l'autre l'évolution en monnaie. Chaque courbe représente une série, avec un affichage enrichi des informations
        lors du survol : date, évolution en pourcentage et évolution en monnaie.

        Args:
            dfPourcentage (pd.DataFrame): DataFrame contenant l'évolution en pourcentage des données.
            dfMonnaie (pd.DataFrame): DataFrame contenant l'évolution en monnaie des données.
            title (str): Titre du graphique.
            width (int): Largeur du graphique.
            height (int): Hauteur du graphique.

        Returns:
            go.Figure: Le graphique Plotly généré.
        """
        # Assertions pour vérifier les paramètres
        assert isinstance(dfPourcentage, pd.DataFrame), f"dfPourcentage doit être un DataFrame : ({type(dfPourcentage)})"
        assert isinstance(dfMonnaie, pd.DataFrame), f"dfMonnaie doit être un DataFrame : ({type(dfMonnaie)})"
        assert isinstance(title, str), f"title doit être une chaîne de caractères : ({type(title)})"
        assert isinstance(width, int), f"width doit être un entier: ({type(width)})"
        assert isinstance(height, int), f"height doit être un entier: ({type(height)})"
        assert dfPourcentage.columns.equals(dfMonnaie.columns), "Les colonnes des deux DataFrames doivent être identiques."
        assert dfPourcentage.index.equals(dfMonnaie.index), "Les index des deux DataFrames doivent être identiques."

        fig = go.Figure()
        colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        for i, column in enumerate(dfPourcentage.columns):
            colorIndex = i % len(colors)
            fig.add_trace(go.Scatter(
                x=dfPourcentage.index,
                y=dfPourcentage[column],
                mode='lines',
                name=column,
                line=dict(color=colors[colorIndex], width=2.5),
                customdata=dfMonnaie[column].values,  # Ajout des données pour le hovertemplate
                hovertemplate=f'Ticker: {column}<br>' +
                            'Date: %{x}<br>' +
                            'Pourcentage: %{y:.2f}%<br>' +
                            'Prix: %{customdata:,.2f}€<extra></extra>'
            ))

        super().GenerateGraph(fig)
        fig.update_layout(
            xaxis=dict(
                title='Date',
                titlefont=dict(size=14, color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                title='Valeur en %',
                titlefont=dict(size=14, color='white'),
                ticksuffix="%",
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                x=0.01, y=0.99,
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            title=title,
            width=width,
            height=height,
        )

        return fig

