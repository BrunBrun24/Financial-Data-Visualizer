import json
import pandas as pd
from datetime import datetime
import os
import glob


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

def TrierToutesCategoriesParDate(dataDict):
    """
    Trie toutes les catégories dans le dictionnaire par date d'opération si elles contiennent des opérations.

    Args:
        dataDict (dict): Dictionnaire contenant les opérations financières.
    
    Returns:
        dict: Le même dictionnaire avec toutes les catégories triées par date.
    """
    assert isinstance(dataDict, dict), f"dataDict n'est pas un dict {type(dataDict).__name__}"
    
    # Parcourir chaque catégorie du dictionnaire
    for categorie, operations in dataDict.items():
        # Si la catégorie contient une liste d'opérations
        if isinstance(operations, list) and operations and "DATE D'OPÉRATION" in operations[0]:
            # Trier la liste d'opérations par la clé 'DATE D'OPÉRATION'
            dataDict[categorie] = sorted(
                operations, 
                key=lambda x: pd.to_datetime(x["DATE D'OPÉRATION"], format='%Y-%m-%d')
            )
    
    return dataDict

def SaveDictToJson(dataDict, filePath):
    """
    Sauvegarde un dictionnaire dans un fichier JSON, après avoir trié toutes les catégories par date d'opération.
    Convertit également les objets pandas Timestamp en chaînes de caractères.

    Args:
        dataDict (dict): Le dictionnaire à sauvegarder.
        filePath (str): Le chemin du fichier JSON où les données doivent être sauvegardées.
    """
    assert isinstance(dataDict, dict), f"dataDict n'est pas un dict {type(dataDict).__name__}"
    assert isinstance(filePath, str), f"filePath n'est pas un str {type(filePath).__name__}"
    
    # Trier toutes les catégories par date d'opération
    dataDict = TrierToutesCategoriesParDate(dataDict)
    
    def convert_timestamp_to_string(obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        raise TypeError(f"Type non serialisable: {type(obj).__name__}")

    # Sauvegarde du dictionnaire trié dans un fichier JSON
    with open(filePath, 'w', encoding='utf-8') as file:
        json.dump(dataDict, file, indent=4, default=convert_timestamp_to_string, ensure_ascii=False)

def EnregistrerDataFrameEnJson(dataFrame: pd.DataFrame, cheminFichierJson: str) -> None:
    """
    Enregistre un DataFrame au format JSON dans le fichier spécifié, avec les dates comme clés et les montants comme valeurs.

    Args:
        dataFrame (pd.DataFrame): Le DataFrame à enregistrer. L'index doit être constitué de dates, et le DataFrame doit avoir une seule colonne avec les montants.
        cheminFichierJson (str): Le chemin du fichier JSON dans lequel enregistrer le DataFrame.

    Returns:
        None
    """
    # Vérifications des types des arguments
    assert isinstance(dataFrame, pd.DataFrame), f"dataFrame doit être un pd.DataFrame, mais c'est {type(dataFrame).__name__}."
    assert isinstance(cheminFichierJson, str) and cheminFichierJson.endswith(".json"), \
        f"cheminFichierJson doit être une chaîne se terminant par '.json', mais c'est {type(cheminFichierJson).__name__}."

    # Vérifier que l'index du DataFrame est constitué de dates
    assert pd.api.types.is_datetime64_any_dtype(dataFrame.index), "L'index du DataFrame doit être de type datetime."

    # Vérifier que le DataFrame a exactement une colonne
    assert dataFrame.shape[1] == 1, "Le DataFrame doit contenir exactement une colonne avec les montants."

    # Convertir l'index en dates au format string et les valeurs en dictionnaire
    dictData = dataFrame.reset_index()
    dictData.columns = ['Date', 'Montant']
    dictData['Date'] = dictData['Date'].dt.strftime('%Y-%m-%d')  # Convertir les dates au format 'YYYY-MM-DD'
    dictData = dictData.set_index('Date')['Montant'].to_dict()

    # Convertir le dictionnaire en JSON et l'enregistrer
    jsonData = pd.Series(dictData).to_json(orient='index', indent=2)

    # Écrire le JSON dans le fichier
    with open(cheminFichierJson, 'w', encoding="utf-8") as f:
        f.write(jsonData)

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

def LoadDictFromJson(filePath):
        """
        Lit un fichier JSON et le convertit en dictionnaire.

        Args:
            filePath (str): Le chemin du fichier JSON à lire.

        Returns:
            dict: Le dictionnaire lu à partir du fichier JSON.
        """
        assert isinstance(filePath, str), "filePath doit être une chaîne de caractères."

        try:
            with open(filePath, 'r', encoding='utf-8') as file:
                dataDict = json.load(file)
            return dataDict
        except Exception as e:
            raise AttributeError(f"Une erreur s'est produite lors de la lecture du fichier JSON : {str(e)}")
        
def RecupererFichiersJson(dossier):
    """
    Récupère tous les fichiers JSON dans le dossier spécifié.
    
    Args:
        dossier (str): Chemin du dossier où chercher les fichiers JSON.
        
    Returns:
        list: Liste des chemins complets des fichiers JSON trouvés.
    """
    # Vérification que le chemin du dossier est une chaîne valide
    assert isinstance(dossier, str), f"dossier doit être une chaîne de caractères, mais c'est {type(dossier).__name__}."
    
    # Vérification que le dossier existe
    assert os.path.isdir(dossier), f"Le dossier spécifié n'existe pas: {dossier}"
    
    # Utilisation de glob pour récupérer tous les fichiers .json
    chemin_fichiers_json = os.path.join(dossier, "*.json")
    fichiers_json = glob.glob(chemin_fichiers_json)
    
    return fichiers_json
