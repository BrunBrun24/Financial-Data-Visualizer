import plotly.graph_objects as go
import pandas as pd

class GraphiqueHeatmap:

    @staticmethod
    def GraphiqueHeatmapPourcentageParMois(df: pd.DataFrame) -> go.Figure:
        """
        Crée une heatmap représentant les pourcentages d'évolution mensuels d'un portefeuille
        avec un menu déroulant pour sélectionner la colonne à afficher.

        Args:
            df (pd.DataFrame): DataFrame contenant les pourcentages d'évolution,
                            indexé par date au format 'YYYY-MM'.

        Returns:
            fig (go.Figure): Figure Plotly
        """
        assert isinstance(df, pd.DataFrame), "df doit être un DataFrame"
        assert not df.empty, "Le DataFrame ne doit pas être vide"

        # Convertir l'index en DateTime si ce n'est pas déjà fait
        df.index = pd.to_datetime(df.index)

        # Créer de nouvelles colonnes pour les années et les mois
        df['Année'] = df.index.year
        df['Mois'] = df.index.month_name()

        # Tri des mois pour assurer l'ordre
        moisOrder = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']
        df['Mois'] = pd.Categorical(df['Mois'], categories=moisOrder, ordered=True)

        # Obtenir la liste des colonnes à inclure dans le menu déroulant
        portefeuilleColonnes = [col for col in df.columns if col not in ['Année', 'Mois']]

        # Créer une figure vide
        fig = go.Figure()

        # Ajouter une heatmap pour chaque colonne, en les masquant par défaut sauf la première
        for i, nomColonne in enumerate(portefeuilleColonnes):
            # Pivot du DataFrame pour la colonne courante
            heatmapData = df.pivot_table(index="Année", columns="Mois", values=nomColonne, observed=False).sort_index(ascending=True)

            # Calculer les valeurs minimales et maximales pour la colorisation
            zMin = heatmapData.min().min()
            zMax = heatmapData.max().max()

            # Préparer les valeurs de texte formatées pour les pourcentages
            text_values = heatmapData.apply(lambda col: col.map(lambda x: f'{x:.2f}%' if x != 0 and pd.notnull(x) else ''), axis=0)

            # Ajouter la trace de la heatmap
            fig.add_trace(go.Heatmap(
                z=heatmapData.values,
                x=heatmapData.columns,
                y=heatmapData.index,
                colorscale=[
                    [0, 'rgba(255, 0, 0, 0.7)'],
                    [0.5, 'rgba(144, 238, 144, 1)'],
                    [1, 'rgba(0, 128, 0, 1)']
                ],
                colorbar=dict(title="Pourcentage"),
                zmin=zMin,
                zmax=zMax,
                visible=i == 0,  # Visible uniquement pour la première colonne
                hovertemplate='Mois: %{x}<br>Année: %{y}<br>Pourcentage: %{z:.2f}%<extra></extra>',  # Modifications des étiquettes au survol
                text=text_values.values,  # Pour afficher les valeurs de pourcentage au centre
                texttemplate='%{text}',  # Formatage des valeurs à afficher
                textfont=dict(color='rgba(255, 255, 255, 0.5)'),  # Texte en blanc avec 50% de transparence
            ))

        # Créer le menu déroulant pour sélectionner la colonne
        buttons = []
        for i, nomColonne in enumerate(portefeuilleColonnes):
            buttons.append(dict(
                label=nomColonne,
                method="update",
                args=[{"visible": [j == i for j in range(len(portefeuilleColonnes))]},
                    {"title": f'Evolution mensuelle du portefeuille: {nomColonne}'}]
            ))

        # Configurer le layout de la figure
        fig.update_layout(
            updatemenus=[{
                "buttons": buttons,
                "direction": "down",
                "showactive": True,
                "xanchor": "center",
                "yanchor": "top"
            }],
            title_text=f'Evolution mensuelle du portefeuille: {portefeuilleColonnes[0]}',
            xaxis_title='Mois',
            yaxis_title='Année',
            xaxis=dict(
                tickmode='array',
                tickvals=moisOrder,
                ticktext=moisOrder,
                showgrid=False,
                tickangle=45  # Orientation des étiquettes à 45 degrés
            ),
            yaxis=dict(tickmode='array', tickvals=df['Année'].unique(), showgrid=False),  # Suppression de la grille
            showlegend=False,
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return fig
    
