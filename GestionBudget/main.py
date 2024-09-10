from RecuperationDesDonnees import DataExtractor
from TraitementDesDonneesTkinter import OperationCategoriser
from GraphiquesPlotly import GraphiqueFinancier
from CreationFichierExcel import ExcelReportGenerator
from PortefeuilleBoursier import TradeRepublicPerformance
from TradeRepublicExcelJson import TradeRepublicFileExcelJson

from FonctionsSecondaires import *


def CompteLivret():
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
            'Banque': ["Epargne", "Remboursement emprumt", "Frais bancaires", "Prélèvement carte débit différé", "Banques - Autres"],
            "Logement": ["Logement - Autres", "Electricité, gaz", "Eau", "Chauffage", "Loyer", "Prêt Immobiler", "Bricolage et jardinage", "Assurance habitation", "Logement - Autres", "Mobilier, électroménager, déco"],
            'Loisir et sorties': ["Voyages, vacances", "Restaurants - Bars", "Diversements, sortie culturelles", "Sports", "Soirée - Sortie", "Loisirs et sorties - Autres"],
            'Santé': ["Medecin", "Pharmacie", "Dentiste", "Mutuelle", "Opticien", "Hôpital"],
            'Transports et véhicules': ["Assurance véhicule", "Crédit auto", "Carburant", "Entretient véhicule", "Transport en commun", "Billet d'avion, Billet de train", "Taxi, VTC", "Location de véhicule", "Péage", "Stationnement"],
            'Vie quotidienne': ["Alimentation - Supermarché", "Frais animaux", "Coiffeur, soins", "Habillement", "Achat, shopping", "Jeux Vidéo", "Frais postaux", "Achat multimédias - Hight tech", "Autres", "Aide-à-domicile", "Cadeaux", "Vie quotidienne - Autres"],
            'Enfant(s)': ["Pension alimentaire", "Crèche, baby-sitter", "Scolarité, études", "Argent de poche", "Activités enfants"],
        }

        # Trier les clés du dictionnaire
        sortedKeys = sorted(buttonLabels.keys())
        # Créer un nouveau dictionnaire avec les clés triées et les valeurs triées
        buttonLabels = {key: sorted(buttonLabels[key]) for key in sortedKeys}

        trierDonnee = OperationCategoriser(data, buttonLabels, cheminFileJson)
        results = trierDonnee.AfficherFenetreAvecBoutons()

        if dossier is not None:
            SaveDictToJson(results, f"Bilan/Archives/{dossier}/{year}.json")

            if dossier == "Compte Chèques":
                chartGen = GraphiqueFinancier(results, f"Bilan/{dossier}/{year}/Bilan {year}.html")
                chartGen.GraphiqueAutomatique(compteCourant=True)

                # Graphique pour chaques mois
                allmonth = DiviserParMois(results)
                for yearMonth, transaction in allmonth.items():
                    chartGen.SetData(transaction)
                    chartGen.SetOutputFile(f"Bilan/{dossier}/{year}/{yearMonth}.html")
                    chartGen.GraphiqueAutomatique(compteCourant=True)

                ExcelReportGenerator(results, f"Bilan/{dossier}/{year}/Bilan {year}.xlsx")
            else:
                chartGen = GraphiqueFinancier(results, f"Bilan/{dossier}/{year}/Bilan {year}.html")
                chartGen.GraphiqueAutomatique(compteCourant=False)

                # Graphique pour chaques mois
                allmonth = DiviserParMois(data=results)
                for yearMonth, transaction in allmonth.items():
                    chartGen.SetData(transaction)
                    chartGen.SetOutputFile(f"Bilan/{dossier}/{year}/{yearMonth}.html")
                    chartGen.GraphiqueAutomatique(compteCourant=False)

    elif (data is not None) and (extension == "Json"):
        year = CreerNomFichier(data)

        if dossier is not None:
            CheminFile = f"Bilan/{dossier}/{year}/Bilan {year}.html"
            
            if dossier == "Compte Chèques":
                chartGen = GraphiqueFinancier(data, CheminFile)
                chartGen.GraphiqueAutomatique(compteCourant=True)

                # Graphique pour chaques mois
                allmonth = DiviserParMois(data=data)
                for yearMonth, transaction in allmonth.items():
                    CheminFile = f"Bilan/{dossier}/{year}/{yearMonth}.html"

                    chartGen.SetData(transaction)
                    chartGen.SetOutputFile(CheminFile)
                    chartGen.GraphiqueAutomatique(compteCourant=True)

            else:
                chartGen = GraphiqueFinancier(results, CheminFile)
                chartGen.GraphiqueAutomatique(compteCourant=False)

                # Graphique pour chaques mois
                allmonth = DiviserParMois(data=data)
                for yearMonth, transaction in allmonth.items():
                    CheminFile = f"Bilan/{dossier}/{year}/{yearMonth}.html"

                    chartGen.SetData(transaction)
                    chartGen.SetOutputFile(CheminFile)
                    chartGen.GraphiqueAutomatique(compteCourant=False)

