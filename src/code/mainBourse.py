from .modules.TradeRepublicPerformance import TradeRepublicPerformance
from .modules.TradeRepublicFileExcelJson import TradeRepublicFileExcelJson


def CreateData():
    """
    Création du fichier Excel et des fichiers Json sur la bourse
    """
    
    directory = f"Bilan/Archives/Bourse/Fichiers pdf/"
    tickerMapping = {
        'Hermes': 'RMS.PA',
        'Air Liquide': 'AI.PA',
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
    TradeRepublic.DownloadDataAndCreateFileExcel("Bilan/Bourse/Récapitulatif des gains.xlsx")

def Portefeuille():
    portfolioPercentage = [
        [{'CSSPX.MI': 100}, 'S&P 500'],

        [{'IGLN.L': 27.27272727272727, 'TTE.PA': 9.090909090909092, 'MC.PA': 9.090909090909092, 'OR.PA': 9.090909090909092, 'AC.PA': 9.090909090909092,
        'BN.PA': 9.090909090909092, 'SW.PA': 9.090909090909092, 'AI.PA': 9.090909090909092, 'SU.PA': 9.090909090909092}, '1er Portefeuille'],

        [{'MSFT': 7.142857142857142, 'AAPL': 7.142857142857142, 'CDNS': 7.142857142857142, 'PANW': 7.142857142857142, 'AVGO': 7.142857142857142,
        'ANET': 7.142857142857142, 'CTAS': 7.142857142857142, 'INTU': 7.142857142857142, 'KLAC': 7.142857142857142, 'V': 7.142857142857142,
        'FTNT': 7.142857142857142, 'NVO': 7.142857142857142, 'SNPS': 7.142857142857142, 'LLY': 7.142857142857142}, '2ème Portefeuille'],

        [{'PANW': 7.6923076923076925, 'V': 7.6923076923076925, 'AVGO': 7.6923076923076925, 'MSFT': 7.6923076923076925, 'NVO': 7.6923076923076925,
        'ANET': 7.6923076923076925, 'INTU': 7.6923076923076925, 'FTNT': 7.6923076923076925, 'AMZN': 7.6923076923076925, 'CNSWF': 7.6923076923076925,
        'BKNG': 7.6923076923076925, 'COST': 7.6923076923076925, 'CRM': 7.6923076923076925}, '4ème Portefeuille'],
    ]

    bourse = TradeRepublicPerformance("Bilan/Archives/Bourse/")
    bourse.SetPortfolioPercentage(portfolioPercentage)
    # bourse.ReplicationDeMonPortefeuille()
    bourse.DollarCostAveraging()
    bourse.PlotlyInteractive("Bilan/Bourse/", "Bilan Portefeuille.html")