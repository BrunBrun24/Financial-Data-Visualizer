import plotly.graph_objects as go
import pandas as pd

class GraphiqueCirculaire:
    
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
    
