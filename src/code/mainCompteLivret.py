from modules.DataExtractor import DataExtractor
from modules.OperationCategoriser import OperationCategoriser
from modules.GraphiqueFinancier import GraphiqueFinancier
from modules.ExcelReportGenerator import ExcelReportGenerator
from utils.FonctionsSecondaires import ExtraireAnnee, SaveDictToJson, DiviserParMois, CreerNomFichier, RecupererFichiersJson, LoadDictFromJson


def GenererGraphiquesMensuels(chartGen, data, dossier, year, compteCourant=False):
    """
    Génère des graphiques mensuels à partir des données financières et les enregistre sous forme de fichiers HTML.

    Args:
        chartGen (GraphiqueFinancier): Instance de la classe GraphiqueFinancier utilisée pour générer les graphiques.
        data (dict): Données financières issues du fichier JSON.
        dossier (str): Nom du dossier où les fichiers graphiques seront enregistrés (ex : "Compte Chèques", "Livret A").
        year (str): Année extraite des données pour organiser les fichiers.
        compteCourant (bool, optionnel): Indique si le compte est un compte courant. Défaut à False.
    """
    allmonth = DiviserParMois(data=data)
    for yearMonth, transaction in allmonth.items():
        cheminFile = f"Bilan/{dossier}/{year}/{yearMonth}.html"
        chartGen.SetData(transaction)
        chartGen.SetOutputFile(cheminFile)
        chartGen.GraphiqueAutomatique(compteCourant=compteCourant)

def GenererRapports(data, dossier, year, compteCourant):
    """
    Génère un rapport annuel et des graphiques mensuels à partir des données financières, et les enregistre sous forme de fichiers HTML.

    Args:
        data (dict): Données financières issues du fichier JSON.
        dossier (str): Nom du dossier où les fichiers graphiques seront enregistrés (ex : "Compte Chèques", "Livret A").
        year (str): Année extraite des données pour organiser les fichiers.
        compteCourant (bool): Indique si le compte est un compte courant.
    """
    chartGen = GraphiqueFinancier(data, f"Bilan/{dossier}/{year}/Bilan {year}.html")
    chartGen.GraphiqueAutomatique(compteCourant=compteCourant)
    GenererGraphiquesMensuels(chartGen, data, dossier, year, compteCourant)

def CompteLivret():
    """
    Catégorise les dépenses
    """
    # Créer une instance de DataExtractor
    extracteur = DataExtractor(initialDir="Bilan/Archives")
    
    # Appeler la méthode SelectAndExtractData pour ouvrir la fenêtre de sélection et extraire les données
    data, extension, dossier = extracteur.SelectAndExtractData()

    if (data is not None) and (extension == "Excel"):
        year = ExtraireAnnee(data)
        cheminFileJson = f"Bilan/Archives/{dossier}/{year}.json"

        buttonLabels = {
            'Investissement': ["CTO", "Livret A", "Investissement - Autres"],
            'Revenus': ["Aides et allocations", "Salaires et revenus d'activité", "Revenus de placement", "Pensions", "Intérêts", "Loyers", "Dividendes", "Remboursement", "Chèque reçu", "Déblocage emprunt", "Virement reçu", "Virement interne", "Cashback", "Revenus - Autres"],
            'Abonnement': ["Téléphone", "Internet", "Streaming", "Logiciels"],
            'Impôts': ["Impôt sur taxes", "Impôt sur le revenu", "Impôt sur la fortune", "Taxe foncière", "Taxe d'habitation", "Contribution sociales (CSG / CRDS)"],
            'Banque': ["Epargne", "Remboursement emprumt", "Frais bancaires", "Prélèvement carte débit différé", "Retrait d'espèces", "Banques - Autres"],
            "Logement": ["Logement - Autres", "Electricité, gaz", "Eau", "Chauffage", "Loyer", "Prêt Immobiler", "Bricolage et jardinage", "Assurance habitation", "Logement - Autres", "Mobilier, électroménager, déco"],
            'Loisir et sorties': ["Voyages, vacances", "Restaurants - Bars", "Diversements, sortie culturelles", "Sports", "Soirée - Sortie", "Loisirs et sorties - Autres"],
            'Santé': ["Medecin", "Pharmacie", "Dentiste", "Mutuelle", "Opticien", "Hôpital"],
            'Transports et véhicules': ["Assurance véhicule", "Crédit auto", "Carburant", "Entretient véhicule", "Transport en commun", "Billet d'avion, Billet de train", "Taxi, VTC", "Location de véhicule", "Péage", "Stationnement"],
            'Vie quotidienne': ["Alimentation - Supermarché", "Frais animaux", "Coiffeur, soins", "Habillement", "Achat, shopping", "Jeux Vidéo", "Frais postaux", "Achat multimédias - Hight tech", "Autres", "Aide-à-domicile", "Cadeaux", "Vie quotidienne - Autres"],
            'Enfant(s)': ["Pension alimentaire", "Crèche, baby-sitter", "Scolarité, études", "Argent de poche", "Activités enfants"],
        }

        buttonLabels = {key: sorted(buttonLabels[key]) for key in sorted(buttonLabels.keys())}

        trierDonnee = OperationCategoriser(data, buttonLabels, cheminFileJson)
        results = trierDonnee.AfficherFenetreAvecBoutons()

        if dossier is not None:
            SaveDictToJson(results, f"Bilan/Archives/{dossier}/{year}.json")

            compteCourant = (dossier == "Compte Chèques")
            GenererRapports(results, dossier, year, compteCourant)
            ExcelReportGenerator(results, f"Bilan/{dossier}/{year}/Bilan {year}.xlsx")

    elif (data is not None) and (extension == "Json"):
        year = CreerNomFichier(data)
        if dossier is not None:
            compteCourant = (dossier == "Compte Chèques")
            GenererRapports(data, dossier, year, compteCourant)


