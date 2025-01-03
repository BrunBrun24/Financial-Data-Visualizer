import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


class GraphiqueLigne:
    

    def GraphiqueLineaireEvolutionPatrimoine(self, freq="D"):
        """
        Affiche un graphique interactif avec Plotly montrant l'évolution du patrimoine.
        Un menu déroulant permet de basculer entre les différentes colonnes de patrimoine.
        Les pourcentages de variation sont affichés sous le graphique principal avec une mise en forme colorée.

        Args:
            freq (str): Fréquence de sélection des données (ex: 'D', 'M', 'Y'). Par défaut, 'D' pour quotidien.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({type(self.patrimoine)})"
        assert not self.patrimoine.empty, f"La variable patrimoine doit contenir des colonnes."

        df = self.patrimoine.copy()

        # Remplir les valeurs manquantes pour toutes les colonnes sauf certaines d'entre elles
        colsSauf = df.columns.difference(['Bourse'])
        df[colsSauf] = df[colsSauf].ffill()

        df.sort_index(inplace=True)
        df["Patrimoine"] = df.sum(axis=1)
        dfPourCalulerLePourcentage = df.copy()
        df = self.SelectionnerDates(df, freq)
        
        # On enlève le patrimoine pour pouvoir le remettre avec les données actuelles
        del df["Patrimoine"]
        df["Patrimoine"] = df.sum(axis=1)
        df = self.ReorganiserColonnesParValeurDerniereLigne(df)

        colors = ['rgba(99, 110, 250, 1)', 'rgba(239, 85, 59, 1)', 'rgba(0, 204, 150, 1)', 
                'rgba(171, 99, 250, 1)', 'rgba(255, 161, 90, 1)', 'rgba(25, 211, 243, 1)']

        # Créer la figure
        fig = go.Figure()
        buttons = []

        # Ajouter les traces pour chaque colonne et calculer la plage de dates non nulles
        dateRanges = {}
        for i, livret in enumerate(df.columns):
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[livret],
                mode='lines',
                name=livret,
                line=dict(color=colors[i % len(colors)], width=2),  # Utiliser les couleurs définies
                visible=(i == 0),
                showlegend=False
            ))

            # Définir la ligne de base pour le remplissage
            minValue = df[livret].min()
            baseline = minValue - 250
            if baseline < 0:
                baseline = 0

            # Ajouter la ligne de base (remplissage en dessous)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[baseline] * len(df),
                mode='lines',
                line=dict(color='rgba(0, 0, 0, 0)', width=0),  # Ligne invisible
                fill='tonexty',  # Remplir entre cette ligne et la courbe du patrimoine
                fillcolor=colors[i % len(colors)].replace('1)', '0.2)'),
                showlegend=False,
                visible=(i == 0)
            ))

            # Calculer les dates non nulles
            datesNonNull = df[df[livret] > 0].index
            if not datesNonNull.empty:
                dateRanges[livret] = (datesNonNull.min(), datesNonNull.max())
            else:
                dateRanges[livret] = (df.index.min(), df.index.max())  # Si toutes les valeurs sont nulles

            # Gérer la visibilité pour les courbes et les lignes de base
            visibility = [False] * (2 * len(df.columns))  # 2 traces (courbe et ligne de base) par livret
            visibility[i * 2] = True  # Affiche la courbe correspondante
            visibility[i * 2 + 1] = True  # Affiche la ligne de base correspondante

            # Ajout des annotations spécifiques à chaque livret lors de la sélection
            buttons.append(dict(
                label=livret,
                method='update',
                args=[
                    {'visible': visibility},
                    {
                        'title': f'Evolution du {livret}',
                        'annotations': self.ObtenirAnnotations(dfPourCalulerLePourcentage, livret),
                        'xaxis.range': dateRanges[livret]  # Mise à jour de la plage de dates
                    }
                ]
            ))

        # Ajout des boutons de plage de date
        dateButtons = [
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=5, label="5Y", step="year", stepmode="backward"),
            dict(count=10, label="10Y", step="year", stepmode="backward"),
            dict(step="all", label="Max")
        ]

        # Mise en forme du graphique
        fig.update_layout(
            updatemenus=[
                dict(
                    type='dropdown',
                    buttons=buttons,
                    direction='down',
                    showactive=True,
                )
            ],
            xaxis=dict(
                rangeselector=dict(
                    buttons=dateButtons,
                    x=0,  # Positionnement des boutons à gauche
                    xanchor='left',
                    y=1,  # Sous le titre
                    yanchor='bottom'
                ),
                title='Date',
                type='date'
            ),
            yaxis=dict(
                title='Prix',
                automargin=True,  # Ajoute une marge automatique si nécessaire
                autorange=True,   # Permet l'adaptation dynamique de l'axe Y selon la sélection de date
                tickprefix="€",
            ),
            title=f'Evolution du {df.columns[0]}',
            barmode='group',
            annotations=self.ObtenirAnnotations(dfPourCalulerLePourcentage, df.columns[0]),
            margin=dict(b=150),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig

    def GraphiqueLineaireAera(self, freq="D"):
        """
        Affiche un graphique empilé montrant l'évolution du patrimoine sous forme d'aires empilées.
        Chaque compte est empilé en dessous, en commençant par le compte avec le plus d'argent et en descendant.
        Les couleurs sont fixes et associées correctement à chaque livret, sans afficher la courbe du patrimoine total.

        Args:
            freq (str): Fréquence de sélection des données (ex: 'D', 'M', 'Y'). Par défaut, 'D' pour quotidien.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({type(self.patrimoine)})"
        assert not self.patrimoine.empty, f"La variable patrimoine doit contenir des colonnes."

        df = self.patrimoine.copy()

        # Remplir les valeurs manquantes pour les autres colonnes
        df.ffill(inplace=True)
        df.bfill(inplace=True)

        # Trier les colonnes par valeur finale (ordre décroissant pour l'empilement correct)
        colonnesTriees = df.iloc[-1].sort_values(ascending=False).index.tolist()
        df = df[colonnesTriees]

        # Sélectionner les données selon la fréquence demandée (quotidienne, mensuelle, annuelle...)
        df = self.SelectionnerDates(df, freq)
        df = self.SupprimerValeursRepeteesSpecifiques(df)

        # Définir les couleurs pour chaque colonne avec une transparence ajustée
        colors = [
            'rgba(99, 110, 250, 0.2)',  # Bleu clair
            'rgba(239, 85, 59, 0.2)',   # Rouge clair
            'rgba(0, 204, 150, 0.2)',   # Vert clair
            'rgba(171, 99, 250, 0.2)',  # Violet clair
            'rgba(255, 161, 90, 0.2)',  # Orange clair
            'rgba(25, 211, 243, 0.2)'   # Cyan clair
        ]

        # Tracer le graphique en aires empilées avec Plotly Express
        fig = px.area(
            df,
            x=df.index,
            y=df.columns,
            title="Evolution du patrimoine",
            labels={"value": "Prix (€)", "variable": "Livret", "Date": "Date"},
            template="plotly_white",
            color_discrete_sequence=colors  # Appliquer les couleurs définies
        )

        # Mettre à jour la mise en page
        fig.update_layout(
            xaxis_title=None,
            yaxis=dict(title='Prix (€)', tickprefix="€"),
            margin=dict(b=150),
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig
    
    @staticmethod
    def SupprimerValeursRepeteesSpecifiques(df: pd.DataFrame) -> pd.DataFrame:
        """
        Supprime les valeurs répétées au début de certaines colonnes d'un DataFrame.
        - Pour 'Bourse', remplace toutes les valeurs répétées au début par NaN.

        Args:
            df (pd.DataFrame): Le DataFrame à traiter.

        Returns:
            pd.DataFrame: Le DataFrame modifié avec les premières valeurs répétées remplacées par NaN.
        """
        dfModifie = df.copy()

        # Traiter la colonne 'Bourse'
        column = ['Bourse', "Compte Courant"]
        for col in column:
            if col in dfModifie.columns:
                # Trouver les valeurs répétées au début
                dfBourse = dfModifie[col]
                firstDiff = dfBourse.ne(dfBourse.shift()).cumsum()
                dfModifie[col] = dfBourse.where(firstDiff != 1, 0)

        return dfModifie
    

    
    def ObtenirAnnotations(self, df: pd.DataFrame, livret: str) -> list:
        """
        Génère des annotations pour un graphique Plotly basées sur les pourcentages de variation moyenne mensuelle et annuelle
        pour une colonne spécifique d'un DataFrame. Les annotations indiquent les évolutions en pourcentage avec des couleurs
        différentes selon la tendance (positive ou négative) et s'adaptent dynamiquement à la taille du texte.

        Args:
            df (pd.DataFrame): DataFrame contenant les données de patrimoine pour calculer les pourcentages d'évolution.
            livret (str): Nom de la colonne du DataFrame pour laquelle les pourcentages de variation doivent être calculés.

        Returns:
            list: Liste de dictionnaires représentant les annotations pour Plotly, avec les pourcentages de variation
                et des bordures colorées en fonction de la tendance (positif = vert, négatif = rouge).
        """
        assert isinstance(df, pd.DataFrame), f"La variable patrimoine doit être un DataFrame: ({type(df)})"
        assert isinstance(livret, str), "Le paramètre livret doit être une chaîne de caractères."
        assert livret in df.columns, f"La colonne '{livret}' n'existe pas dans le DataFrame."

        # Pas d'annotations pour "Compte Courant" ou "Bourse"
        if livret in ["Compte Courant", "Bourse"]:
            return []

        # Calculer les pourcentages d'évolution moyenne
        pourcentages = self.CalculEvolutionMoyenneParMois(df[livret])
        annotations = []
        x = 0.472  # Position initiale des annotations sur l'axe x

        # Parcourir les lettres (W, M, Y) et leurs pourcentages respectifs
        for lettre, pourcentage in pourcentages.items():
            # Déterminer la couleur en fonction de la tendance (positive ou négative)
            if pourcentage >= 0:
                color, rgba = 'lightgreen', 'rgba(144, 238, 144, 0.3)'
            else:
                color, rgba = 'lightcoral', 'rgba(255, 99, 71, 0.3)'

            # Ajuster la taille de la police et les marges en fonction de la longueur du texte
            texte = f"{lettre}: {pourcentage:.2f}%"
            tailleTexte = max(13, 12 - len(texte) // 5)  # Ajustement de la taille de police selon la longueur
            annotations.append(
                dict(
                    xref='paper', yref='paper',
                    x=x, y=-0.15,
                    text=texte,
                    showarrow=False,
                    font=dict(size=tailleTexte),  # Taille de police dynamique
                    bordercolor=color,
                    borderwidth=2,
                    bgcolor=rgba,
                    opacity=1,
                    # Marges supplémentaires pour améliorer l'apparence
                    ax=0,
                    ay=0,
                    xanchor="center",  # Centrer le texte
                    yanchor="middle",  # Centrer verticalement
                    align="center",    # Aligner le texte au centre
                )
            )
            x += 0.06  # Espace ajusté dynamiquement entre les annotations

        return annotations
    
    @staticmethod
    def CalculEvolutionMoyenneParMois(patrimoine: pd.Series) -> dict:
        """
        Calcule l'évolution moyenne mensuelle ou annuelle pour la colonne 'Patrimoine' d'une Série.

        Args:
            patrimoine (pd.Series): Série de données avec des dates comme index et des valeurs de patrimoine.

        Returns:
            dict: Dictionnaire contenant deux DataFrames, 'Mois' pour les données mensuelles et 'Année' pour les données annuelles.
        """
        # Vérifier que le paramètre est une Série avec un index de type datetime
        assert isinstance(patrimoine, pd.Series), "Le paramètre patrimoine doit être une pd.Series."
        assert pd.api.types.is_datetime64_any_dtype(patrimoine.index), "L'index de la Série doit être de type datetime."

        # Dictionnaire pour stocker les résultats
        resultats = {}

        for freq in ["M", "Y"]:
            freq += "E"
            # Resampler les données par fréquence et calculer les premiers et derniers jours
            dfPlage = patrimoine.resample(freq).agg(['first', 'last'])
            # Calculer l'évolution moyenne pour chaque période
            dfPlage['EvolutionMoyenne'] = (dfPlage['last'] - dfPlage['first']) / dfPlage['first'] * 100

            resultats[freq] = round(dfPlage["EvolutionMoyenne"].sum(axis=0) / len(dfPlage["EvolutionMoyenne"]), 2)

        return resultats
    