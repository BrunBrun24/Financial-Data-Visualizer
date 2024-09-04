import os
import json
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go



def transformerDossierJsonEnDataFrame(cheminDossier: str) -> pd.DataFrame:
    """
    Charge tous les fichiers JSON d'un dossier, les combine en un DataFrame, avec 'DATE D'OPÉRATION' comme index,
    et trie les données par cet index.

    Args:
        cheminDossier: Chemin vers le dossier contenant les fichiers JSON.

    Returns:
        df: DataFrame combiné avec les transactions de tous les fichiers, 'DATE D'OPÉRATION' en index,
            et les catégories ajoutées comme colonne 'Catégorie', trié par 'DATE D'OPÉRATION'.
    """
    # Assertions pour vérifier les types d'entrées
    assert isinstance(cheminDossier, str), f"Le cheminDossier doit être une chaîne de caractères: ({cheminDossier})"
    assert os.path.isdir(cheminDossier), f"Le chemin spécifié n'est pas un dossier valide: ({cheminDossier})"
    
    # Initialiser une liste pour stocker les données
    lignes = []
    
    # Parcourir tous les fichiers JSON dans le dossier
    for fichier in os.listdir(cheminDossier):
        if fichier.endswith('.json'):
            cheminFichier = os.path.join(cheminDossier, fichier)
            
            # Charger le contenu du fichier JSON
            with open(cheminFichier, 'r', encoding='UTF-8') as f:
                data = json.load(f)
                
                # Parcourir chaque catégorie et ses transactions
                for categorie, transactions in data.items():
                    assert isinstance(transactions, list), f"Les transactions pour chaque catégorie doivent être une liste: ({transactions})"
                    for transaction in transactions:
                        assert isinstance(transaction, dict), f"Chaque transaction doit être un dictionnaire: ({transaction})"
                        assert "DATE D'OPÉRATION" in transaction, f"La clé 'DATE D'OPÉRATION' est manquante dans la transaction: ({transaction})"
                        
                        # Ajouter la catégorie comme une nouvelle colonne
                        transaction['Catégorie'] = categorie
                        lignes.append(transaction)
    
    # Convertir en DataFrame
    df = pd.DataFrame(lignes)
    
    # Mettre 'DATE D'OPÉRATION' en tant qu'index
    df.set_index("DATE D'OPÉRATION", inplace=True)
    
    # Trier le DataFrame par l'index 'DATE D'OPÉRATION'
    df.sort_index(inplace=True)
    
    return df



def calculPatrimoineDeDepartCompteCourant(argentCompteCourant: float, dossierCompteCourant: str) -> float:
    """
    Calculer le patrimoine initial basé sur les transactions trouvées dans les fichiers JSON.
    
    Args:
        argentCompteCourant: Argent du Compte courant le 2022-10-27.
        dossierCompteCourant: Chemin vers le dossier contenant les fichiers JSON pour le Compte Courant.

    Returns:
        argentCompteCourantInitial: Montant initial du compte courant.
    """
    
    assert isinstance(argentCompteCourant, (int, float)), f"La variable argentCompteCourant doit être un nombre => ({argentCompteCourant})"
    assert isinstance(dossierCompteCourant, str), f"La variable dossierCompteCourant doit être une chaîne de caractère: ({dossierCompteCourant})"
    assert os.path.exists(dossierCompteCourant), f"Le dossier spécifié n'existe pas: {dossierCompteCourant}"
    
    # Parcourir les fichiers JSON du Compte Courant
    for fichier in os.listdir(dossierCompteCourant):
        if fichier.endswith(".json"):
            with open(os.path.join(dossierCompteCourant, fichier), 'r', encoding="UTF-8") as f:
                data = json.load(f)
                
                # Parcourir toutes les catégories (Investissement, Revenus, etc.)
                for categorie, operations in data.items():
                    for operation in operations:
                        # Ajuster le montant du Compte Courant basé sur chaque opération
                        argentCompteCourant += operation["MONTANT"]
    
    return argentCompteCourant

