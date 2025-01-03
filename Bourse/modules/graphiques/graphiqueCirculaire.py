import plotly.graph_objects as go
import pandas as pd

class GraphiqueCirculaire:

    @staticmethod
    def GraphiqueDiagrammeCirculairePortefeuille(portefeuilles: dict) -> go.Figure:
        """
        Génère un diagramme circulaire interactif avec un menu déroulant permettant de sélectionner
        la répartition des actions pour différents portefeuilles, basée sur les valeurs les plus récentes
        disponibles dans chaque DataFrame.

        Args:
            portefeuilles (dict): Dictionnaire où chaque clé est un nom de portefeuille (str),
                                et chaque valeur est un DataFrame contenant les valeurs des actions par entreprise,
                                avec les dates en index.

        Returns:
            go.Figure: Figure Plotly contenant un diagramme circulaire interactif avec un menu déroulant pour la sélection des portefeuilles.
        """
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans 'portefeuilles' doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame doit avoir un index de type datetime."

        # Créer une figure vide
        fig = go.Figure()

        # Itérer à travers chaque portefeuille pour ajouter les données au diagramme circulaire
        for i, (nomPortefeuille, df) in enumerate(portefeuilles.items()):
            assert not df.empty, f"Le DataFrame pour '{nomPortefeuille}' ne doit pas être vide."

            # Sélection des données les plus récentes
            derniere_valeur = df.iloc[-1]
            assert derniere_valeur.notna().all(), f"Le DataFrame pour '{nomPortefeuille}' contient des valeurs manquantes pour la ligne la plus récente."

            # Créer un DataFrame pour le diagramme circulaire
            pie_df = pd.DataFrame({
                'Entreprise': derniere_valeur.index,
                'Valeur': derniere_valeur.values
            })

            # Ajouter le diagramme circulaire pour ce portefeuille
            fig.add_trace(
                go.Pie(
                    labels=pie_df['Entreprise'],
                    values=pie_df['Valeur'],
                    name=nomPortefeuille,
                    visible=(i == 0)  # Seul le premier portefeuille est visible par défaut
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
                args=[
                    {"visible": visible},
                    {"title": f"Répartition des actions pour le portefeuille : {nomPortefeuille}"}
                ]
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
            title_text=f"Répartition des actions pour le portefeuille : {list(portefeuilles.keys())[0]}"
        )

        fig.update_traces(textposition='inside', textinfo='percent+label')

        return fig

    @staticmethod
    def GraphiqueSunburst(portefeuilles: dict) -> go.Figure:
        """
        Génère un graphique Sunburst pour chaque portefeuille spécifié dans le dictionnaire
        et combine tous les graphiques en une seule figure avec un menu déroulant pour sélectionner
        chaque portefeuille.

        Args:
            portefeuilles (dict): Dictionnaire de portefeuilles où chaque clé est un nom de portefeuille (str)
                                et chaque valeur est un DataFrame contenant les valeurs par entreprise avec les
                                dates en index.

        Returns:
            go.Figure: Figure Plotly avec un menu déroulant pour sélectionner les portefeuilles.
        """
        # Vérifications des arguments
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        assert all(isinstance(df, pd.DataFrame) for df in portefeuilles.values()), \
            "Toutes les valeurs dans 'portefeuilles' doivent être des DataFrames."
        assert all(pd.api.types.is_datetime64_any_dtype(df.index) for df in portefeuilles.values()), \
            "Chaque DataFrame doit avoir un index de type datetime."

        # Créer une figure vide
        figCombined = go.Figure()

        # Créer un bouton pour chaque portefeuille
        buttons = []
        for i, (name, df) in enumerate(portefeuilles.items()):
            labels = [name]
            parents = ['']
            values = [df.iloc[-1].sum()]  # Somme des valeurs du dernier jour
            hovertext = [f"{name}<br>Valeur totale: {values[0]:.2f}€"]

            # Ajouter chaque action en tant que catégorie
            totalValeur = df.iloc[-1].sum()
            for ticker, valeur in df.iloc[-1].items():
                # Pour enlever les tickers vendues entièrement
                if valeur != 0:
                    labels.append(ticker)
                    parents.append(name)
                    values.append(valeur)
                    percent = (valeur / totalValeur) * 100
                    hovertext.append(f"{ticker}<br>Valeur: {valeur:.2f}<br>Pourcentage: {percent:.2f}%")

            # Créer une trace Sunburst pour le portefeuille courant
            figCombined.add_trace(go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues='total',
                textinfo='label+percent entry',
                hoverinfo='text',
                hovertext=hovertext,
                insidetextfont=dict(color='white'),  # Texte interne (label + pourcentage) en blanc
                hoverlabel=dict(
                    font=dict(color='white')
                ),
                marker=dict(
                    line=dict(color='white', width=1)  # Ligne de séparation blanche entre les sections
                ),
                visible=(i == 0)  # Rendre visible uniquement le premier portefeuille au départ
            ))

            # Créer un bouton pour ce portefeuille
            buttons.append(
                {
                    'label': name,
                    'method': 'update',
                    'args': [
                        {'visible': [j == i for j in range(len(portefeuilles))]},  # Masquer tous sauf le sélectionné
                        {'title': f'Portefeuille: {name}'}  # Changer le titre
                    ]
                }
            )

        # Configurer le menu déroulant dans la figure combinée
        figCombined.update_layout(
            updatemenus=[{
                'buttons': buttons,
                'direction': 'down',
                'showactive': True,
            }],
            title_text=f'Sélectionnez un portefeuille',
            showlegend=False,
            margin=dict(l=30, r=30, t=50, b=50),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )

        return figCombined

