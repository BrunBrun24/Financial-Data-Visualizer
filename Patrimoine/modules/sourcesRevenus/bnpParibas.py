from .recuperationDonnees import RecuperationDonnees

import pandas as pd
import os


class BnpParibas(RecuperationDonnees):

    def EvolutionDuPatrimoine(self, nomDuCompte: str, argent: float, dossierCompte: str) -> pd.DataFrame:
        """
        Calcule l'évolution du patrimoine quotidiennement basé sur les transactions trouvées dans les fichiers JSON.

        Args:
            nomDuCompte (str): Nom du compte à mettre à jour.
            argent (float): Montant initial d'argent sur le compte.
            dossierCompte (str): Chemin vers le dossier contenant les fichiers JSON avec les transactions.

        Returns:
            pd.DataFrame: Le DataFrame mis à jour avec l'évolution du patrimoine.
        """
        assert isinstance(self.patrimoine, pd.DataFrame), f"La variable patrimoine doit être un DataFrame: ({type(self.patrimoine)})"
        assert isinstance(nomDuCompte, str), f"La variable nomDuCompte doit être une chaîne de caractères: ({type(nomDuCompte)})"
        assert isinstance(argent, (int, float)), f"La variable argent doit être un nombre: ({type(argent)})"
        assert isinstance(dossierCompte, str), f"La variable dossierCompte doit être une chaîne de caractères: ({type(dossierCompte)})"
        assert os.path.exists(dossierCompte), f"Le dossier spécifié n'existe pas: {dossierCompte}"

        if nomDuCompte not in self.patrimoine.columns:
            self.patrimoine[nomDuCompte] = pd.Series(dtype=float)

        transactions = self.TransformerDossierJsonEnDataFrame(dossierCompte)

        assert pd.api.types.is_datetime64_any_dtype(transactions.index), "L'index doit être de type datetime."
        assert "MONTANT" in transactions, "La colonne 'MONTANT' est manquante dans les transactions."

        for date, row in transactions.iterrows():
            argent += row["MONTANT"]
            self.patrimoine.at[pd.to_datetime(date), nomDuCompte] = argent
    
    
    