from .graphiquesPortefeuilles import GraphiquesPortefeuilles
from .graphiquesTickers import GraphiquesTickers

import os

class GraphiquesDashboard(GraphiquesPortefeuilles, GraphiquesTickers):
    
    def __init__(self):
        GraphiquesTickers.__init__(self)
        
    def PlotlyInteractive(self, nomDossier: str, nomFichier: str):
        """
        Crée un graphique interactif utilisant Plotly pour visualiser différents aspects de l'évolution du portefeuille en l'enregistrant dans un fichier html.

        Args:
            nomDossier (str): Chemin vers le dossier où sauvegarder le fichier de sortie.
            nomFichier (str): Nom du fichier de sortie (doit avoir une extension .html).
        """
        assert isinstance(nomDossier, str), "nomDossier doit être une chaîne de caractères"
        if nomDossier != "":
            assert os.path.exists(nomDossier), f"Le chemin '{nomDossier}' n'existe pas"

        assert isinstance(nomFichier, str), f"nomFichier doit être une chaîne de caractères: ({nomFichier})"
        assert nomFichier.endswith('.html'), f"Le fichier {nomFichier} n'a pas l'extension .html."

        portefeuillesGraphiquesHtml = []

        # Ajout des graphiques
        portefeuillesGraphiquesHtml.append(self.GraphiqueLineairePortefeuillesMonnaie(self.soldeCompteBancaire, self.montantsInvestisPortefeuille, "Progression de l'argent sur le Compte", 1880, 900))
        portefeuillesGraphiquesHtml.append(self.GraphiqueDfPourcentageMonnaie(self.portefeuilleTWR, self.prixNetPortefeuille, "Progression en TWR pour chaque portefeuille", 1880, 900))
        portefeuillesGraphiquesHtml.append(self.GraphiqueCombineSunburstTreemapHeatmap(self.prixBrutTickers, self.pourcentagesMensuelsPortefeuille, self.cash, 1880))

        portefeuillesGraphiquesHtml.append(self.GraphiqueAnalyseTickers(self.prixTickers, self.tickersTWR, self.prixNetTickers, 
                                                                        self.dividendesTickers, self.prixFifoTickers, self.fondsInvestisTickers, 
                                                                        self.montantsInvestisTickers, self.montantsVentesTickers, 1880))


        portefeuillesGraphiquesHtml = [element for element in portefeuillesGraphiquesHtml if element is not None]
        self.SaveInFile(portefeuillesGraphiquesHtml, (nomDossier + nomFichier))
    
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

    