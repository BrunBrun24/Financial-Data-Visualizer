import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


class GraphiqueBar:
    
    def GraphiqueHistogrammeSuperpose(self, freq: str):
        """
        Affiche un histogramme superposé des montants pour toutes les colonnes du DataFrame à une fréquence donnée,
        excepté la colonne 'Date'.

        Cette fonction utilise les données du DataFrame de patrimoine, applique la transformation en fonction de la
        fréquence spécifiée, filtre les lignes contenant des valeurs manquantes, puis crée un histogramme superposé
        des montants pour toutes les colonnes à l'aide de Plotly Express.

        Args:
            freq (str): Fréquence des dates à utiliser pour transformer le DataFrame. Peut être 'M' (mois) ou 'Y' (années).
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"self.patrimoine doit être un DataFrame: {type(self.patrimoine)}."
        assert freq in ['M', 'Y'], f"La fréquence doit être 'M' ou 'Y': '{freq}'."

        df = self.patrimoine.copy()
        df = self.ReorganiserColonnesParValeurDerniereLigne(df)
        df = self.TransformerDataframe(df, freq)

        assert 'Date' in df.columns, "La colonne 'Date' est manquante dans le DataFrame."
        df['Date'] = pd.to_datetime(df['Date'])
        # Sélectionner toutes les colonnes sauf 'Date' pour l'histogramme
        colonnes = [col for col in df.columns if col != 'Date']
        assert len(colonnes) > 0, "Aucune colonne à afficher hormis la colonne 'Date'."

        # Filtrer les lignes où les colonnes sélectionnées n'ont pas de NaN
        dfiltered = df.dropna(subset=colonnes)

        # Trier les colonnes par la valeur de la dernière ligne de manière décroissante
        colonnes = sorted(colonnes, key=lambda col: df[col].iloc[-1], reverse=True)

        # Créer un histogramme superposé avec Plotly Express pour toutes les colonnes
        fig = px.bar(
            dfiltered,
            x='Date',
            y=colonnes,
            labels={'value': 'Montant', 'variable': 'Type de Compte'},
            title="Évolution du patrimoine par type de compte (montant en fin d'année)"
        )

        fig.update_layout(
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig

    @staticmethod
    def ReorganiserColonnesParValeurDerniereLigne(df: pd.DataFrame) -> pd.DataFrame:
        """
        Réorganise les colonnes du DataFrame en fonction des valeurs de la dernière ligne,
        en mettant la colonne avec la valeur la plus élevée au début et celle avec la valeur la plus basse à la fin.

        Args:
            df (pd.DataFrame): DataFrame contenant les données.

        Returns:
            pd.DataFrame: DataFrame avec les colonnes réorganisées.
        """
        assert isinstance(df, pd.DataFrame), f"Le paramètre 'df' doit être un DataFrame: {type(df)}."

        # Obtenir les valeurs de la dernière ligne
        valeursDerniereLigne = df.iloc[-1]
        # Trier les colonnes en fonction des valeurs de la dernière ligne
        colonnesReorganisees = valeursDerniereLigne.sort_values(ascending=False).index
        # Réorganiser les colonnes du DataFrame
        return df[colonnesReorganisees]
    
    def TransformerDataframe(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Transforme un DataFrame de large à long, réinitialisant l'index et utilisant melt pour
        convertir le DataFrame. Réorganise les colonnes pour obtenir 'Date', 'Type', et 'Montant'.

        Args:
            df (pd.DataFrame): DataFrame avec des dates comme index et plusieurs colonnes de valeurs.
            freq (str): Fréquence des dates à ajouter. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.

        Returns:
            pd.DataFrame: DataFrame transformé.
        """
        assert pd.api.types.is_datetime64_any_dtype(df.index), "L'index doit être de type datetime."
        assert not df.empty, "Le DataFrame est vide"
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], "La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q'."

        df = self.SelectionnerDates(df, freq)
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Date'}, inplace=True)

        if freq == "Y":
            # Décaler les dates d'un an
            df['Date'] = df['Date'] - pd.DateOffset(years=1)

        return df
    
    @staticmethod
    def SelectionnerDates(df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Ajoute des dates à une fréquence spécifiée dans le DataFrame, garde seulement ces dates, et complète les valeurs manquantes par la date la plus proche.

        Args:
            df (pd.DataFrame): DataFrame avec des dates comme index et plusieurs colonnes de valeurs.
            freq (str): Fréquence des dates à ajouter. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.

        Returns:
            pd.DataFrame: DataFrame mis à jour avec les dates ajoutées et les valeurs manquantes complétées.
        """
        assert isinstance(df, pd.DataFrame), f"La variable df doit être une DataFrame: ({type(df)})"
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], "La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q'."

        # Convertir l'index en datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        if "Bourse" in df.columns:
            firstDateBourse = df['Bourse'].first_valid_index()
        if "Compte Courant" in df.columns:
            firstDateCompteCourant = df['Compte Courant'].first_valid_index()

        # Déterminer les dates à inclure selon la fréquence choisie
        if freq == 'D':
            periodRange = pd.date_range(df.index.min(), df.index.max(), freq='D')
        elif freq == 'M':
            periodRange = pd.date_range(df.index.min().replace(day=1), df.index.max().replace(day=1), freq='MS')
        elif freq == 'Y':
            periodRange = pd.date_range(df.index.min().replace(month=1, day=1), df.index.max().replace(month=1, day=1), freq='YS')
        elif freq == 'W':
            periodRange = pd.date_range(df.index.min() - pd.DateOffset(days=df.index.min().weekday()),
                                        df.index.max() + pd.DateOffset(days=(6 - df.index.max().weekday())), freq='W-SUN')
        elif freq == 'Q':
            periodRange = pd.date_range(df.index.min() - pd.DateOffset(months=(df.index.min().month - 1) % 3),
                                        df.index.max() + pd.DateOffset(months=2 - (df.index.max().month - 1) % 3), freq='Q')

        combined_dates = pd.Index(periodRange).union([df.index.max()])
        newDf = df.reindex(combined_dates)

        # S'assurer que l'index est trié
        newDf = newDf.sort_index()

        # Remplir les valeurs manquantes en utilisant les valeurs les plus proches disponibles dans le DataFrame initial
        for column in df.columns:
            # Trouver les valeurs non manquantes dans la colonne
            non_nan = df[[column]].dropna()
            # Créer une série de valeurs manquantes
            missing_values = newDf[newDf[column].isna()]

            if not non_nan.empty:
                # Trouver les dates les plus proches pour les valeurs manquantes
                indexer = non_nan.index.get_indexer(missing_values.index, method='nearest')

                for i, missing_date in enumerate(missing_values.index):
                    closest_date = non_nan.index[indexer[i]]
                    # Remplacer la valeur manquante avec la valeur de la date la plus proche
                    newDf.loc[missing_date, column] = df.loc[closest_date, column]

        # if freq == 'Y':
        #     newDf.index = [i.strftime('%Y') for i in newDf.index]

        if "Bourse" in newDf.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            newDf.loc[newDf.index < firstDateBourse, 'Bourse'] = 0
        if "Compte Courant" in newDf.columns:
            # Remplacer les valeurs avant la première date valide de 'Bourse' par 0
            newDf.loc[newDf.index < firstDateCompteCourant, 'Compte Courant'] = 0

        return newDf


    def GraphiqueHistogrammeCoteACote(self, freq: str):
        """
        Affiche un graphique en barres côte à côte pour les montants de chaque colonne du DataFrame
        sur une période déterminée par la fréquence spécifiée.

        La fonction sélectionne les données en fonction de la fréquence, filtre les lignes sans valeurs manquantes,
        puis affiche un graphique avec des barres pour chaque colonne du DataFrame. Les barres sont colorées et affichées
        côte à côte avec une personnalisation de l'espacement.

        Args:
            freq (str): Fréquence des dates à utiliser pour filtrer le DataFrame. Peut être 'D', 'M', 'Y', 'W', ou 'Q'.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"self.patrimoine doit être un DataFrame: {type(self.patrimoine)}."
        assert freq in ['D', 'M', 'Y', 'W', 'Q'], f"La fréquence doit être 'D', 'M', 'Y', 'W', ou 'Q': '{freq}'."

        df = self.patrimoine.copy()
        df = self.SelectionnerDates(df, freq)
        df = df.dropna()

        colors = ['rgba(99, 110, 250, 1)', 'rgba(239, 85, 59, 1)', 'rgba(0, 204, 150, 1)',
                'rgba(171, 99, 250, 1)', 'rgba(255, 161, 90, 1)', 'rgba(25, 211, 243, 1)']

        fig = go.Figure()

        for i, nameColumn in enumerate(df.columns):
            # Ajouter les barres pour chaque colonne
            fig.add_trace(go.Bar(x=df.index, y=df[nameColumn], name=nameColumn, marker_color=colors[i % len(colors)]))

        # Mise en forme du graphique
        fig.update_layout(
            title='Evolution des différents Comptes',
            xaxis_tickfont_size=14,
            yaxis=dict(
                title='Montant (€)',
                titlefont_size=16,
                tickfont_size=14,
            ),
            barmode='group',
            bargap=-0,  # Espace entre les groupes de barres
            bargroupgap=0.1,  # Espace entre les barres du même groupe
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white')
        )

        return fig
    
