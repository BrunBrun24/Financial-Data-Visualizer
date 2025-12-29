import os

import pandas as pd


class ReportDataHandler:
    """
    Fournit des outils utilitaires pour le traitement des données financières 
    et la gestion des fichiers de rapports.

    Cette classe regroupe les fonctions de filtrage des revenus/dépenses 
    et la préparation de l'arborescence des dossiers.
    """

    # --- [ Traitement des Données ] ---
    @staticmethod
    def _get_income_df(operations: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre les opérations de la catégorie 'Revenus' et convertit la date.

        Args:
            - operations (pd.DataFrame) : DataFrame des opérations catégorisées.

        Returns:
            - pd.DataFrame : DataFrame filtré contenant uniquement les revenus.
        """
        # Filtrage basé sur la colonne 'category'
        df = operations[operations['category'] == 'Revenus'].copy()
        df["operation_date"] = pd.to_datetime(df["operation_date"])
        return df

    @staticmethod
    def _get_expense_df(operations: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre les opérations de dépenses et convertit les montants en valeurs absolues.

        Args:
            - operations (pd.DataFrame) : DataFrame des opérations catégorisées.

        Returns:
            - pd.DataFrame : DataFrame filtré des dépenses (montants positifs).
        """
        # On exclut la catégorie 'Revenus'
        df = operations[operations['category'] != 'Revenus'].copy()
        df["operation_date"] = pd.to_datetime(df["operation_date"])
        
        # Transformation des montants négatifs en positifs pour les graphiques/rapports
        df['amount'] = df['amount'].abs()
        return df

    # --- [ Gestion du Système de Fichiers ] ---
    @staticmethod
    def _create_annual_folders(root_path: str, operations: pd.DataFrame):
        """
        Crée l'arborescence des dossiers par année pour le stockage des rapports.

        Args:
            - root_path (str) : Chemin racine où créer les dossiers.
            - operations (pd.DataFrame) : DataFrame contenant les dates d'opérations.
        """
        # Création du dossier racine s'il n'existe pas
        os.makedirs(root_path, exist_ok=True)

        # Extraction des années uniques à partir de la colonne date
        df_temp = operations.copy()
        df_temp["year"] = pd.to_datetime(df_temp["operation_date"]).dt.year
        years = sorted(df_temp["year"].unique())

        # Création d'un sous-dossier pour chaque année
        for year in years:
            year_path = os.path.join(root_path, str(int(year)))
            os.makedirs(year_path, exist_ok=True)