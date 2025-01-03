import plotly.graph_objects as go
import pandas as pd

class GraphiqueTreemap:

    @staticmethod
    def GraphiqueTreemapPortefeuille(portefeuilles: dict) -> go.Figure:
        """
        Génère un treemap interactif avec un menu déroulant pour sélectionner la répartition des actions
        dans différents portefeuilles basés sur les valeurs les plus récentes.

        Args:
            portefeuilles (dict): Dictionnaire où chaque clé est un nom de portefeuille (str)
                                et la valeur est un DataFrame contenant les valeurs des actions par entreprise
                                avec les dates en index.

        Returns:
            fig (go.Figure): Figure Plotly avec menu déroulant.
        """
        assert isinstance(portefeuilles, dict), "portefeuilles doit être un dictionnaire."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans portefeuilles doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame dans portefeuilles doit avoir un index de type datetime."

        # Créer une figure vide
        fig = go.Figure()

        # Itérer à travers chaque portefeuille pour ajouter les données au treemap
        for i, (nomPortefeuille, df) in enumerate(portefeuilles.items()):
            # Sélection des données les plus récentes
            derniere_valeur = df.iloc[-1]

            # Calcul de la valeur totale du portefeuille
            valeurTotale = derniere_valeur.sum()

            # Créer un DataFrame pour le treemap avec les pourcentages calculés
            treemapDf = pd.DataFrame({
                'Entreprise': derniere_valeur.index,
                'Valeur': derniere_valeur.values,
                'Pourcentage': (derniere_valeur / valeurTotale * 100).round(2)  # Calculer le pourcentage avec 2 décimales
            })

            # Ajouter une colonne texte avec des informations formatées
            treemapDf['text'] = treemapDf.apply(
                lambda row: f"{row['Entreprise']}<br>Répartition: {row['Pourcentage']:.2f}% <br>Valeur: {row['Valeur']:.2f}", axis=1
            )

            # Ajouter le treemap pour ce portefeuille
            fig.add_trace(
                go.Treemap(
                    labels=treemapDf['Entreprise'],
                    parents=[''] * len(treemapDf),
                    values=treemapDf['Valeur'],
                    visible=(i == 0),  # Seul le premier portefeuille est visible par défaut
                    text=treemapDf['text'],
                    textinfo='text',  # Utiliser les informations formatées comme texte
                    insidetextfont=dict(color='white'),  # Texte des labels en blanc
                    marker=dict(
                        line=dict(color='white', width=1)  # Bordure blanche autour des sections
                    ),
                    hoverlabel=dict(
                        font=dict(color='white')  # Texte au survol en blanc
                    ),
                    hovertemplate=(
                        "<b>%{label}</b><br>" +
                        "Répartition: %{customdata[0]:.2f}%" +  # Affiche le pourcentage avec 2 décimales
                        "Valeur: %{value:.2f}<br>"  # Affiche la valeur avec 2 décimales
                    ),
                    customdata=treemapDf[['Pourcentage']].values  # Passer les pourcentages comme données de survol
                )
            )

        # Créer les boutons du menu déroulant
        buttons = []
        for i, nomPortefeuille in enumerate(portefeuilles.keys()):
            # Créer un bouton pour chaque portefeuille
            visible = [False] * len(portefeuilles)
            visible[i] = True
            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[{"visible": visible},
                    {"title": f'Répartition des actions pour le portefeuille: {nomPortefeuille}'}]
            ))

        # Mise à jour de la mise en page avec le menu déroulant
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title_text=f'Répartition des actions pour le portefeuille: {list(portefeuilles.keys())[0]}',
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    
