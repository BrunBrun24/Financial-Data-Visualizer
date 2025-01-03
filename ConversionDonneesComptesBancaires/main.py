from comptesBancaires.tradeRepublic.tradeRepublicFileExcelJson import TradeRepublicFileExcelJson
from comptesBancaires.bnpParibas.dataExtractor import DataExtractor
from comptesBancaires.bnpParibas.operationCategoriser import OperationCategoriser
from comptesBancaires.bnpParibas.excelReportGenerator import ExcelReportGenerator
from comptesBancaires.bnpParibas.graphiqueFinancier import GraphiqueFinancier
from comptesBancaires.bnpParibas.fonctionsSecondaires import *


def TradeRepublic():
    directory = f"data/Bourse/"
    tickerMapping = {
        'Hermes': 'RMS.PA',
        'Air Liquide': 'AI.PA',
        'TotalEnergies': 'TTE.PA',
        "Oréal": 'OR.PA',
        "L'Oreal": 'OR.PA',
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
        'KLA-Tencor': 'KLAC',
        'Lam Research': 'LRCX',
        'Eli Lilly': 'LLY',
        'Mastercard': 'MA',
        "McDonald's": 'MCD',
        'Microsoft': 'MSFT',
        'Novo-Nordisk': 'NVO',
        'Novo Nordisk': 'NVO',
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
        'Cintas': 'CTAS',
        'Pluxee': 'PLX.PA',
    }

    TradeRepublic = TradeRepublicFileExcelJson(directoryData=directory, tickerMapping=tickerMapping)
    TradeRepublic.CreateFileExcelJson("Bilan/Bourse/Récapitulatif des gains.xlsx")

def BnpParibas():
    pass



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

    dossierContenantLesDonnees = "data/"
    extracteur = DataExtractor(initialDir=dossierContenantLesDonnees)
    data, extension, dossier = extracteur.SelectAndExtractData()

    if (data is not None) and (extension == "Excel"):
        year = ExtraireAnnee(data)
        cheminFileJson = dossierContenantLesDonnees + f"{dossier}/{year}.json"

        trierDonnee = OperationCategoriser(data, cheminFileJson)
        results = trierDonnee.AfficherFenetreAvecBoutons()

        if dossier is not None:
            SaveDictToJson(results, (dossierContenantLesDonnees + f"{dossier}/{year}.json"))

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
        allFileJson = RecupererFichiersJson(f"src/data/{dossier}")

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
    TradeRepublic()
    # BnpParibas()
    # CompteLivret()
    # CompteLivretAllUpdateGraphiques()