def calculPatrimoineDeDepartLivretA(argentLivretA: float, dossierLivretA: str) -> float:
    """
    Calculer le patrimoine initial basé sur les transactions trouvées dans les fichiers JSON.
    
    Args:
        argentLivretA: Argent du Livret A le 2022-10-27.
        dossierLivretA: Chemin vers le dossier contenant les fichiers JSON pour le Livret A.

    Returns:
        argentLivretAInitial: Montant initial du Livret A.
    """
    
    assert isinstance(argentLivretA, (int, float)), f"La variable argentLivretA doit être un nombre: ({argentLivretA})"
    assert isinstance(dossierLivretA, str), f"La variable dossierLivretA doit être une chaîne de caractère: ({dossierLivretA})"
    assert os.path.exists(dossierLivretA), f"Le dossier spécifié n'existe pas: {dossierLivretA}"
    
    # Parcourir les fichiers JSON du Livret A
    for fichier in os.listdir(dossierLivretA):
        if fichier.endswith(".json"):
            with open(os.path.join(dossierLivretA, fichier), 'r', encoding="UTF-8") as f:
                data = json.load(f)
                
                # Parcourir toutes les catégories (Investissement, Revenus, etc.)
                for categorie, operations in data.items():
                    for operation in operations:
                        # Ajuster le montant du Livret A basé sur chaque opération
                        argentLivretA += operation["MONTANT"]


    return argentLivretA


