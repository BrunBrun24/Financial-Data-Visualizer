from RecuperationDesDonnees import DataExtractor
from TraitementDesDonneesTkinter import OperationCategoriser
from GraphiquesPlotly import GraphiqueFinancier
from CreationFichierExcel import ExcelReportGenerator

from FonctionsSecondaires import ExtraireAnnee
from FonctionsSecondaires import DiviserParMois
from FonctionsSecondaires import SaveDictToJson
from FonctionsSecondaires import CreerNomFichier


def Main():
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


if __name__  == "__main__":
    Main()