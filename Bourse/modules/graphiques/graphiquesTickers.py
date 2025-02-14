from .graphiquesBase import GraphiquesBase

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import numpy as np

class GraphiquesTickers(GraphiquesBase):
    
    def __init__(self):
        self.colors = [
            '#ff00ff', '#00ffff', '#00ff7f', '#ff0000', '#0000ff', '#ffff00', '#ff1493', '#ff8c00',
            '#8a2be2', '#ff69b4', '#7cfc00', '#20b2aa', '#32cd32', '#ff6347', '#adff2f', '#00fa9a',
            '#dc143c', '#7fffd4', '#ff8c69', '#00ced1', '#8b0000', '#228b22', '#ff4500', '#da70d6',
            '#00bfff', '#ff7f50', '#9acd32', '#00ff00'
        ]
    
    # Linéaire
    def GraphiqueLineaireTickersPourcentageDevise(self, dataPourcentage: dict, dataDevise: dict, title="", width=1600, height=650) -> go.Figure:
        """
        Génère un graphique linéaire interactif avec un menu déroulant permettant de visualiser les performances en pourcentage
        et les prix de différents tickers dans plusieurs portefeuilles.

        Args:
            dataPourcentage (dict): Dictionnaire où les clés sont les noms des portefeuilles et les valeurs sont des DataFrames contenant les performances en pourcentage des tickers.
                                    Chaque colonne représente un ticker, et chaque ligne correspond à une date.
            dataDevise (dict): Dictionnaire où les clés sont les noms des portefeuilles et les valeurs sont des DataFrames contenant les prix des tickers correspondants.
                            Chaque colonne représente un ticker, et chaque ligne correspond à une date.
            title (str): Titre du graphique. Par défaut, une chaîne vide.
            width (int): Largeur du graphique en pixels. Par défaut, 1600.
            height (int): Hauteur du graphique en pixels. Par défaut, 650.

        Returns:
            go.Figure: Objet Figure de Plotly représentant le graphique interactif.
        """
        assert isinstance(dataPourcentage, dict), f"dataPourcentage doit être un dictionnaire: ({type(dataPourcentage)})"
        assert all(isinstance(df, pd.DataFrame) for df in dataPourcentage.values()), "Chaque valeur de dataPourcentage doit être un DataFrame"
        assert isinstance(dataDevise, dict), f"dataDevise doit être un dictionnaire: ({type(dataDevise)})"
        assert all(isinstance(df, pd.DataFrame) for df in dataDevise.values()), "Chaque valeur de dataDevise doit être un DataFrame"
        assert dataPourcentage.keys() == dataDevise.keys(), "Les clés de dataPourcentage et dataDevise doivent correspondre"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(width, int) and width > 0, f"width doit être un entier positif: ({width})"
        assert isinstance(height, int) and height > 0, f"height doit être un entier positif: ({height})"

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
        for portfolioIndex, (portfolioName, df) in enumerate(dataPourcentage.items()):
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
                    customdata=dataDevise[portfolioName][column].values,  # Ajout des données pour le hovertemplate
                    hovertemplate=f'Ticker: {column}<br>' + 
                                    'Date: %{x}<br>' + 
                                    'Pourcentage: %{y:.2f}%<br>' + 
                                    'Prix: %{customdata:,.2f}€<extra></extra>',
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
                    {"title": f"{title}"}]
            ))

        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(dropdownButtons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        super().GenerateGraph(fig)
        # Configuration du layout et des menus déroulants
        fig.update_layout(
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
                ticksuffix="%",
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            title=title,
            width=width,
            height=height,
        )

        return fig

    def GraphiqueLineaireTickersDevise(self, dataDict: dict, title="", width=1600, height=650) -> go.Figure:
        """
        Génère un graphique linéaire interactif avec Plotly, permettant de visualiser l'évolution des
        prix de différents tickers dans plusieurs portefeuilles. Chaque portefeuille est représenté par un
        DataFrame dans le dictionnaire d'entrée, et un menu déroulant permet de sélectionner le portefeuille
        à afficher.

        Args:
            dataDict (dict): Dictionnaire contenant des DataFrames. La clé représente le nom du portefeuille,
                            et chaque DataFrame contient les données à tracer, avec les dates en index et
                            les tickers en colonnes.
            title (str): Titre du graphique. Par défaut, une chaîne vide.
            width (int): Largeur du graphique en pixels. Par défaut, 1600.
            height (int): Hauteur du graphique en pixels. Par défaut, 650.

        Returns:
            go.Figure: Le graphique Plotly interactif avec un menu déroulant pour sélectionner les portefeuilles.
        """
        assert isinstance(dataDict, dict), f"dataDict doit être un dictionnaire: ({type(dataDict)})"
        assert all(isinstance(df, pd.DataFrame) for df in dataDict.values()), "Chaque valeur de dataDict doit être un DataFrame"
        assert isinstance(title, str), f"title doit être une chaîne de caractères: ({type(title)})"
        assert isinstance(width, int) and width > 0, f"width doit être un entier positif: ({width})"
        assert isinstance(height, int) and height > 0, f"height doit être un entier positif: ({height})"

        fig = go.Figure()
        colors = self.colors

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
                    hovertemplate=f'Ticker: {column}<br>' + 'Date: %{x}<br>Prix: %{y:.2f}€' + '<extra></extra>',
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
                    {"title": f"{title}"}]
            ))

        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(dropdownButtons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        super().GenerateGraph(fig)
        # Configuration du layout et des menus déroulants
        fig.update_layout(
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
                ticksuffix="€",
                tickfont=dict(color='white'),
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(255,255,255,0.3)',
                font=dict(color='white')
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            title=title,
            width=width,
            height=height,
        )

        return fig
    
    
    @staticmethod
    def CreateLineaireTickerPourcentageDevise(nameTicker: str, dataPourcentage: pd.Series, dataDevise: pd.Series, color: str) -> go.Scatter:
        """
        Crée une courbe linéaire pour un ticker donné, représentant son évolution en pourcentage, 
        avec des informations supplémentaires sur les prix affichées dans le hovertemplate.

        Args:
            nameTicker (str): Nom du ticker à afficher.
            dataPourcentage (pd.Series): Série contenant les valeurs en pourcentage à tracer (l'axe des ordonnées).
            dataDevise (pd.Series): Série contenant les valeurs de prix associées pour les données du ticker.
            color (str): Couleur de la ligne du graphique.

        Returns:
            go.Scatter: Objet Plotly Scatter représentant la courbe linéaire du ticker.
        """
        # Assertions pour valider les types des arguments
        assert isinstance(nameTicker, str), f"nameTicker doit être une chaîne de caractères: ({type(nameTicker)})"
        assert isinstance(dataPourcentage, pd.Series), f"dataPourcentage doit être une série Pandas: ({type(dataPourcentage)})"
        assert isinstance(dataDevise, pd.Series), f"dataDevise doit être une série Pandas: ({type(dataDevise)})"
        assert len(dataPourcentage) == len(dataDevise), "dataPourcentage et dataDevise doivent avoir la même longueur"
        assert isinstance(color, str), f"color doit être une chaîne de caractères: ({type(color)})"

        # Création et retour de la courbe linéaire
        return go.Scatter(
            x=dataPourcentage.index,
            y=dataPourcentage,
            mode='lines',
            name=f"{nameTicker}",
            line=dict(color=color, width=2.5),
            customdata=dataDevise.values,  # Ajout des données pour le hovertemplate
            hovertemplate=f'Ticker: {nameTicker}<br>' + 
                            'Date: %{x}<br>' + 
                            'Pourcentage: %{y:.2f}%<br>' + 
                            'Prix: %{customdata:,.2f}€<extra></extra>',
        )

    @staticmethod
    def CreateLineaireCoursTicker(nameTicker: str, prixTicker: pd.Series, prixFifoTicker: pd.Series, 
                                  fondsInvestisTicker: pd.Series, montantsInvestisTicker: pd.Series, montantsVentesTickers: pd.Series, 
                                  dataPourcentage: pd.Series, color: str) -> list[go.Scatter]:
        """
        Crée plusieurs traces Scatter représentant les informations financières d'un ticker, incluant son prix, 
        son prix FIFO, les fonds investis, et les points d'investissements et de ventes sur des dates clés.

        Args:
            nameTicker (str): Nom du ticker.
            prixTicker (pd.Series): Série contenant les prix du ticker sur une période donnée (axe des ordonnées).
            prixFifoTicker (pd.Series): Série contenant les prix FIFO (premier entré, premier sorti) associés au ticker.
            fondsInvestisTicker (pd.Series): Série contenant les fonds investis pour le ticker.
            montantsInvestisTicker (pd.Series): Série des montants investis avec les dates correspondantes comme index.
            montantsVentesTickers (pd.Series): Série des montants vendus avec les dates correspondantes comme index.
            dataPourcentage (pd.Series): Série contenant les pourcentages associés au ticker.
            color (str): Couleur pour la ligne principale du prix du ticker.

        Returns:
            list[go.Scatter]: Liste contenant quatre traces Scatter pour le graphique :
                            - Prix du ticker
                            - Prix FIFO
                            - Points d'investissements
                            - Points de ventes
        """
        assert isinstance(nameTicker, str), "nameTicker doit être une chaîne de caractères"
        assert isinstance(prixTicker, pd.Series), "prixTicker doit être une série Pandas"
        assert isinstance(prixFifoTicker, pd.Series), "prixFifoTicker doit être une série Pandas"
        assert isinstance(fondsInvestisTicker, pd.Series), "fondsInvestisTicker doit être une série Pandas"
        assert isinstance(montantsInvestisTicker, pd.Series), "montantsInvestisTicker doit être une série Pandas"
        assert isinstance(montantsVentesTickers, pd.Series), "montantsVentesTickers doit être une série Pandas"
        assert isinstance(dataPourcentage, pd.Series), "dataPourcentage doit être une série Pandas"
        assert isinstance(color, str), "color doit être une chaîne de caractères"
        assert len(prixTicker) > 0, "prixTicker ne doit pas être vide"
        assert len(prixFifoTicker) == len(prixTicker), "prixFifoTicker doit avoir la même longueur que prixTicker"
        assert len(fondsInvestisTicker) == len(prixTicker), "fondsInvestisTicker doit avoir la même longueur que prixTicker"
        assert all(montantsInvestisTicker.index.isin(prixTicker.index)), "Les dates de montantsInvestisTicker doivent exister dans prixTicker"
        assert all(montantsVentesTickers.index.isin(prixTicker.index)), "Les dates de montantsVentesTickers doivent exister dans prixTicker"

        # Tracé pour les prix du ticker
        tracePrix = go.Scatter(
            x=prixTicker.index,
            y=prixTicker,
            mode='lines',
            name=f"{nameTicker} - Prix",
            line=dict(color=color, width=2.5),
            customdata=fondsInvestisTicker.values,
            hovertemplate=f'Ticker: {nameTicker}<br>' +
                        'Date: %{x}<br>' +
                        'Cours du ticker: %{y:.2f}€<br>' +
                        'Fonds investis: %{customdata:,.2f}€<extra></extra>',
        )

        dataPourcentageFiltres = dataPourcentage.dropna()
        prixFifoTickerFiltres = prixFifoTicker.reindex(index=dataPourcentageFiltres.index)
        prixFifoTickerFiltres = prixFifoTickerFiltres.apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 0)
        prixFifoTickerFiltres = prixFifoTickerFiltres[prixFifoTickerFiltres > 0].sort_index()
        # Tracé pour les prix FIFO du ticker
        tracePrixFifo = go.Scatter(
            x=prixFifoTickerFiltres.index,
            y=prixFifoTickerFiltres,
            mode='lines',
            name=f"{nameTicker} - Prix FIFO",
            line=dict(color='#00ffff', dash='dot', width=2.5),
            hovertemplate=f'Ticker: {nameTicker}<br>' +
                        'Date: %{x}<br>' +
                        'Prix FIFO: %{y:.2f}€<extra></extra>',
        )

        # Trier les montants investis pour ne garder que les dates où des investissements ont eu lieu
        montantsInvestisFiltres = montantsInvestisTicker[montantsInvestisTicker > 0].sort_index()
        # Extraire les prix du ticker aux dates d'investissements
        prixFifoTickerFiltres = prixFifoTicker.apply(lambda x: x[1] if isinstance(x, list) and len(x) > 0 else 0)
        prixAuxDatesInvestissements = prixFifoTickerFiltres.loc[montantsInvestisFiltres.index]
        # Tracé pour les points d'investissements sur le graphique du prix de l'action
        traceInvestissements = go.Scatter(
            x=prixAuxDatesInvestissements.index,
            y=prixAuxDatesInvestissements.values,
            mode='markers',
            name=f"{nameTicker} - Investissements",
            marker=dict(
                color='green', 
                size=10, 
                symbol='triangle-up', 
                opacity=1, 
                line=dict(color='white', width=1.5)  # Bordure blanche autour des triangles
            ),
            hovertemplate=f'Ticker: {nameTicker}<br>' +
                        'Date: %{x}<br>' +
                        'Prix de l\'action: %{y:.2f}€<br>' +
                        'Montant investi: %{customdata:,.2f}€<extra></extra>',
            customdata=montantsInvestisFiltres.values,  # Associer les montants investis aux points
        )

        # Trier les montants investis pour ne garder que les dates où des investissements ont eu lieu
        montantsVentesFiltres = montantsVentesTickers[montantsVentesTickers > 0].sort_index()
        # Extraire les prix du ticker aux dates d'investissements
        prixAuxDatesVentes = prixTicker.loc[montantsVentesFiltres.index]
        # Tracé pour les points d'investissements sur le graphique du prix de l'action
        traceVentes = go.Scatter(
            x=prixAuxDatesVentes.index,
            y=prixAuxDatesVentes.values,
            mode='markers',
            name=f"{nameTicker} - Ventes",
            marker=dict(
                color='red', 
                size=10, 
                symbol='triangle-down', 
                opacity=1, 
                line=dict(color='white', width=1.5)  # Bordure blanche autour des triangles
            ),
            hovertemplate=f'Ticker: {nameTicker}<br>' +
                        'Date: %{x}<br>' +
                        'Prix de l\'action: %{y:.2f}€<br>' +
                        'Montant vendu: %{customdata:,.2f}€<extra></extra>',
            customdata=montantsVentesFiltres.values,  # Associer les montants investis aux points
        )

        return [tracePrix, tracePrixFifo, traceInvestissements, traceVentes]

    @staticmethod
    def CreateLineaireDividendsTicker(nameTicker: str, dividendesTicker: pd.Series, color: str) -> list[go.Scatter]:
        """
        Crée une trace Scatter représentant l'évolution des dividendes d'un ticker, avec des points aux dates de versement.

        Args:
            nameTicker (str): Nom du ticker.
            dividendesTicker (pd.Series): Series contenant les dividendes versés avec les dates comme index.
            color (str): Couleur de la ligne pour le graphique.

        Returns:
            list[go.Scatter]: Liste contenant les traces Scatter pour l'évolution des dividendes et les points de versement.
        """
        assert isinstance(nameTicker, str), "nameTicker doit être une chaîne de caractères"
        assert isinstance(dividendesTicker, pd.Series), "dividendesTicker doit être une Series"
        assert isinstance(color, str), "color doit être une chaîne de caractères"

        # Tracé linéaire pour l'évolution des dividendes
        traceDividendes = go.Scatter(
            x=dividendesTicker.index,
            y=dividendesTicker.cumsum(),  # Cumuler les dividendes pour montrer l'évolution
            mode='lines',
            name=f"{nameTicker} - Dividendes cumulés",
            line=dict(color=color, width=2.5),
            hovertemplate=f'Ticker: {nameTicker}<br>' +
                        'Date: %{x}<br>' +
                        'Dividendes cumulés: %{y:.2f}€<extra></extra>',
        )

        # Points où les dividendes ont été versés
        dividendesFiltres = dividendesTicker[dividendesTicker > 0].sort_index()  # Filtrer les dates avec dividendes > 0
        tracePointsDividendes = go.Scatter(
            x=dividendesFiltres.index,
            y=dividendesTicker.cumsum().loc[dividendesFiltres.index],  # Cumul des dividendes au lieu de valeurs de dividendes simples
            mode='markers+text',
            name=f"{nameTicker} - Points de dividendes",
            marker=dict(
                color=color, 
                size=10, 
                symbol='circle', 
                opacity=0.8
            ),
            text=[f"{val:.2f}€" for val in dividendesFiltres.values],  # Texte au-dessus des points
            textposition="top center",  # Position du texte
            hovertemplate=f'Ticker: {nameTicker}<br>' +
                        'Date: %{x}<br>' +
                        'Dividende: %{y:.2f}€<extra></extra>',
        )

        return [traceDividendes, tracePointsDividendes]


    # Histogramme
    def GraphiqueHistogrammeDividendesParAction(self, portefeuilles: dict, width=1600, height=650) -> go.Figure:
        """
        Trace un graphique de dividendes par action pour différents portefeuilles avec un menu pour choisir le portefeuille.

        Args:
            portefeuilles (dict): Dictionnaire contenant les noms des portefeuilles comme clés et
                                les DataFrames correspondants comme valeurs. Chaque DataFrame doit
                                contenir les années comme index, les noms des actions comme colonnes,
                                et les montants de dividendes (float) comme valeurs.
            width (int): Largeur du graphique en pixels. Par défaut, 1600.
            height (int): Hauteur du graphique en pixels. Par défaut, 650.

        Returns:
            go.Figure: Le graphique Plotly interactif avec un menu de sélection de portefeuilles.
        """
        assert isinstance(portefeuilles, dict), "Le paramètre 'portefeuilles' doit être un dictionnaire."
        assert isinstance(width, int) and width > 0, f"width doit être un entier positif: ({width})"
        assert isinstance(height, int) and height > 0, f"height doit être un entier positif: ({height})"
        for key, df in portefeuilles.items():
            assert isinstance(df, pd.DataFrame), f"Les valeurs de 'portefeuilles' doivent être des DataFrames (erreur pour '{key}')."
            assert all(np.issubdtype(dtype, np.number) for dtype in df.dtypes), f"Toutes les colonnes du DataFrame de '{key}' doivent contenir des valeurs numériques."

        colors = ["#C70039", "#335BFF", "#FF33B5", "#FF8D33", "#FFC300", "#33A1FF", "#81C784", "#5733FF", "#FFD54F", "#BA68C8",
                  "#4DB6AC", "#33FF57", "#FFB74D", "#FF5733", "#FFAB40", "#FF7043", "#64B5F6", "#DCE775", "#A1887F", "#F0E68C"]

        fig = go.Figure()
        title = "Dividende par action"
        buttons = []
        tracesCount = 0  # Compte du nombre total de traces ajoutées

        # Suppression des entrées avec des DataFrames contenant uniquement des zéros
        filteredDict = {key: df for key, df in portefeuilles.items() if not (df == 0).all().all()}
        dataFrameAnnuel = None

        # Création de traces pour chaque portefeuille
        for i, (nomPortefeuille, df) in enumerate(filteredDict.items()):
            nbVersementDividendesParAnnee = self.CountDividendsByYear(df.copy())

            # Regrouper par année et calculer la somme
            dataFrameAnnuel = df.resample('YE').sum()
            # Supprimer les lignes dont toutes les colonnes sont égales à zéro
            dataFrameAnnuel = dataFrameAnnuel[(dataFrameAnnuel != 0).any(axis=1)]
            # Modifier l'index pour qu'il ne contienne que l'année
            dataFrameAnnuel.index = dataFrameAnnuel.index.year

            # Calcul de la somme de chaque colonne
            sommeColonnes = dataFrameAnnuel.iloc[-1]
            # Tri des noms de colonnes en ordre alphabétique
            sortedColumns = sommeColonnes.index.sort_values()
            # Réorganisation du DataFrame en utilisant l'ordre trié
            dataFrameAnnuel = dataFrameAnnuel[sortedColumns]

            visibility = [False] * len(fig.data)
            # Filtrer les colonnes dont la somme est supérieure à zéro
            dataFrameAnnuel = dataFrameAnnuel.loc[:, dataFrameAnnuel.sum() > 0]
            nbTickers = len(dataFrameAnnuel.columns)
            if nbTickers <= 2:
                widthBar = 0.4
            elif nbTickers <= 3:
                widthBar = 0.3
            elif nbTickers <= 6:
                widthBar = 0.2
            elif nbTickers <= 10:
                widthBar = 0.2
            else:
                widthBar = 0.1
                if nbTickers > 15:
                    # Calculer la somme de chaque colonne
                    sommeColonnes = dataFrameAnnuel.sum()
                    # Obtenir les 15 colonnes avec les sommes les plus élevées
                    colonnesSelectionnees = sommeColonnes.nlargest(15).index
                    # Filtrer le DataFrame pour ne garder que ces colonnes
                    dataFrameAnnuel = dataFrameAnnuel[colonnesSelectionnees]
                    title += " (seulement 15 actions)"


            for j, col in enumerate(dataFrameAnnuel.columns):
                # Vérifier si l'action a versé des dividendes
                if dataFrameAnnuel[col].sum() != 0:
                    # Ajouter une trace pour l'action courante
                    fig.add_trace(go.Bar(
                        x=dataFrameAnnuel.index,
                        y=dataFrameAnnuel[col],
                        name=f"{col}",
                        marker=dict(color=colors[j % len(colors)]),
                        width=widthBar,
                        visible=(i == 0),  # Rendre visible seulement les traces du premier portefeuille au départ
                        text=[f"{val:.2f} €" if pd.notna(val) and val != 0 else "" for val in dataFrameAnnuel[col]],
                        textposition='outside',
                        hoverinfo='text',
                        hovertext=[
                            f"Ticker: {col}<br>Montant: {val:.2f} €<br>Nombre de dates de distribution des dividendes: {nbVersementDividendesParAnnee[year][col]}<br>Année: {year}"
                            if pd.notna(val) and val != 0 else ""
                            for year, val in zip(dataFrameAnnuel.index, dataFrameAnnuel[col])
                        ],
                        hoverlabel=dict(
                            bgcolor=colors[j % len(colors)],  # Couleur de fond
                            font=dict(color="white")  # Couleur du texte en blanc
                        ),
                        textfont=dict(color=colors[j % len(colors)], size=12, family="Arial")
                    ))
                    visibility.append(True)  # Ajouter True pour la trace actuelle
                    tracesCount += 1


            # Ajouter False pour les traces suivantes (ajoutées après ce portefeuille)
            visibility += [False] * (len(fig.data) - len(visibility))

            # Ajouter un bouton pour chaque portefeuille avec sa liste de visibilité
            buttons.append(dict(
                label=nomPortefeuille,
                method="update",
                args=[{"visible": visibility},
                    {"title": f"Dividende par action"}],
            ))


        # Vérifier et compléter les listes de visibilité pour chaque bouton
        for i, button in enumerate(buttons):
            if len(button["args"][0]["visible"]) != tracesCount:
                difference = tracesCount - len(button["args"][0]["visible"])
                # Ajouter les valeurs manquantes de False
                button["args"][0]["visible"].extend([False] * difference)

        if dataFrameAnnuel is not None and not dataFrameAnnuel.empty:
            super().GenerateGraph(fig)
            # Mise à jour de la disposition du graphique
            fig.update_layout(
                xaxis=dict(
                    title='Années',
                    tickmode='array',
                    tickvals=dataFrameAnnuel.index,  # Utiliser les années comme valeurs
                    ticktext=[str(year) for year in dataFrameAnnuel.index],  # Convertir en chaîne pour l'affichage
                    color='white'
                ),
                yaxis=dict(
                    title='Montant des dividendes (€)',
                    color='white',
                    ticksuffix="€",
                ),
                plot_bgcolor='#121212',
                paper_bgcolor='#121212',
                font=dict(color='white'),
                legend=dict(title="Tickers", font=dict(color='white')),
                updatemenus=[{
                    "buttons": buttons,
                    "direction": "down",
                    "showactive": True,
                    "x": 0,
                    "xanchor": "left",
                    "y": 1,
                    "yanchor": "top"
                }],
                title=title,
                width=width,
                height=height,
            )

            return fig
        
        return None
    
    @staticmethod
    def CountDividendsByYear(dataFrame: pd.DataFrame) -> dict:
        """
        Compte le nombre de versements de dividendes pour chaque action par année.

        Args:
            dataFrame (pd.DataFrame): DataFrame contenant des dates comme index et des noms d'entreprises comme colonnes.
                                    Les valeurs représentent les montants de dividendes.

        Returns:
            dict: Dictionnaire avec pour clé l'année, et comme valeur un dictionnaire ayant pour clé le nom de l'action
                et pour valeur le nombre de versements de dividendes.
        """
        assert isinstance(dataFrame, pd.DataFrame), "Le paramètre 'dataFrame' doit être un DataFrame avec des dates en index et des noms d'actions en colonnes."
        assert pd.api.types.is_datetime64_any_dtype(dataFrame.index), "L'index du DataFrame doit être de type datetime."

        # Convertir les index en années pour faciliter l'agrégation
        dataFrame['Year'] = dataFrame.index.year

        # Initialiser le dictionnaire de résultats
        dividendsPerYear = {}

        # Parcourir les années distinctes dans le DataFrame
        for year in dataFrame['Year'].unique():
            # Sélectionner les lignes correspondant à l'année courante
            yearlyData = dataFrame[dataFrame['Year'] == year].drop(columns='Year')

            # Compter les versements de dividendes (les valeurs non nulles ou non nulles et non zéros)
            dividendsPerYear[year] = yearlyData.apply(lambda x: x[x != 0].count(), axis=0).to_dict()

        return dividendsPerYear
    

    # Combiné
    def GraphiqueAnalyseTickers(self, prixTickers: pd.DataFrame, tickersTWR: dict, prixNetTickers: dict, 
                                dividendesTickers: dict, prixFifoTickers: dict, fondsInvestisTickers: dict, 
                                montantsInvestisTickers: dict, montantsVentesTickers: dict, 
                                width=1600, height=2000) -> go.Figure:
        """
        Cette fonction génère un graphique d'analyse de portefeuille, contenant plusieurs sous-graphiques pour chaque ticker. 
        Le graphique présente trois sections :
            1. Le pourcentage et le prix des tickers.
            2. Le prix des tickers et le prix FIFO.
            3. Les dividendes versés par ticker.
        
        Elle crée un graphique interactif avec des sous-tracés, incluant des menus déroulants pour chaque ticker.

        Args:
            prixTickers (pd.DataFrame): DataFrame contenant les prix des tickers (par date).
            tickersTWR (dict): Dictionnaire contenant les informations des tickers au format TWR.
            prixNetTickers (dict): Dictionnaire contenant les prix nets des tickers.
            dividendesTickers (dict): Dictionnaire contenant les dividendes versés par ticker.
            prixFifoTickers (dict): Dictionnaire des prix FIFO des tickers.
            fondsInvestisTickers (dict): Dictionnaire des fonds investis pour chaque ticker.
            montantsInvestisTickers (dict): Dictionnaire des montants investis pour chaque ticker.
            montantsVentesTickers (dict): Dictionnaire des montants des ventes pour chaque ticker.
            width (int, optional): Largeur du graphique. Par défaut 1600.
            height (int, optional): Hauteur du graphique. Par défaut 2000.

        Returns:
            go.Figure: Un objet de type Plotly `go.Figure` représentant le graphique interactif généré.
        """
        assert isinstance(prixTickers, pd.DataFrame), "prixTickers doit être un DataFrame."
        assert isinstance(tickersTWR, dict), "tickersTWR doit être un dictionnaire."
        assert isinstance(prixNetTickers, dict), "prixNetTickers doit être un dictionnaire."
        assert isinstance(dividendesTickers, dict), "dividendesTickers doit être un dictionnaire."
        assert isinstance(prixFifoTickers, dict), "prixFifoTickers doit être un dictionnaire."
        assert isinstance(fondsInvestisTickers, dict), "fondsInvestisTickers doit être un dictionnaire."
        assert isinstance(montantsInvestisTickers, dict), "montantsInvestisTickers doit être un dictionnaire."
        assert isinstance(montantsVentesTickers, dict), "montantsVentesTickers doit être un dictionnaire."

        # Vérifie que les arguments width et height sont des entiers positifs
        assert isinstance(width, int) and width > 0, f"width doit être un entier positif, mais c'est {type(width)}."
        assert isinstance(height, int) and height > 0, f"height doit être un entier positif, mais c'est {type(height)}."

        colors = self.colors
        fig = make_subplots(
            rows=3, cols=1,
            specs=[[{'type': 'xy'}], [{'type': 'xy'}], [{'type': 'xy'}]],
            row_heights=[0.33, 0.33, 0.33],
            column_widths=[1],
            subplot_titles=["Pourcentage & Prix", "Prix du ticker", "Dividendes versés"],
            vertical_spacing=0.05      # Réduit l'espace vertical entre les lignes
        )

        PORTEFEUILLEANALYSER = "Mon Portefeuille"

        buttonsTickers = []
        nbTraces = []
        initialVisibleTraces = []

        tickers = list(tickersTWR[PORTEFEUILLEANALYSER].iloc[-1].dropna().index)
        for i, nameTicker in enumerate(tickers):
            color = colors[i % len(colors)]

            # Tracé pour le pourcentage par devise
            pourcentageDevise = self.CreateLineaireTickerPourcentageDevise(
                nameTicker, tickersTWR[PORTEFEUILLEANALYSER][nameTicker], prixNetTickers[PORTEFEUILLEANALYSER][nameTicker], color)
            fig.add_trace(pourcentageDevise, row=1, col=1)
            nbTraces.append(pourcentageDevise)

            # Tracés pour les prix et les prix FIFO
            tracesPrix = self.CreateLineaireCoursTicker(
                nameTicker, prixTickers[nameTicker], prixFifoTickers[PORTEFEUILLEANALYSER][nameTicker], fondsInvestisTickers[PORTEFEUILLEANALYSER][nameTicker], 
                montantsInvestisTickers[PORTEFEUILLEANALYSER][nameTicker], montantsVentesTickers[PORTEFEUILLEANALYSER][nameTicker], tickersTWR[PORTEFEUILLEANALYSER][nameTicker], color)
            for trace in tracesPrix:
                fig.add_trace(trace, row=2, col=1)
                nbTraces.append(trace)

            # Tracés pour les dividendes
            tracesDividends = self.CreateLineaireDividendsTicker(
                nameTicker, dividendesTickers[PORTEFEUILLEANALYSER][nameTicker], color)
            for trace in tracesDividends:
                fig.add_trace(trace, row=3, col=1)
                nbTraces.append(trace)

            # Set initial visibility for the traces related to this ticker
            if i == 0:  # First ticker: All traces visible
                initialVisibleTraces.extend([True] * len(nbTraces[-(len(tracesPrix) + len(tracesDividends) + 1):]))  # Visible
            else:  # Other tickers: All traces hidden
                initialVisibleTraces.extend([False] * len(nbTraces[-(len(tracesPrix) + len(tracesDividends) + 1):]))  # Hidden

        # Now set the visibility for each trace in `fig.data` according to `initialVisibleTraces`
        for i, trace in enumerate(fig.data):
            trace.visible = initialVisibleTraces[i]

        # Créer le bouton du menu déroulant
        for i, nameTicker in enumerate(tickers):
            buttonsTickers.append(dict(
                label=nameTicker,
                method="update",
                args=[{"visible": [trace.name.startswith(nameTicker) for trace in nbTraces]}]
            ))

        super().GenerateGraph(fig)
        # Ajout du menu déroulant
        fig.update_layout(
            updatemenus=[{
                "buttons": buttonsTickers,
                "direction": "down",
                "showactive": True,
                "xanchor": "left",
                "yanchor": "top",
            }],
            showlegend=False,  # Ne pas afficher la légende
            width=width,
            height=height
        )

        layoutUpdates = {
            'tickfont': dict(color='white'),
            'gridcolor': 'rgba(255, 255, 255, 0.2)'
        }

        for i in range(1, 4):
            if i == 1:  # Pour le premier graphique (Pourcentage)
                suffix = '%'
            else:  # Pour les autres graphiques (Euros)
                suffix = '€'

            # Appliquer les mises à jour avec le suffixe correspondant
            fig.update_layout({
                f'xaxis{i}': layoutUpdates,
                f'yaxis{i}': {**layoutUpdates, 'ticksuffix': suffix}
            })

        return fig

