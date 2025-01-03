import plotly.graph_objects as go
import pandas as pd

class GraphiqueLigne:

    @staticmethod
    def GraphiqueLineairePortefeuilles(df: pd.DataFrame, title="", suffixe: str="") -> go.Figure:
        """
        Génère un graphique linéaire interactif avec Plotly, basé sur les données contenues dans un DataFrame.
        Pour chaque colonne de `df`, une courbe distincte est tracée, permettant de visualiser l'évolution des
        séries de données dans le temps. Le graphique est coloré de manière esthétique avec une palette de couleurs
        prédéfinie, et le fond est personnalisé pour une meilleure lisibilité.

        Args:
            df (pd.DataFrame): DataFrame contenant les données à tracer. Les colonnes représentent différentes séries de données.
            title (str): Titre du graphique.
            suffixe (str): Suffixe à ajouté sur l'axe des ordonnées.

        Returns:
            go.Figure: Le graphique Plotly
        """
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame: ({type(df)})"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(suffixe, str), f"devise doit être une chaîne de caractères: ({type(suffixe)})"

        fig = go.Figure()
        colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        for i, column in enumerate(df.columns):
            colorIndex = i % len(colors)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                mode='lines',
                name=column,
                line=dict(color=colors[colorIndex], width=2.5),
                hovertemplate=f'Ticker: {column}<br>' + 'Date: %{x}<br>Pourcentage: %{y:.2f}' + suffixe + '<extra></extra>'
            ))

        fig.update_layout(
            title=title,
            xaxis=dict(
                title='Date',
                titlefont=dict(size=14, color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                title='Valeur en %',
                titlefont=dict(size=14, color='white'),
                ticksuffix=suffixe,
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
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig

    @staticmethod
    def GraphiqueLineaireTickers(dataDict: dict, title="", suffixe: str="") -> go.Figure:
        """
        Génère un graphique linéaire interactif avec Plotly, permettant de visualiser l'évolution des
        données pour différents portefeuilles et tickers. Chaque portefeuille est représenté par un
        DataFrame dans le dictionnaire d'entrée, et un menu déroulant permet de sélectionner le portefeuille
        à afficher.

        Args:
            dataDict (dict): Dictionnaire contenant des DataFrames. La clé représente le nom du portefeuille,
                            et chaque DataFrame contient les données à tracer, avec les dates en index et
                            les tickers en colonnes.
            title (str): Titre du graphique.
            suffixe (str): Suffixe à ajouté sur l'axe des ordonnées.

        Returns:
            go.Figure: Le graphique Plotly avec un menu déroulant pour la sélection des portefeuilles.
        """
        assert isinstance(dataDict, dict), f"dataDict doit être un dictionnaire: ({type(dataDict)})"
        assert all(isinstance(df, pd.DataFrame) for df in dataDict.values()), "Chaque valeur de dataDict doit être un DataFrame"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(suffixe, str), f"devise doit être une chaîne de caractères: ({type(suffixe)})"

        fig = go.Figure()
        colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00', '#8b008b'
        ]

        # Ajout de chaque portefeuille comme une option du menu déroulant
        dropdownButtons = []
        tracesCount = 0  # Compte du nombre total de traces ajoutées
        for portfolioIndex, (portfolioName, df) in enumerate(dataDict.items()):
            # On trie le dataFrame pour récupérer les tickers qui ne sont pas clôturés
            dfFiltré = df.loc[:, df.iloc[-1].notna()]
            visibility = [False] * len(fig.data)
            # Création des courbes pour chaque ticker de ce portefeuille
            for i, column in enumerate(dfFiltré.columns):
                colorIndex = i % len(colors)
                fig.add_trace(go.Scatter(
                    x=dfFiltré.index,
                    y=dfFiltré[column],
                    mode='lines',
                    name=f"{column}",
                    line=dict(color=colors[colorIndex], width=1.5),
                    hovertemplate=f'Ticker: {column}<br>' + 'Date: %{x}<br>Pourcentage: %{y:.2f}' + suffixe + '<extra></extra>',
                    visible=(portfolioIndex == 0)  # Visible uniquement pour le premier portefeuille
                ))
                visibility.append(True)  # Ajouter True pour la trace actuelle
                tracesCount += 1

            # Ajouter False pour les traces suivantes (ajoutées après ce portefeuille)
            visibility += [False] * (len(fig.data) - len(visibility))

            dropdownButtons.append(dict(
                label=portfolioName,
                method="update",
                args=[{"visible": visibility},
                    {"title": f"{title} - {portfolioName}"}]
            ))

        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(dropdownButtons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        # Configuration du layout et des menus déroulants
        fig.update_layout(
            title=title + f" - {next(iter(dataDict))}",
            updatemenus=[{
                "buttons": dropdownButtons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            xaxis=dict(
                titlefont=dict(size=14, color='white'),
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            yaxis=dict(
                titlefont=dict(size=14, color='white'),
                ticksuffix=suffixe,
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig

