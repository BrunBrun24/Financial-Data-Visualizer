from .graphiqueBar import GraphiqueBar
from .graphiqueCirculaire import GraphiqueCirculaire
from .graphiqueCorrelation import GraphiqueCorrelation
from .graphiqueLigne import GraphiqueLigne
from .graphiqueTreeMap import GraphiqueTreemap

import os


class GraphiquesDashboard(GraphiqueBar, GraphiqueCirculaire, GraphiqueCorrelation, GraphiqueLigne, GraphiqueTreemap):
    

    def PlotlyInteractive(self, nomDossier: str, nomFichier: str):
        """
        Crée un graphique interactif utilisant Plotly pour visualiser différents aspects de l'évolution du patrimoine en l'enregistrant dans un fichier html.

        Args:
            nomDossier (str): Chemin vers le dossier où sauvegarder le fichier de sortie.
            nomFichier (str): Nom du fichier de sortie (doit avoir une extension .html).
        """
        assert isinstance(nomDossier, str), "nomDossier doit être une chaîne de caractères"
        assert os.path.exists(nomDossier), f"Le chemin '{nomDossier}' n'existe pas"

        assert isinstance(nomFichier, str), f"nomFichier doit être une chaîne de caractères: ({nomFichier})"
        assert nomFichier.endswith('.html'), f"Le fichier {nomFichier} n'a pas l'extension .html."

        patrimoineGraphique = []

        # Ajout des graphiques
        patrimoineGraphique.append(self.GraphiqueLineaireEvolutionPatrimoine())
        patrimoineGraphique.append(self.GraphiqueLineaireAera())
        patrimoineGraphique.append(self.GraphiqueHistogrammeSuperpose("M"))
        patrimoineGraphique.append(self.GraphiqueDiagrammeCirculaire())
        patrimoineGraphique.append(self.GraphiqueTreemap())
        
        patrimoineGraphique.append(self.GraphiqueCorrelationMap())

        # Sauvegarde des graphiques dans un fichier HTML
        self.SaveInFile(patrimoineGraphique, (nomDossier + nomFichier))

    @staticmethod
    def SaveInFile(figures: list, nomFichier: str):
        """
        Enregistre les graphiques générés dans un fichier HTML.

        Args:
            figures (list): Liste d'objets graphiques Plotly à enregistrer.
            nomFichier (str): Nom du fichier dans lequel enregistrer les graphiques HTML.
        """
        # Assertions pour valider les types des paramètres
        assert isinstance(figures, list), "figures doit être une liste"
        assert all(hasattr(fig, 'write_html') for fig in figures), "Chaque élément de figures doit avoir la méthode 'write_html'"
        assert isinstance(nomFichier, str), "nomFichier doit être une chaîne de caractères"

        with open(nomFichier, 'w') as f:
            for fig in figures:
                fig.write_html(f, include_plotlyjs='cdn')

    