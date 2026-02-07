from bank_accounts.bnp_paribas.data_extractor import ExcelDataExtractor
from bank_accounts.bnp_paribas.excel_report_generator import (
    ExcelReportGenerator as BnpParibasExcelReportGenerator,
)
from bank_accounts.bnp_paribas.financial_chart import FinancialChart
from bank_accounts.bnp_paribas.operation_categorizer import OperationCategorizer
from bank_accounts.trade_republic.excel_report_generator import (
    ExcelReportGenerator as TradeRepublicExcelReportGenerator,
)
from bank_accounts.trade_republic.portfolio_performance import PortfolioPerformance
from bank_accounts.trade_republic.portfolio_visualizer import PortfolioVisualizer
from bank_accounts.trade_republic.trade_republic_importer import TradeRepublicImporter
from database.bnp_paribas_database import BnpParibasDatabase
from wealth_management.wealth_dashboard import WealthDashboard


def upgrade_account(db_path: str, save_file_path: str, initial_dir: str):
    """
    Extrait les données Excel, les intègre à la base de données et génère les rapports.
    
    Args:
        - db_path (str) : Chemin vers la base de données SQLite.
        - save_file_path (str) : Dossier de destination pour les rapports générés.
        - initial_dir (str) : Dossier contenant les fichiers Excel sources.
    """
    # Extraction des données Excel
    data_extractor = ExcelDataExtractor(initial_dir)
    data = data_extractor.run_extraction()
    
    if data is not None:
        db = BnpParibasDatabase(db_path)
        db.add_raw_data(data)

    # Catégorisation et génération des rapports visuels et Excel
    categorizer = OperationCategorizer(db_path)
    categorizer.categorize()
    
    chart_generator = FinancialChart(db_path, save_file_path)
    chart_generator.generate_all_reports()
    
    excel_generator = BnpParibasExcelReportGenerator(db_path, save_file_path)
    excel_generator.generate_all_reports()

def process_bnp_paribas_global(db_path: str, source_db_path: str, target_db_path: str, save_file_path: str):
    """
    Fusionne plusieurs bases de données bancaires et génère un rapport consolidé.
    
    Args:
        - db_path (str) : Chemin de la base de données finale fusionnée.
        - source_db_path (str) : Chemin de la première base source.
        - target_db_path (str) : Chemin de la deuxième base source.
        - save_file_path (str) : Dossier de destination pour les rapports.
    """
    # Fusion des bases de données de différents comptes
    BnpParibasDatabase.merge_bank_databases(source_db_path, target_db_path, db_path)
    
    chart_generator = FinancialChart(db_path, save_file_path)
    chart_generator.generate_all_reports()
    
    excel_generator = BnpParibasExcelReportGenerator(db_path, save_file_path)
    excel_generator.generate_all_reports()

def process_trade_republic(db_path: str, root_path: str):
    """
    Gère l'importation et l'analyse des données de investissement Trade Republic.
    
    Args:
        - db_path (str) : Chemin vers la base de données bourse.
        - root_path (str) : Dossier racine pour la sauvegarde des bilans.
    """
    # Processus d'importation Trade Republic
    importer = TradeRepublicImporter(db_path)
    importer.run_full_import_process()

    # Calcul de la performance du portefeuille
    performance_engine = PortfolioPerformance(db_path)
    performance_engine.calculate_performance()

    # Visualisation et rapport Excel
    visualizer = PortfolioVisualizer(db_path, root_path)
    visualizer.generate_performance_report()

    excel_generator = TradeRepublicExcelReportGenerator(db_path, root_path)
    excel_generator.generate_global_report()

def main():
    """
    Point d'entrée principal de l'application de gestion de patrimoine.
    """
    # --- [ Configuration BNP Paribas ] ---
    upgrade_account("data/bnp paribas/compte chèques/compte chèques.db", "Bilan/Bnp Paribas/Compte Chèques/", "data/bnp paribas/Compte Chèques/")
    upgrade_account("data/bnp paribas/livret A/livret A.db", "Bilan/Bnp Paribas/Livret A/", "data/bnp paribas/livret A/")
    process_bnp_paribas_global("data/bnp paribas/all/all.db", "data/bnp paribas/compte chèques/compte chèques.db", "data/bnp paribas/livret A/livret A.db", "Bilan/Bnp Paribas/All/")

    # --- [ Configuration Trade Republic ] ---
    process_trade_republic("data/bourse/Trade Republic.db", "Bilan/Trade Repubic/")

    # --- [ Dashboard de Patrimoine Global ] ---
    wealth_engine = WealthDashboard(
        "data/bnp paribas/compte chèques/compte chèques.db", 
        "data/bnp paribas/livret A/livret A.db", 
        "data/bourse/Trade Republic.db"
    )
    wealth_engine.generate_wealth_report("Bilan/")

if __name__ == "__main__":
    main()