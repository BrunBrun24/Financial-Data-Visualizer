from .graphiqueLigne import GraphiqueLigne
from .graphiqueBar import GraphiqueBar
from .graphiqueCirculaire import GraphiqueCirculaire
from .graphiqueTableaux import GraphiqueTableaux
from .graphiqueHeatmap import GraphiqueHeatmap
from .graphiqueTreemap import GraphiqueTreemap

import os


class GraphiquesDashboard(GraphiqueLigne, GraphiqueBar, GraphiqueCirculaire, GraphiqueTableaux, GraphiqueHeatmap, GraphiqueTreemap):
    def __init__(self, tickersTWR, prixNetTickers, prixBrutTickers, dividendesTickers, 
                 portefeuilleTWR, prixNetPortefeuille, soldeCompteBancaire, fondsInvestis, 
                 pourcentagesMensuelsPortefeuille):
        super().__init__(tickersTWR, prixNetTickers, prixBrutTickers, dividendesTickers, 
                 portefeuilleTWR, prixNetPortefeuille, soldeCompteBancaire, fondsInvestis, 
                 pourcentagesMensuelsPortefeuille)
        

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

        portefeuillesGraphiques = []

        # Ajout des graphiques
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.portefeuilleTWR, "Progression en TWR (pour l'argent investi) pour chaque portefeuille", "%"))
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.prixNetPortefeuille, "Progression en euro pour chaque portefeuille", "€"))
        portefeuillesGraphiques.append(self.GraphiqueHeatmapPourcentageParMois(self.pourcentagesMensuelsPortefeuille))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.tickersTWR, "Progression en TWR (pour l'argent investi) pour chaque ticker", "%"))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.prixNetTickers, "Progression net en euro pour chaque ticker", "€"))
        portefeuillesGraphiques.append(self.GraphiqueLineaireTickers(self.prixBrutTickers, "Progression brut en euro pour chaque ticker", "€"))
        portefeuillesGraphiques.append(self.GraphiqueDividendesParAction(self.dividendesTickers))
        portefeuillesGraphiques.append(self.GraphiqueTreemapPortefeuille(self.prixBrutTickers))
        portefeuillesGraphiques.append(self.GraphiqueSunburst(self.prixBrutTickers))
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.fondsInvestis, "Progression de l'argent investi", "€"))
        portefeuillesGraphiques.append(self.GraphiqueLineairePortefeuilles(self.soldeCompteBancaire, "Progression de l'argent sur le Compte Bancaire", "€"))

        # Sauvegarde des graphiques dans un fichier HTML
        self.SaveInFile(portefeuillesGraphiques, (nomDossier + nomFichier))
        
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

    