def evolutionDuPatrimoineSurLeCompteCourant(patrimoine: pd.DataFrame, argentCompteCourant: float, dossierCompteCourant: str) -> pd.DataFrame:
    """
    Calcule l'évolution du patrimoine quotidiennement pour le Compte Courant basé sur les transactions trouvées dans les fichiers JSON.
    
    Args:
        patrimoine: DataFrame contenant aucune ou plusieurs colonnes avec pour index des dates (YYYY-MM-DD) et comme valeur des float ou int.
        argentCompteCourant: Argent du Compte courant le 2022-10-27.
        dossierCompteCourant: Chemin vers le dossier contenant les fichiers JSON pour le Compte Courant.

    Returns:
        patrimoine: DataFrame avec l'évolution du patrimoine quotidiennement pour le Compte Courant.
    """

    assert isinstance(patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({patrimoine})"
    assert isinstance(argentCompteCourant, (int, float)), f"La variable argentCompteCourant doit être un nombre: ({argentCompteCourant})"
    assert isinstance(dossierCompteCourant, str), f"La variable dossierCompteCourant doit être une chaîne de caractère: ({dossierCompteCourant})"
    assert os.path.exists(dossierCompteCourant), f"Le dossier spécifié n'existe pas: {dossierCompteCourant}"
    
    # Créer la colonne "Compte Courant" si elle n'existe pas déjà
    if 'Compte Courant' not in patrimoine.columns:
        patrimoine['Compte Courant'] = pd.Series(dtype=float)

    transactions = transformerDossierJsonEnDataFrame(dossierCompteCourant)

    motif_date = r'^\d{4}-\d{2}-\d{2}$'
    # Vérifier que toutes les valeurs de l'index correspondent au motif de date
    assert all(re.match(motif_date, date) for date in transactions.index), "L'index ne comporte pas des dates au format 'YYYY-MM-DD'."
    assert("MONTANT" in transactions), "(MONTANT) n'est pas le nom d'une colonne dans (transactions)"
    
    for date, row in transactions.iterrows():
        # Evolution de l'argent
        argentCompteCourant += row["MONTANT"]
        # Ajout de la date et du prix
        patrimoine.loc[date, "Compte Courant"] = argentCompteCourant

    # Remplacer les valeurs manquantes par la valeur précédente puis les suivantes
    patrimoine = patrimoine.fillna(method='ffill').fillna(method='bfill')

    return patrimoine

def evolutionDuPatrimoineSurLeLivretA(patrimoine: pd.DataFrame, argentLivretA: float, dossierLivretA: str) -> pd.DataFrame:
    """
    Calcule l'évolution du patrimoine quotidiennement pour le Livret A basé sur les transactions trouvées dans les fichiers JSON.
    
    Args:
        patrimoine: DataFrame contenant aucune ou plusieurs colonnes avec pour index des dates (YYYY-MM-DD) et comme valeur des float ou int.
        argentLivretA: Argent du Livret A le 2022-10-27.
        dossierLivretA: Chemin vers le dossier contenant les fichiers JSON pour le Livret A.

    Returns:
        patrimoine: DataFrame avec l'évolution du patrimoine quotidiennement pour le Livret A.
    """

    assert isinstance(patrimoine, pd.DataFrame), f"La variable patrimoine doit être une DataFrame: ({patrimoine})"
    assert isinstance(argentLivretA, (int, float)), f"La variable argentLivretA doit être un nombre: ({argentLivretA})"
    assert isinstance(dossierLivretA, str), f"La variable dossierLivretA doit être une chaîne de caractère: ({dossierLivretA})"
    assert os.path.exists(dossierLivretA), f"Le dossier spécifié n'existe pas: {dossierLivretA}"
    
    # Créer la colonne "Livret A" si elle n'existe pas déjà
    if 'Livret A' not in patrimoine.columns:
        patrimoine['Livret A'] = pd.Series(dtype=float)

    transactions = transformerDossierJsonEnDataFrame(dossierLivretA)

    motif_date = r'^\d{4}-\d{2}-\d{2}$'
    # Vérifier que toutes les valeurs de l'index correspondent au motif de date
    assert all(re.match(motif_date, date) for date in transactions.index), "L'index ne comporte pas des dates au format 'YYYY-MM-DD'."
    assert("MONTANT" in transactions), "(MONTANT) n'est pas le nom d'une colonne dans (transactions)"
    
    for date, row in transactions.iterrows():
        # Evolution de l'argent
        argentLivretA += row["MONTANT"]
        # Ajout de la date et du prix
        patrimoine.loc[date, "Livret A"] = argentLivretA

    # Remplacer les valeurs manquantes par la valeur précédente puis les suivantes
    patrimoine = patrimoine.fillna(method='ffill').fillna(method='bfill')
    
    return patrimoine


def plotHistograms(df: pd.DataFrame) -> go.Figure:
    """
    Crée un graphique histogramme pour les données du DataFrame.
    
    Args:
        df: DataFrame contenant les données à visualiser.
    
    Returns:
        fig: Objet Figure de Plotly contenant les histogrammes.
    """

    print(df)
    
    # Remplacer les valeurs négatives par 0 dans la colonne 'Montant'
    df['Montant'] = df['Montant'].clip(lower=0)
    # Trier le DataFrame en fonction de la colonne 'Montant'
    df = df.sort_values(by='Montant', ascending=False)
    
    # Créer le graphique
    fig = px.bar(
        df, x='Date', y='Montant',
        color='Type',
        labels={'Date': 'Date', 'Montant': 'Montant', 'Type': 'Type'}
    )

    # Mettre à jour la mise en page
    fig.update_layout(
        title="Histogramme des Transactions",
        xaxis_title="Date",
        yaxis_title="Montant",
        height=900,
        showlegend=True
    )
    
    fig.show()
    return fig


def mois(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fonction pour ajouter les dates du début de chauqe mois dans la période couverte
    par le DataFrame, garder seulement ces dates,
    et compléter les valeurs manquantes par propagation des valeurs précédentes et suivantes.
    
    Args:
        df: DataFrame avec des dates comme index et plusieurs colonnes de valeurs.
    
    Returns:
        DataFrame avec les dates du 1er de chaque mois ajoutées, les autres dates supprimées,
        la première et dernière date incluses, et les valeurs complétées.
    """
    # Convertir la colonne Date en datetime
    df['Date'] = pd.to_datetime(df.index)
    # Définir la colonne Date comme index
    df.set_index('Date', inplace=True)
    # Créer une série de toutes les dates du début de chaque mois dans la période de données
    all_month_starts = pd.date_range(start=df.index.min().replace(day=1),
                                    end=df.index.max().replace(day=1),
                                    freq='MS')
    # Réindexer le DataFrame pour inclure toutes les dates du début de chaque mois
    df = df.reindex(all_month_starts)
    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True)

    return df

def anne(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fonction pour ajouter les dates du 1er janvier pour chaque année dans la période couverte
    par le DataFrame, garder seulement ces dates, la première et la dernière entrée,
    et compléter les valeurs manquantes par propagation des valeurs précédentes et suivantes.
    
    Args:
        df: DataFrame avec des dates comme index et plusieurs colonnes de valeurs.
    
    Returns:
        DataFrame avec les dates du 1er janvier ajoutées, les autres dates supprimées,
        la première et dernière date incluses, et les valeurs complétées.
    """
    
    # Convertir l'index en datetime si nécessaire
    df.index = pd.to_datetime(df.index)
    
    # Créer une série des dates du 1er janvier pour chaque année seulement à partir de la première date de df
    all_january_firsts = pd.date_range(start=df.index.min().replace(month=1, day=1) + pd.offsets.YearBegin(),
                                       end=df.index.max().replace(month=1, day=1),
                                       freq='YS')
    
    # Ajouter la première et la dernière date de df
    start_date = df.index.min()
    end_date = df.index.max()
    
    # Combiner toutes les dates nécessaires, sans inclure de 1er janvier artificiel avant start_date
    combined_dates = pd.Index(all_january_firsts).union([start_date, end_date])
    
    # Réindexer le DataFrame pour inclure toutes ces dates
    newDf = df.reindex(combined_dates)
    
    # Compléter les valeurs manquantes
    newDf.fillna(method='ffill', inplace=True)
    newDf.fillna(method='bfill', inplace=True)

    return newDf

def transformer_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforme un DataFrame de large à long en réinitialisant l'index,
    renommant la colonne 'index' en 'Date', puis utilisant melt pour
    convertir le DataFrame. Réorganise les colonnes pour obtenir 'Date',
    'Type' et 'Montant'.

    Parameters:
    patrimoineMois (pd.DataFrame): DataFrame avec des dates en index et
                                   des colonnes de types financiers.

    Returns:
    pd.DataFrame: DataFrame transformé avec les colonnes 'Date', 'Type', 
                  et 'Montant'.
    """
    # Réinitialiser l'index pour le rendre une colonne normale
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Date'}, inplace=True)
    
    # Utiliser melt pour convertir le DataFrame de large à long
    df_long = df.melt(id_vars='Date', var_name='Type', value_name='Montant')
    
    # Réorganiser les colonnes
    df_long = df_long[['Date', 'Type', 'Montant']]
    
    return df_long


def main():
    patrimoine = pd.DataFrame()

    # 2024-09-01
    # argentCompteCourant = 51.82
    # argentLivretA = 12663.41
    # argentTradeRepublic = 2664

    # 2022-10-27
    argentCompteCourant = 264.13 # NE PAS CHANGER C'EST CORRECTE
    argentLivretA = 10045.71 # NE PAS CHANGER C'EST CORRECTE
    dossierCompteCourant = f"Bilan/Archives/Compte Chèques"
    dossierLivretA = f"Bilan/Archives/livret A"


    argentCompteCourantInitial = calculPatrimoineDeDepartCompteCourant(argentCompteCourant, dossierCompteCourant)
    argentLivretAInitial = calculPatrimoineDeDepartLivretA(argentLivretA, dossierLivretA)

    print(argentCompteCourantInitial)
    print(argentLivretAInitial)


    # patrimoine = evolutionDuPatrimoineSurLeCompteCourant(patrimoine, argentCompteCourant, dossierCompteCourant)
    # patrimoine = evolutionDuPatrimoineSurLeLivretA(patrimoine, argentLivretA, dossierLivretA)
    
    # patrimoineMois = mois(patrimoine)
    # patrimoineMois = transformer_dataframe(patrimoineMois)
    # plotHistograms(patrimoineMois)

    # patrimoineAnne = anne(patrimoine)
    # patrimoineAnne = transformer_dataframe(patrimoineAnne)
    # plotHistograms(patrimoineAnne)




if "__main__" == __name__:
    main()

    