def Bourse():
    directory = f"Bilan/Archives/Bourse/Fichiers pdf/"
    tickerMapping = {
        'Hermes': 'RMS.PA',
        'Air': 'AI.PA',
        'TotalEnergies': 'TTE.PA',
        "Oréal": 'OR.PA',
        'ACCOR': 'AC.PA',
        'Danone': 'BN.PA',
        'Pernod Ricard': 'RI.PA',
        'LVMH': 'MC.PA',
        'Sodexo': 'SW.PA',
        'Schneider Electric': 'SU.PA',
        'Capgemini': 'CAP.PA',
        'Cap gemini': 'CAP.PA',
        'iShares Physical Metals PLC': 'PHYMF',
        'iShs VII-Core S&P': 'CSPX.L',
        'AbbVie': 'ABBV',
        'Alphabet': 'GOOGL',
        'Salesforce': 'CRM',
        'Amazon': 'AMZN',
        'Apple': 'AAPL',
        'Arista Networks': 'ANET',
        'Blackrock': 'BLK',
        'Broadcom': 'AVGO',
        'Cadence Design Systems': 'CDNS',
        'Coca-Cola': 'KO',
        'Meta Platforms': 'META',
        'Fortinet': 'FTNT',
        'Intuit': 'INTU',
        'Johnson & Johnson': 'JNJ',
        'KLA Corp': 'KLAC',
        'Lam Research': 'LRCX',
        'Eli Lilly': 'LLY',
        'Mastercard': 'MA',
        "McDonald's": 'MCD',
        'Microsoft': 'MSFT',
        'Novo-Nordisk': 'NVO',
        'NVIDIA': 'NVDA',
        'Oracle': 'ORCL',
        'Palo Alto Networks': 'PANW',
        'PepsiCo': 'PEP',
        'Procter & Gamble': 'PG',
        'Roper Technologies': 'ROP',
        'S&P Global': 'SPGI',
        'Synopsys': 'SNPS',
        'UnitedHealth': 'UNH',
        'VISA': 'V',
        'Walmart': 'WMT',
        'Cintas': 'CTAS'
    }

    TradeRepublic = TradeRepublicFileExcelJson(directoryData=directory, tickerMapping=tickerMapping)

    # Liste des opérations à effectuer
    operations = [
        {"directory": (directory + "Ordres d'achats/data"), "directoryRename": (directory + "Ordres d'achats"), "createFunction": TradeRepublic.RenameAndMoveOrdresAchats},
        {"directory": (directory + "Dépôts d'argents/data"), "directoryRename": (directory + "Dépôts d'argents"), "createFunction": TradeRepublic.RenameAndMoveDepotRetraitArgentInteret},
        {"directory": (directory + "Dividendes/data"), "directoryRename": (directory + "Dividendes"), "createFunction": TradeRepublic.RenameAndMoveDividendes},
        {"directory": (directory + "Interets/data"), "directoryRename": (directory + "Interets"), "createFunction": TradeRepublic.RenameAndMoveDepotRetraitArgentInteret},
        {"directory": (directory + "Retraits d'argents/data"), "directoryRename": (directory + "Retraits d'argents"), "createFunction": TradeRepublic.RenameAndMoveDepotRetraitArgentInteret},
        {"directory": (directory + "Ordres de ventes/data"), "directoryRename": (directory + "Ordres de ventes/FacturesVentes"), "createFunction": TradeRepublic.RenameAndMoveOrdresVentes},
    ]

    # Boucle pour traiter chaque type de donnée et créer les feuilles Excel correspondantes
    for operation in operations:
        TradeRepublic.ProcessPdf(operation["directory"], operation["directoryRename"], operation["createFunction"])
        
    TradeRepublic.DownloadDataAndCreateFileExcel("Bilan/Bourse/Récapitulatif des gains.xlsx", False)

    bourse = TradeRepublicPerformance("Bilan/Archives/Bourse/Transactions.json")
    EnregistrerDataFrameEnJson(bourse.GetEvolutionPrixPortefeuille(False), "Bilan/Archives/Bourse/Portefeuille.json")


if __name__  == "__main__":
    # CompteLivret()
    Bourse()