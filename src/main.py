from database.compte_titre import CompteTireBdd
from comptes_bancaires.bnp_paribas.excel_report_generator import ExcelReportGenerator
from comptes_bancaires.bnp_paribas.graphique_financier import GraphiqueFinancier
from comptes_bancaires.bnp_paribas.operation_categoriser import OperationCategoriser
from comptes_bancaires.bnp_paribas.data_extractor import select_and_extract_data


def compte_upgrade(db_path: str, save_file_path: str, initial_dir: str, two_last_years: bool):
    data = select_and_extract_data(initial_dir)
    if data is not None:
        bdd = CompteTireBdd(db_path)
        bdd.ajouter_donnees_brutes(data)
 
    operation_categoriser = OperationCategoriser(db_path)
    operation_categoriser.categoriser()
    graphique_financier = GraphiqueFinancier(db_path, save_file_path)
    graphique_financier.main(two_last_years)
    excel_report_generator = ExcelReportGenerator(db_path, save_file_path)
    excel_report_generator.main(two_last_years)

def main():
    # Créez les graphiques et les fichier Excel seulement pour les 2 dernières années
    two_last_years = True

    compte_upgrade("data/Compte Chèques/Compte Chèques.db", "Bilan/Compte Chèques/", "data/Compte Chèques/", two_last_years)
    compte_upgrade("data/livret A/livret A.db", "Bilan/livret A/", "data/livret A/", two_last_years)

if __name__ == "__main__":
    main()