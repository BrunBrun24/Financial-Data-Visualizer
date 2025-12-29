from bank_accounts.bnp_paribas.data_extractor import select_and_extract_data
from bank_accounts.bnp_paribas.excel_report_generator import ExcelReportGenerator
from bank_accounts.bnp_paribas.financial_chart import GraphiqueFinancier
from bank_accounts.bnp_paribas.operation_categorizer import OperationCategorizer
from bank_accounts.trade_republic.portfolio_performance import PortfolioPerformance
from bank_accounts.trade_republic.portfolio_visualizer import PortfolioVisualizer
from bank_accounts.trade_republic.trade_republic_importer import (
    TradeRepublicImporter,
)
from database.bnp_paribas_database import BnpParibasDatabase


def compte_upgrade(db_path: str, save_file_path: str, initial_dir: str, two_last_years: bool):
    data = select_and_extract_data(initial_dir)
    if data is not None:
        bdd = BnpParibasDatabase(db_path)
        bdd.add_raw_data(data)
 
    operation_categoriser = OperationCategorizer(db_path)
    operation_categoriser.categorize()
    graphique_financier = GraphiqueFinancier(db_path, save_file_path)
    graphique_financier.generate_all_reports(two_last_years)
    excel_report_generator = ExcelReportGenerator(db_path, save_file_path)
    excel_report_generator.generate_all_reports(two_last_years)

def bnp_paribas_all_compte(db_path: str, source_db_path: str, target_db_path: str, save_file_path: str, two_last_years: bool):
    BnpParibasDatabase.merge_bank_databases(source_db_path, target_db_path, db_path)
    graphique_financier = GraphiqueFinancier(db_path, save_file_path)
    graphique_financier.generate_all_reports(two_last_years)
    excel_report_generator = ExcelReportGenerator(db_path, save_file_path)
    excel_report_generator.generate_all_reports(two_last_years)

def trade_republic(db_path: str, root_path: str):
    trade_republic_file = TradeRepublicImporter(db_path)
    trade_republic_file.run_full_import_process()

    portfolio_performance = PortfolioPerformance(db_path)
    portfolio_performance.calculate_performance()

    portfolio_visualizer = PortfolioVisualizer(db_path, root_path)
    portfolio_visualizer.generate_performance_report()

def main():
    # Créez les graphiques et les fichier Excel seulement pour les 2 dernières années
    two_last_years = False

    compte_upgrade("data/bnp paribas/compte chèques/compte chèques.db", "Bilan/Bnp Paribas/Compte Chèques/", "data/bnp paribas/Compte Chèques/", two_last_years)
    compte_upgrade("data/bnp paribas/livret A/livret A.db", "Bilan/Bnp Paribas/Livret A/", "data/bnp paribas/livret A/", two_last_years)
    bnp_paribas_all_compte("data/bnp paribas/all/all.db", "data/bnp paribas/compte chèques/compte chèques.db", "data/bnp paribas/livret A/livret A.db", "Bilan/Bnp Paribas/All/", two_last_years)

    trade_republic("data/bourse/Trade Republic.db", "Bilan/Trade Repubic/")
    

if __name__ == "__main__":
    main()