def GenererGraphiquesParMois(chartGen, data, dossier, year, compteCourant):
    """
    Génère les graphiques pour chaque mois à partir des données fournies.

    Args:
        chartGen (GraphiqueFinancier): Instance du générateur de graphique.
        data (dict): Données financières du fichier JSON.
        dossier (str): Nom du dossier (ex: Compte Chèques, Livret A).
        year (str): Année extraite du fichier.
        compteCourant (bool): Indique si le compte est un compte courant ou non.
    """
    allmonth = DiviserParMois(data=data)
    for yearMonth, transaction in allmonth.items():
        CheminFile = f"Bilan/{dossier}/{year}/{yearMonth}.html"

        chartGen.SetData(transaction)
        chartGen.SetOutputFile(CheminFile)
        chartGen.GraphiqueAutomatique(compteCourant=compteCourant)

def GenererGraphiquesAnnuel(chartGen, data, CheminFile, compteCourant):
    """
    Génère le graphique annuel pour les données fournies.

    Args:
        chartGen (GraphiqueFinancier): Instance du générateur de graphique.
        data (dict): Données financières du fichier JSON.
        dossier (str): Nom du dossier (ex: Compte Chèques, Livret A).
        year (str): Année extraite du fichier.
        compteCourant (bool): Indique si le compte est un compte courant ou non.
    """
    chartGen.SetData(data)
    chartGen.SetOutputFile(CheminFile)
    chartGen.GraphiqueAutomatique(compteCourant=compteCourant)

def CompteLivretAllUpdateGraphiques():
    """
    Met à jour les graphiques pour tous les fichiers JSON des comptes "Compte Chèques" et "Livret A".
    """
    dossiers = ["Compte Chèques", "Livret A"]

    for dossier in dossiers:
        allFileJson = RecupererFichiersJson(f"Bilan/Archives/{dossier}")

        for fileJson in allFileJson:
            data = LoadDictFromJson(fileJson)
            year = CreerNomFichier(data)

            CheminFile = f"Bilan/{dossier}/{year}/Bilan {year}.html"

            # Génération des graphiques
            compteCourant = (dossier == "Compte Chèques")
            chartGen = GraphiqueFinancier(data, CheminFile)

            # Générer le graphique annuel
            GenererGraphiquesAnnuel(chartGen, data, CheminFile, compteCourant)

            # Générer les graphiques mensuels
            GenererGraphiquesParMois(chartGen, data, dossier, year, compteCourant)


if __name__ == "__main__":
    # CompteLivretAllUpdateGraphiques()
    CompteLivret()