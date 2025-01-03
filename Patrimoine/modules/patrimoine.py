from .sourcesRevenus.bnpParibas import BnpParibas
from .sourcesRevenus.bourse import Bourse
from .sourcesRevenus.graphiques.GraphiquesDashboard import GraphiquesDashboard

import pandas as pd
import os


class Patrimoine(BnpParibas, Bourse, GraphiquesDashboard):
    """
    La classe `Patrimoine` est conçue pour gérer et analyser l'évolution du patrimoine financier à partir de transactions.
    Elle permet de charger des données depuis des fichiers JSON, de calculer l'évolution du patrimoine quotidiennement,
    de transformer les données en différents formats, et de visualiser les résultats à l'aide de graphiques interactifs.
    """

    def __init__(self, repertoireJson: str):
        """
        Args:
            repertoireJson (str): Le chemin du répertoire où les fichiers JSON sont stockés.
        """
        assert isinstance(repertoireJson, str), f"repertoireJson doit être une chaîne de caractères: ({type(repertoireJson)})"
        assert os.path.isdir(repertoireJson), f"directory doit être un répertoire valide : ({repertoireJson})"
        
        argentCompteCourantInitial = 0
        argentLivretAInitial = 3816.42  # Argent initial (2014-10-27)
        self.patrimoine = pd.DataFrame(dtype=float)

        self.EvolutionDuPatrimoine("Compte Courant", argentCompteCourantInitial, (repertoireJson + "Compte Chèques"))
        self.EvolutionDuPatrimoine("Livret A", argentLivretAInitial, (repertoireJson + "livret A"))
        self.EvolutionDuPatrimoineBourse(repertoireJson + "Bourse/json/Portefeuille.json")

