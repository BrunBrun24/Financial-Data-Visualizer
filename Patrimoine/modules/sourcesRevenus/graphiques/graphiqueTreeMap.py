import plotly.graph_objects as go
import pandas as pd

class GraphiqueTreemap:
    
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
    
    