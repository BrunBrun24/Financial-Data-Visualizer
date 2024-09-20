from .modules.TradeRepublicPerformance import TradeRepublicPerformance
from .modules.TradeRepublicFileExcelJson import TradeRepublicFileExcelJson


def CreateData():
    """
    Création du fichier Excel et des fichiers Json sur la bourse
    """
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
    bourse.EnregistrerDataFrameEnJson(bourse.GetEvolutionPrixPortefeuille(False), "Bilan/Archives/Bourse/Portefeuille.json")

def UpdateData():
    bourse = TradeRepublicPerformance("Bilan/Archives/Bourse/Transactions.json")
    bourse.EnregistrerDataFrameEnJson(bourse.GetEvolutionPrixPortefeuille(False), "Bilan/Archives/Bourse/Portefeuille.json")
