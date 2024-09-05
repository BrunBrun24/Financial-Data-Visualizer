import json
import pandas as pd
from datetime import datetime


def ExtraireAnnee(data):
    """
    Extrait l'année de la première date dans la colonne 'DATE D'OPÉRATION' d'un DataFrame.

    Args:
        data (list of dicts or DataFrame): Les données contenant une colonne 'DATE D'OPÉRATION'
                                           avec des dates au format compatible.

    Returns:
        str: L'année extraite de la première date dans la colonne sous forme de chaîne de caractères.
    """
    # Convertir les données en DataFrame si ce n'est pas déjà le cas
    if not isinstance(data, pd.DataFrame):
        df = pd.DataFrame(data)
    else:
        df = data

    # Vérifier que la colonne 'DATE D'OPÉRATION' existe dans le DataFrame
    assert 'DATE D\'OPÉRATION' in df.columns, "La colonne 'DATE D'OPÉRATION' est absente du DataFrame."

    # S'assurer que la colonne 'DATE D'OPÉRATION' est au format datetime
    df['DATE D\'OPÉRATION'] = pd.to_datetime(df['DATE D\'OPÉRATION'], errors='coerce')

    # Vérifier qu'il y a des dates valides après conversion
    assert not df['DATE D\'OPÉRATION'].isnull().all(), "Aucune date valide dans la colonne 'DATE D'OPÉRATION'."

    # Extraire l'année de la première date de la colonne
    annee = df['DATE D\'OPÉRATION'].dt.year.dropna().iloc[0]

    # Retourner l'année sous forme de chaîne de caractères
    return str(int(annee))


def DiviserParMois(data: dict) -> dict:
    """
    Divise les opérations par mois et année à partir des données fournies.

    Args:
        data (Dict[str, List[Dict[str, Any]]]): Un dictionnaire où les clés sont des catégories 
                                                et les valeurs sont des listes d'opérations.
                                                Chaque opération est un dictionnaire contenant au moins
                                                une clé 'DATE D'OPÉRATION' au format '%Y-%m-%d'.

    Returns:
        Dict[str, Dict[str, List[Dict[str, Any]]]]: Un dictionnaire où les clés sont les mois/années
                                                     au format '%Y-%m', chaque mois/année ayant des 
                                                     sous-dictionnaires de catégories et listes d'opérations.
    """
    # Vérifier que les données sont un dictionnaire
    assert isinstance(data, dict), f"Les données doivent être un dictionnaire: {type(data).__name__}"
    
    result = {}
    
    for category, operations in data.items():
        assert isinstance(category, str), f"La catégorie doit être une chaîne de caractères: {type(category).__name__}"
        assert isinstance(operations, list), f"Les opérations doivent être une liste: {type(operations).__name__}"
        
        for operation in operations:
            assert isinstance(operation, dict), f"Chaque opération doit être un dictionnaire: {type(operation).__name__}"
            assert "DATE D'OPÉRATION" in operation, "Chaque opération doit contenir une clé 'DATE D'OPÉRATION'."
            
            date_str = operation["DATE D'OPÉRATION"]
            assert isinstance(date_str, str), f"DATE D'OPÉRATION doit être une chaîne de caractères: {type(date_str).__name__}"
            
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Le format de la date est invalide: {date_str}. Doit être '%Y-%m-%d'.")
            
            year_month = date_obj.strftime('%Y-%m')
            
            if year_month not in result:
                result[year_month] = {}
                
            if category not in result[year_month]:
                result[year_month][category] = []
            
            result[year_month][category].append(operation)
    
    return result

def SaveDictToJson(data_dict, file_path):
    """
    Sauvegarde un dictionnaire dans un fichier JSON, en convertissant les objets pandas Timestamp en chaînes de caractères.

    Args:
        data_dict (dict): Le dictionnaire à sauvegarder.
        file_path (str): Le chemin du fichier JSON où les données doivent être sauvegardées.
    """
    def convert_timestamp_to_string(obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        raise TypeError(f"Type non serialisable: {type(obj).__name__}")

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data_dict, file, indent=4, default=convert_timestamp_to_string, ensure_ascii=False)


def CreerNomFichier(data: dict) -> str:
    """
    Crée un nom de fichier basé sur les années extraites des dates d'opération dans les DataFrames.

    Args:
        data (dict): Dictionnaire où les clés sont des catégories et les valeurs sont des listes de données.

    Returns:
        str: Nom de fichier basé sur les années extraites. Format 'YYYY' si une seule année, sinon 'YYYY-YYYY'.
    """
    # Vérifiez que 'data' est un dictionnaire
    assert isinstance(data, dict), f"Le paramètre 'data' doit être un dictionnaire. Type fourni: {type(data).__name__}"

    # Créez des DataFrames à partir des valeurs du dictionnaire si les valeurs ne sont pas vides
    dfs = {key: pd.DataFrame(value) for key, value in data.items() if value}

    years = set()

    for df in dfs.values():
        if 'DATE D\'OPÉRATION' in df.columns:
            # Assurez-vous que la colonne 'DATE D\'OPÉRATION' peut être convertie en datetime
            df['DATE D\'OPÉRATION'] = pd.to_datetime(df['DATE D\'OPÉRATION'], errors='coerce')
            
            # Vérifiez qu'il y a des dates valides après conversion
            if df['DATE D\'OPÉRATION'].notna().any():
                min_year = df['DATE D\'OPÉRATION'].min().year
                max_year = df['DATE D\'OPÉRATION'].max().year
                years.add(min_year)
                years.add(max_year)
            else:
                raise ValueError(f"Les dates dans la colonne 'DATE D\'OPÉRATION' ne sont pas valides pour les données dans une ou plusieurs catégories.")

    # Si aucune année n'a été trouvée, raise une erreur
    if not years:
        raise ValueError("Aucune année valide trouvée dans les données.")

    years = sorted(years)
    
    # Retourner le nom de fichier basé sur les années trouvées
    if len(years) == 1:
        return str(years[0])
    return f"{years[0]}-{years[-1]}"

