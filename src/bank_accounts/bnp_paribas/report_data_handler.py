import pandas as pd


class ReportDataHandler:
    """
    Fournit des outils utilitaires pour le traitement des données financières
    et la gestion des fichiers de rapports.
    """

    @staticmethod
    def _get_income_df(operations: pd.DataFrame) -> pd.DataFrame:
        """Filtre les opérations de la catégorie 'Revenus' et convertit la date."""

        df = operations[operations["category"] == "Revenus"].copy()
        df["operation_date"] = pd.to_datetime(df["operation_date"])
        return df

    @staticmethod
    def _get_expense_df(operations: pd.DataFrame) -> pd.DataFrame:
        """Filtre les opérations de dépenses et convertit les montants en valeurs absolues."""

        df = operations[operations["category"] != "Revenus"].copy()
        df["operation_date"] = pd.to_datetime(df["operation_date"])

        # Transformation des montants négatifs en positifs pour les graphiques/rapports
        df["amount"] = df["amount"].abs()
        return df
