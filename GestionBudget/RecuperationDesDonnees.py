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
        - `ExtractExcelData(self, filePath)`: Extrait les données d'un fichier Excel et les formate en `DataFrame`.
        - `CleanLine(text, startIndex, endText)`: Nettoie une ligne de texte en supprimant les informations inutiles.
        - `LoadDictFromJson(filePath)`: Lit un fichier JSON et le convertit en dictionnaire.
        - `OpenFileDialog(self, root)`: Ouvre une boîte de dialogue pour sélectionner un fichier.
        - `SelectAndExtractData(self)`: Permet à l'utilisateur de sélectionner un fichier et extrait les données.
        - `CenterWindow(window, width, height)`: Centre une fenêtre Tkinter à l'écran selon la largeur et la hauteur spécifiées.
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

    def ExtractExcelData(self, filePath):
        """
        Extrait les données d'un fichier Excel et les formate en DataFrame.

        Args:
            filePath (str): Le chemin du fichier Excel.

        Returns:
            pd.DataFrame: Les données extraites et formatées en DataFrame.
        """
        assert isinstance(filePath, str), "filePath doit être une chaîne de caractères."
        
        try:
            data = []
            workbook = xlrd.open_workbook(filePath)
            sheet = workbook.sheet_by_index(0)

            for rowIndex in range(2, sheet.nrows):
                row = sheet.row_values(rowIndex, start_colx=0, end_colx=5)
                data.append(row)

            data = data[1:]

            for line in data:
                if line[2] == "FACTURE CARTE":
                    line[0] = line[3][17:23]
                    line[0] = line[0][0:2] + "/" + line[0][2:4] + "/20" + line[0][4:]
                    dateObj = datetime.strptime(line[0], '%d/%m/%Y')
                    line[0] = float((dateObj - datetime(1899, 12, 30)).days)
                    line[3] = self.CleanLine(line[3], 24, "CARTE")

                elif line[2] == "VIR CPTE A CPTE EMIS":
                    line[3] = self.CleanLine(line[3], 22, "/")

                elif line[2] == "VIR CPTE A CPTE RECU":
                    line[3] = self.CleanLine(line[3], 22, "/REF")

                elif line[2] == "VIR SEPA RECU":
                    line[3] = self.CleanLine(line[3], 15, "/REF")

                elif line[2] == "REMISE CHEQUES":
                    line[3] = self.CleanLine(line[3], 15, "/NOPT")

            data.sort(key=lambda x: x[0])

            result = pd.DataFrame(data, columns=["DATE D'OPÉRATION", "LIBELLÉ COURT", "TYPE OPÉRATION", "LIBELLÉ OPÉRATION", "MONTANT"])
            result["DATE D'OPÉRATION"] = result["DATE D'OPÉRATION"].apply(self.ExcelDateToDatetime)
            result["DATE D'OPÉRATION"] = pd.to_datetime(result["DATE D'OPÉRATION"])

            return result

        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur s'est produite lors de la lecture du fichier Excel : {str(e)}")
            return None

    @staticmethod
    def CleanLine(text, startIndex, endText):
        """
        Nettoie une ligne de texte en supprimant les informations inutiles.

        Args:
            text (str): Le texte à nettoyer.
            startIndex (int): L'indice de début pour le nettoyage.
            endText (str): Le texte de fin indiquant la fin de la portion à conserver.

        Returns:
            str: Le texte nettoyé.
        """
        assert isinstance(text, str), "text doit être une chaîne de caractères."
        assert isinstance(startIndex, int), "startIndex doit être un entier."
        assert isinstance(endText, str), "endText doit être une chaîne de caractères."

        endIndex = text.find(endText, startIndex)
        if endIndex != -1:
            text = text[startIndex:endIndex]
            text = ' '.join(text.split())
        return text

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
        
        # Ouvrir la boîte de dialogue de sélection de fichier
        self.filePath = filedialog.askopenfilename(
            title="Choisissez un fichier Excel ou JSON",
            filetypes=[("Fichiers Excel et JSON", "*.xlsx *.xls *.json")],
            initialdir=self.initialDir
        )
        # Ferme la fenêtre principale après la sélection du fichier
        root.destroy()

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

        windowWidth = 400
        windowHeight = 200

        self.CenterWindow(root, windowWidth, windowHeight)

        messageLabel = tk.Label(root, text="Veuillez sélectionner un fichier Excel ou JSON pour extraire les données.", padx=20, pady=20)
        messageLabel.pack()

        searchButton = tk.Button(root, text="Rechercher un fichier", command=lambda: self.OpenFileDialog(root))
        searchButton.pack(pady=10)

        root.mainloop()

        if self.filePath is not None:
            try:
                if self.filePath.lower().endswith('.xlsx') or self.filePath.lower().endswith('.xls'):
                    data = self.ExtractExcelData(self.filePath)
                    return data, "Excel", self.filePath.split('/')[-2]
                elif self.filePath.lower().endswith('.json'):
                    data = self.LoadDictFromJson(self.filePath)
                    return data, "Json", self.filePath.split('/')[-2]
                else:
                    messagebox.showerror("Erreur", "Type de fichier non supporté.")
                    return None

            except Exception as e:
                messagebox.showerror("Erreur", f"Une erreur s'est produite lors de la lecture du fichier : {str(e)}")

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
        assert isinstance(width, int), "width doit être un entier."
        assert isinstance(height, int), "height doit être un entier."

        screenWidth = window.winfo_screenwidth()
        screenHeight = window.winfo_screenheight()

        positionX = (screenWidth // 2) - (width // 2)
        positionY = (screenHeight // 2) - (height // 2)

        window.geometry(f'{width}x{height}+{positionX}+{positionY}')

