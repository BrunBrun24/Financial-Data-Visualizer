import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import xlrd
from datetime import datetime, timedelta
import json


class DataExtractor:
    """
    La classe `DataExtractor` fournit des outils pour extraire et manipuler des données 
    à partir de fichiers Excel et JSON. Elle permet de sélectionner un fichier via une interface 
    utilisateur, de lire et de convertir les données contenues dans le fichier, ainsi que de 
    nettoyer et transformer ces données pour une utilisation ultérieure.

    Attributs:
        - `initialDir` (str): Répertoire initial pour ouvrir la boîte de dialogue de sélection de fichiers. 
          Par défaut, défini sur "Bilan/Archives".
        - `filePath` (str): Chemin du fichier sélectionné par l'utilisateur.
        - `data` (pd.DataFrame ou dict): Contient les données extraites du fichier sélectionné.

    Méthodes:
        - `__init__(self, initialDir="Bilan/Archives")`: Initialise l'extracteur de données avec le répertoire de départ.
        - `ExcelDateToDatetime(excelDate)`: Convertit une date au format Excel en objet `datetime`.
        - `ExtractExcelData(self, filePath, extension)`: Extrait les données d'un fichier Excel et les formate en `DataFrame`.
        - `CleanLine(text, startIndex, endText)`: Nettoie une ligne de texte en supprimant les informations inutiles.
        - `LoadDictFromJson(filePath)`: Lit un fichier JSON et le convertit en dictionnaire.
        - `OpenFileDialog(self, root)`: Ouvre une boîte de dialogue pour sélectionner un fichier.
        - `SelectAndExtractData(self)`: Permet à l'utilisateur de sélectionner un fichier et extrait les données.
        - `CenterWindow(window, width, height)`: Centre une fenêtre Tkinter à l'écran selon la largeur et la hauteur spécifiées.
        - `UpdateDateOperation(df)`: Met à jour les dates dans la colonne 'DATE D'OPÉRATION' et nettoie le contenu de la colonne 'LIBELLÉ OPÉRATION' pour certains types d'opérations spécifiques.
        - `ExtractDateFromLibelle(libelle)`: Extrait la date au format jj/mm/aaaa depuis la chaîne de caractères après 'DU'.
        - `ExtractBetweenSlashes(text, start, end)`: Extrait le texte entre différentes positions des '/' dans une chaîne.
        - `CleanLibelle(libelle)`: Nettoie le libellé en supprimant le texte après le premier double espace.
    """
    
    def __init__(self, initialDir="Bilan/Archives"):
        """
        Initialise l'extracteur de données avec un répertoire de départ pour la sélection de fichiers.

        Args:
            initialDir (str): Le répertoire initial pour ouvrir la boîte de dialogue de sélection de fichiers.
        """
        assert isinstance(initialDir, str), "initialDir doit être une chaîne de caractères."
        self.initialDir = initialDir
        self.filePath = None
        self.data = None


    def SelectAndExtractData(self):
        """
        Ouvre une fenêtre pour permettre à l'utilisateur de sélectionner un fichier Excel ou JSON
        puis extrait les données de ce fichier.

        Returns:
            tuple: Contient les données extraites (DataFrame ou dict), le type de fichier, et le dossier contenant le fichier.
        """
        # Création de la fenêtre principale
        root = tk.Tk()
        root.title("Sélection du Fichier")

        self.CenterWindow(root, 400, 200)

        messageLabel = tk.Label(root, text="Veuillez sélectionner un fichier Excel ou JSON pour extraire les données.", padx=20, pady=20)
        messageLabel.pack()

        searchButton = tk.Button(root, text="Rechercher un fichier", command=lambda: self.OpenFileDialog(root))
        searchButton.pack(pady=10)

        root.mainloop()

        if self.filePath is not None:
            if self.filePath.lower().endswith('.xls'):
                data = self.ExtractExcelData(self.filePath, ".xls")
                return data, "Excel", self.filePath.split('/')[-2]
            elif self.filePath.lower().endswith('.xlsx'):
                data = self.ExtractExcelData(self.filePath, ".xlsx")
                return data, "Excel", self.filePath.split('/')[-2]
            elif self.filePath.lower().endswith('.json'):
                data = self.LoadDictFromJson(self.filePath)
                return data, "Json", self.filePath.split('/')[-2]
            else:
                messagebox.showerror("Erreur", "Type de fichier non supporté.")
                return None

        return None

    @staticmethod
    def CenterWindow(window, width, height):
        """
        Centre une fenêtre Tkinter à l'écran.

        Args:
            window (tk.Tk): La fenêtre à centrer.
            width (int): La largeur de la fenêtre.
            height (int): La hauteur de la fenêtre.
        """
        assert isinstance(window, tk.Tk), f"window doit être une instance de tk.Tk, mais c'est {type(window).__name__}."
        assert isinstance(width, int), f"width doit être un entier, mais c'est {type(width).__name__}."
        assert isinstance(height, int), f"height doit être un entier, mais c'est {type(height).__name__}."

        screenWidth = window.winfo_screenwidth()
        screenHeight = window.winfo_screenheight()

        positionX = (screenWidth // 2) - (width // 2)
        positionY = (screenHeight // 2) - (height // 2)

        window.geometry(f'{width}x{height}+{positionX}+{positionY}')

    @staticmethod
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
            messagebox.showerror("Erreur", f"Une erreur s'est produite lors de la lecture du fichier JSON : {str(e)}")
            return None

    def OpenFileDialog(self, root):
        """
        Ouvre une boîte de dialogue pour permettre à l'utilisateur de sélectionner un fichier 
        et centre la fenêtre principale avant d'ouvrir la boîte de dialogue.
        """
        assert isinstance(root, tk.Tk), f"root doit être une instance de tk.Tk, mais c'est {type(root).__name__}."

        self.CenterWindow(root, 400, 200)
        
        # Ouvrir la boîte de dialogue de sélection de fichier
        self.filePath = filedialog.askopenfilename(
            title="Choisissez un fichier Excel ou JSON",
            filetypes=[("Fichiers Excel et JSON", "*.xlsx *.xls *.json")],
            initialdir=self.initialDir
        )
        # Ferme la fenêtre principale après la sélection du fichier
        root.destroy()



    def ExtractExcelData(self, filePath, extension):
        """
        Extrait les données d'un fichier Excel (.xlsx ou .xls) et les formate en DataFrame.

        Args:
            filePath (str): Le chemin du fichier Excel à extraire.
            extension (str): L'extension du fichier ('.xlsx' ou '.xls').

        Returns:
            pd.DataFrame: Les données extraites et formatées en DataFrame avec les colonnes:
                        - "DATE D'OPÉRATION"
                        - "LIBELLÉ COURT"
                        - "TYPE OPÉRATION"
                        - "LIBELLÉ OPÉRATION"
                        - "MONTANT"
                        Si une erreur survient, retourne None.

        Raises:
            AssertionError: Si le type des arguments `filePath` ou `extension` n'est pas valide.
        """
        assert isinstance(filePath, str), f"filePath doit être une chaîne de caractères, mais c'est {type(filePath).__name__}."
        assert isinstance(extension, str), f"extension doit être une chaîne de caractères, mais c'est {type(extension).__name__}."
        assert extension in ['.xlsx', '.xls'], f"L'extension doit être '.xlsx' ou '.xls', mais c'est {extension}."

        try:
            if extension == ".xls":
                data = []
                workbook = xlrd.open_workbook(filePath)
                sheet = workbook.sheet_by_index(0)

                # Extraction des lignes à partir de la quatrième ligne
                for rowIndex in range(3, sheet.nrows):
                    row = sheet.row_values(rowIndex, start_colx=0, end_colx=5)
                    data.append(row)

            elif extension == ".xlsx":
                df = pd.read_excel(filePath, engine='openpyxl', skiprows=3, usecols="A:E", header=None)
                data = df.values.tolist()

            # Création du DataFrame avec les colonnes spécifiées
            result = pd.DataFrame(data, columns=["DATE D'OPÉRATION", "LIBELLÉ COURT", "TYPE OPÉRATION", "LIBELLÉ OPÉRATION", "MONTANT"])

            # Vérifier si la colonne 'DATE D'OPÉRATION' est de type datetime, sinon la convertir
            if not pd.api.types.is_datetime64_any_dtype(result["DATE D'OPÉRATION"]):
                result["DATE D'OPÉRATION"] = result["DATE D'OPÉRATION"].apply(self.ExcelDateToDatetime)
                result["DATE D'OPÉRATION"] = pd.to_datetime(result["DATE D'OPÉRATION"])

            self.UpdateDateOperation(result)
            # On convertit l'index pour avoir les dates les plus anciennes au début
            result.sort_index(axis=1)
            return result

        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur s'est produite lors de la lecture du fichier Excel : {str(e)}")
            return None

    def UpdateDateOperation(self, df):
        """
        Met à jour les dates dans la colonne 'DATE D'OPÉRATION' et nettoie le contenu de la colonne 'LIBELLÉ OPÉRATION'
        pour certains types d'opérations spécifiques.

        Args:
            df (pd.DataFrame): Le DataFrame contenant les colonnes à mettre à jour.

        Returns:
            pd.DataFrame: DataFrame avec les dates mises à jour et les libellés nettoyés.
        """
        assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame, mais c'est {type(df).__name__}."
        nameColumns = ["LIBELLÉ COURT", "DATE D'OPÉRATION", "TYPE OPÉRATION"]
        for col in nameColumns:
            assert col in df.columns, f"La colonne '{col}' est manquante dans le DataFrame."

        for index, row in df.iterrows():
            if row["LIBELLÉ COURT"] == "PAIEMENT CB":
                df.at[index, "LIBELLÉ OPÉRATION"] = self.ExtractBetweenSlashes(row["LIBELLÉ OPÉRATION"], 0, -2)

                newDate, newLibelle = self.ExtractDateFromLibelle(row["LIBELLÉ OPÉRATION"])
                if newDate:
                    df.at[index, "DATE D'OPÉRATION"] = newDate
                if newLibelle:
                    df.at[index, "LIBELLÉ OPÉRATION"] = self.CleanLibelle(newLibelle)
                    
            elif row["TYPE OPÉRATION"] == "VIR CPTE A CPTE EMIS":
                df.at[index, "LIBELLÉ OPÉRATION"] = self.CleanLibelle(self.ExtractBetweenSlashes(row["LIBELLÉ OPÉRATION"], 0, -2))

            elif row["TYPE OPÉRATION"] == "VIR CPTE A CPTE RECU":
                df.at[index, "LIBELLÉ OPÉRATION"] = self.CleanLibelle(self.ExtractBetweenSlashes(row["LIBELLÉ OPÉRATION"], 0, -1))

            elif row["TYPE OPÉRATION"] == "VIR SEPA RECU":
                df.at[index, "LIBELLÉ OPÉRATION"] = self.CleanLibelle(self.ExtractBetweenSlashes(row["LIBELLÉ OPÉRATION"], 0, -1))

            elif row["TYPE OPÉRATION"] == "REMISE CHEQUES":
                df.at[index, "LIBELLÉ OPÉRATION"] = self.CleanLibelle(self.ExtractBetweenSlashes(row["LIBELLÉ OPÉRATION"], 0, 0))

        return df

    @staticmethod
    def ExcelDateToDatetime(excelDate):
        """
        Convertit une date Excel en un objet datetime.

        Args:
            excelDate (float): La date au format Excel.

        Returns:
            datetime: La date convertie en objet datetime.
        """
        assert isinstance(excelDate, (int, float)), "excelDate doit être un nombre."
        return datetime(1899, 12, 30) + timedelta(days=excelDate)

    @staticmethod
    def ExtractDateFromLibelle(libelle):
        """
        Extrait la date au format jj/mm/aaaa depuis la chaîne de caractères après 'DU'.

        Args:
            libelle (str): Texte contenant l'opération avec la date.

        Returns:
            datetime: La date extraite et formatée en objet datetime.
        """
        if "DU" in libelle:
            try:
                # Trouver l'indice de 'DU' et extraire la date sous format jjmmaaa
                startIndex = libelle.find("DU") + 3
                dateStr = libelle[startIndex:startIndex+6]
                # Formater en date valide
                formattedDate = datetime.strptime(dateStr, "%d%m%y")
                newLibelle = libelle[startIndex+7:]
                return formattedDate, newLibelle
            except ValueError:
                return None, None
        return None, None

    @staticmethod
    def ExtractBetweenSlashes(text, start, end):
        """
        Extrait le texte entre différentes positions des '/' dans une chaîne.

        Args:
            text (str): La chaîne contenant plusieurs '/'.
            start (int): L'indice de départ pour l'extraction (position du premier '/').
            end (int): L'indice de fin pour l'extraction (position du dernier '/').

        Returns:
            str: Le texte extrait entre les positions 'start' et 'end'. Si les indices ne sont pas valides, retourne le texte original.

        Raises:
            AssertionError: Si `text` n'est pas une chaîne de caractères, ou si `start` et `end` ne sont pas des entiers.
        """
        assert isinstance(text, str), "text doit être une chaîne de caractères."
        assert isinstance(start, int) and isinstance(end, int), "start et end doivent être des entiers."

        # Trouver tous les indices des '/'
        slashPositions = [i for i, char in enumerate(text) if char == '/']

        # Si 'end' est 0, on extrait avant le premier '/'
        if end == 0 and slashPositions:
            return text[:slashPositions[0]].strip()

        # S'assurer qu'il y a suffisamment de '/' pour les indices start et end
        if len(slashPositions) >= abs(end) and len(slashPositions) > start:
            startTexte = slashPositions[start]
            endTexte = slashPositions[end]

            # Extraire le texte entre les deux positions
            return text[startTexte + 1:endTexte].strip()
        else:
            # Si les indices ne correspondent pas aux positions disponibles, retourner le texte original
            return text

    @staticmethod
    def CleanLibelle(libelle):
        """
        Nettoie le libellé en supprimant le texte après le premier double espace.

        Args:
            libelle (str): Le texte du libellé à nettoyer.

        Returns:
            str: Le libellé nettoyé, sans le texte après le premier double espace.
        """
        assert isinstance(libelle, str), f"libelle doit être une chaîne de caractères, mais c'est {type(libelle).__name__}."

        # Trouver l'index du premier double espace
        doubleSpaceIndex = libelle.find("  ")
        
        if doubleSpaceIndex != -1:
            newLibelle = libelle[:doubleSpaceIndex]
            return newLibelle.strip()

        # Si aucun double espace n'est trouvé, retourner le libellé tel quel
        return libelle
