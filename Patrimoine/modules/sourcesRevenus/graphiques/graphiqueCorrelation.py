import plotly.graph_objects as go
import numpy as np
import plotly.figure_factory as ff


class GraphiqueCorrelation:
    
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
        df = df.pct_change(fill_method=None)

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

