import pandas as pd
import json
import os


class RecuperationDonnees:
    
    @staticmethod
    def DownloadDataFrameInJson(path: str) -> pd.DataFrame:
        """
        Télécharge les données d'un fichier JSON et retourne un DataFrame.

        Args:
            path (str): Le chemin vers le fichier JSON.

        Returns:
            pd.DataFrame: Les données contenues dans le fichier JSON sous forme de DataFrame.
        """
        assert isinstance(path, str) and os.path.isfile(path), f"Le fichier {path} n'existe pas ou le chemin n'est pas valide."

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, list), "Le contenu du fichier JSON doit être une liste d'objets (dict)."

        return pd.DataFrame(data)

    @staticmethod
    def CalculPatrimoineDeDepart(argent: float, directory: str) -> float:
        """
        Calculer le patrimoine initial basé sur les transactions trouvées dans les fichiers JSON.

        Args:
            argent: Argent sur le compte aujourd'hui.
            directory: Chemin vers le dossier contenant les fichiers JSON.

        Returns:
            float: Montant initial du compte courant.
        """
        assert isinstance(argent, (int, float)), f"La variable argent doit être un nombre: ({type(argent)})"
        assert isinstance(directory, str), f"La variable directory doit être une chaîne de caractères: ({type(directory)})"
        assert os.path.exists(directory), f"Le dossier spécifié n'existe pas: {directory}"

        for fichier in os.listdir(directory):
            if fichier.endswith(".json"):
                with open(os.path.join(directory, fichier), 'r', encoding="UTF-8") as f:
                    data = json.load(f)
                    for categorie, operations in data.items():
                        for operation in operations:
                            argent += operation["MONTANT"]
        return argent
    
    @staticmethod
    def TransformerDossierJsonEnDataFrame(cheminDossier: str) -> pd.DataFrame:
        """
        Charge tous les fichiers JSON d'un dossier, les combine en un DataFrame, avec 'DATE D'OPÉRATION' comme index,
        et trie les données par cet index.

        Args:
            cheminDossier: Chemin vers le dossier contenant les fichiers JSON.

        Returns:
            pd.DataFrame: DataFrame combiné avec les transactions de tous les fichiers.
        """
        assert isinstance(cheminDossier, str), f"Le cheminDossier doit être une chaîne de caractères: ({type(cheminDossier)})"
        assert os.path.isdir(cheminDossier), f"Le chemin spécifié n'est pas un dossier valide: ({cheminDossier})"

        lignes = []
        for fichier in os.listdir(cheminDossier):
            if fichier.endswith('.json'):
                cheminFichier = os.path.join(cheminDossier, fichier)
                with open(cheminFichier, 'r', encoding='UTF-8') as f:
                    data = json.load(f)
                    for categorie, transactions in data.items():
                        assert isinstance(transactions, list), f"Les transactions doivent être une liste: ({transactions})"
                        for transaction in transactions:
                            assert isinstance(transaction, dict), f"Chaque transaction doit être un dictionnaire: ({transaction})"
                            assert "DATE D'OPÉRATION" in transaction, f"Clé 'DATE D'OPÉRATION' manquante: ({transaction})"
                            transaction['Catégorie'] = categorie
                            lignes.append(transaction)

        df = pd.DataFrame(lignes)
        df.set_index("DATE D'OPÉRATION", inplace=True)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df
    
