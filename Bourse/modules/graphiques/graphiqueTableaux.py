import plotly.graph_objects as go
import pandas as pd

class GraphiqueTableaux:

    @staticmethod
    def GraphiqueTableauPortefeuille(df: pd.DataFrame) -> go.Figure:
        """
        Génère une figure Plotly affichant un tableau contenant les données d'un portefeuille,
        avec un menu déroulant permettant de sélectionner le portefeuille souhaité parmi les colonnes du DataFrame.

        Args:
            df (pd.DataFrame): DataFrame contenant les données des portefeuilles avec les dates en index et
                            les noms de portefeuilles en colonnes.

        Returns:
            go.Figure: Figure Plotly contenant un tableau des données du portefeuille sélectionné,
                    avec un menu déroulant pour sélectionner le portefeuille.
        """
        # Vérification des types des arguments
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame."

        # Formatage de l'index de dates en 'YYYY-MM-DD'
        df.index = df.index.strftime('%Y-%m-%d')

        # Création des traces pour chaque portefeuille
        figures_data = []
        for portefeuille in df.columns:
            # Création de la table pour le portefeuille sélectionné
            figures_data.append(
                go.Table(
                    header=dict(values=['Date', portefeuille],
                                fill_color='paleturquoise',
                                align='left'),
                    cells=dict(values=[df.index, df[portefeuille].tolist()],
                            fill_color='lavender',
                            align='left')
                )
            )

        # Création de la figure avec la première vue par défaut
        fig = go.Figure(data=[figures_data[0]])

        # Création du menu déroulant
        buttons = [
            dict(label=portefeuille,
                method="update",
                args=[{"data": [figures_data[i]]},
                    {"title": f"Tableau des données pour le portefeuille : {portefeuille}"}])
            for i, portefeuille in enumerate(df.columns)
        ]

        # Mise à jour de la disposition pour inclure le menu
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "x": 0.5,
                "y": 1.15,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title=f"Tableau des données pour le portefeuille : {df.columns[0]}"
        )

        return fig
    
