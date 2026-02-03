import html
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox

import pandas as pd
import xlrd


class ExcelDataExtractor:
    """
    Classe responsable de la sélection, de l'extraction et du nettoyage 
    de données issues de fichiers Excel (XLS/XLSX).
    """

    def __init__(self, initial_dir: str = "/"):
        """
        Initialise l'extracteur avec un répertoire par défaut.
        
        Args:
            - initial_dir (str) : Répertoire initial pour la sélection de fichiers.
        """
        self._initial_dir = initial_dir
        self.__file_paths = []


    # --- [ Méthodes Publiques ] ---
    def run_extraction(self) -> (pd.DataFrame | None):
        """
        Lance le processus complet : interface de sélection puis extraction.
        
        Returns:
            - pd.DataFrame : Données fusionnées et nettoyées, ou None.
        """
        self.__open_selection_window()
        
        if not self.__file_paths:
            return None

        all_dfs = []
        for file_path in self.__file_paths:
            extension = f".{file_path.lower().split('.')[-1]}"
            if extension in [".xls", ".xlsx"]:
                df_temp = self._extract_file_data(file_path, extension)
            elif extension == ".csv":
                df_temp = self._extract_csv_data(file_path)

            if df_temp is not None:
                all_dfs.append(df_temp)

        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        
        return None


    # --- [ Gestion de l'Interface ] ---
    def __open_selection_window(self):
        """
        Crée et affiche la fenêtre Tkinter pour la sélection des fichiers.
        """
        root = tk.Tk()
        root.title("Sélection des fichiers")
        self._setup_window_geometry(root, 400, 200)

        message_label = tk.Label(root, text="Sélectionnez un ou plusieurs fichiers Excel.")
        message_label.pack(padx=20, pady=20)

        # Utilisation d'une fonction interne pour capturer le root
        def on_search():
            paths = filedialog.askopenfilenames(
                title="Choisir un ou plusieurs fichiers",
                initialdir=self._initial_dir,
                filetypes=[("Fichiers Excel", "*.xls *.xlsx *.csv"), ("Tous les fichiers", "*.*")]
            )
            if paths:
                self.__file_paths = list(paths)
                root.destroy()

        search_button = tk.Button(root, text="Rechercher des fichiers", command=on_search)
        search_button.pack(pady=10)

        root.mainloop()

    def _setup_window_geometry(self, window: tk.Tk, width: int, height: int):
        """
        Centre une fenêtre Tkinter à l'écran.
        
        Args:
            - window (tk.Tk) : Fenêtre à centrer.
            - width (int) : Largeur.
            - height (int) : Hauteur.
        """
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        pos_x = (screen_width // 2) - (width // 2)
        pos_y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{pos_x}+{pos_y}')


    # --- [ Extraction & Traitement ] ---
    def _extract_file_data(self, file_path: str, extension: str) -> (pd.DataFrame | None):
        """
        Extrait les données brutes d'un fichier spécifique.
        
        Args:
            - file_path (str) : Chemin du fichier.
            - extension (str) : Extension détectée.
            
        Returns:
            - pd.DataFrame : DataFrame formaté ou None en cas d'erreur.
        """
        try:
            if extension == ".xls":
                data = []
                workbook = xlrd.open_workbook(file_path)
                sheet = workbook.sheet_by_index(0)
                # On commence à la ligne 4 (index 3)
                for row_idx in range(3, sheet.nrows):
                    row = sheet.row_values(row_idx, start_colx=0, end_colx=5)
                    data.append(row)
            else:
                df = pd.read_excel(file_path, engine='openpyxl', skiprows=3, usecols="A:E", header=None)
                data = df.values.tolist()

            result = pd.DataFrame(data, columns=[
                "date_operation", "libelle_court", "type_operation", "libelle_operation", "montant"
            ])

            # Conversion du format de date Excel vers Datetime
            if not pd.api.types.is_datetime64_any_dtype(result["date_operation"]):
                result["date_operation"] = result["date_operation"].apply(self._excel_date_to_datetime)
                result["date_operation"] = pd.to_datetime(result["date_operation"])

            # Application des règles métier
            self._apply_business_rules(result)
            return result

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur sur le fichier {file_path} : {str(e)}")
            return None

    def _extract_csv_data(self, file_path: str) -> (pd.DataFrame | None):
        """
        Extrait les données brutes d'un fichier csv.
        
        Args:
            - file_path (str) : Chemin du fichier.
            - extension (str) : Extension détectée.
            
        Returns:
            - pd.DataFrame : DataFrame formaté ou None en cas d'erreur.
        """
        try:
            # Lecture avec gestion du séparateur et de la virgule décimale
            df = pd.read_csv(
                file_path, 
                sep=';', 
                encoding='utf-8', 
                header=None, 
                on_bad_lines='skip',
                decimal=','
            )

            # Nettoyage HTML (Nouvelle syntaxe .map)
            df = df.map(lambda x: html.unescape(str(x)) if isinstance(x, str) else x)

            # Filtrage des lignes de transactions uniquement
            df = df[df[0].str.contains(r'\d{2}/\d{2}/\d{4}', na=False)].copy()

            df = df.iloc[:, 0:5]
            df.columns = ["date_operation", "libelle_court", "type_operation", "libelle_operation", "montant"]

            # Conversion forcée en numérique pour éviter les NULL
            df["montant"] = pd.to_numeric(df["montant"], errors='coerce')
            
            # Suppression des lignes où le montant n'a pas pu être converti (évite l'IntegrityError)
            df = df.dropna(subset=["montant"])

            # Conversion de la date
            df["date_operation"] = pd.to_datetime(df["date_operation"], dayfirst=True)

            # Application des règles métier
            self._apply_business_rules(df)
            
            return df

        except Exception as e:
            messagebox.showerror("Erreur CSV", f"Erreur sur le fichier {file_path} : {str(e)}")
            return None

    def _apply_business_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applique les transformations de nettoyage sur les libellés et les dates.
        
        Args:
            - df (pd.DataFrame) : DataFrame à modifier.
            
        Returns:
            - pd.DataFrame : DataFrame mis à jour.
        """
        for index, row in df.iterrows():
            libelle = str(row["libelle_operation"])
            
            if row["libelle_court"] == "PAIEMENT CB":
                df.at[index, "libelle_operation"] = self.__extract_between_slashes(libelle, 0, -2)
                new_date, new_libelle = self.__extract_date_from_libelle(libelle)
                if new_date:
                    df.at[index, "date_operation"] = new_date
                if new_libelle:
                    df.at[index, "libelle_operation"] = self.__clean_libelle_spacing(new_libelle)

            elif row["type_operation"] == "VIR CPTE A CPTE EMIS":
                clean_txt = self.__extract_between_slashes(libelle, 0, -2)
                df.at[index, "libelle_operation"] = self.__clean_libelle_spacing(clean_txt)

            elif row["type_operation"] in ["VIR CPTE A CPTE RECU", "VIR SEPA RECU"]:
                clean_txt = self.__extract_between_slashes(libelle, 0, -1)
                df.at[index, "libelle_operation"] = self.__clean_libelle_spacing(clean_txt)

            elif row["type_operation"] == "REMISE CHEQUES":
                clean_txt = self.__extract_between_slashes(libelle, 0, 0)
                df.at[index, "libelle_operation"] = self.__clean_libelle_spacing(clean_txt)

        return df


    # --- [ Utilitaires de Formatage ] ---
    def _excel_date_to_datetime(self, excel_date: float) -> datetime:
        """
        Convertit un nombre Excel en objet datetime.
        """
        if not isinstance(excel_date, (int, float)):
            return excel_date
        return datetime(1899, 12, 30) + timedelta(days=excel_date)

    def __extract_between_slashes(self, text: str, start: int, end: int) -> str:
        """
        Extrait le texte situé entre des slashs selon les indices fournis.
        """
        slash_positions = [i for i, char in enumerate(text) if char == '/']

        if end == 0 and slash_positions:
            return text[:slash_positions[0]].strip()

        if len(slash_positions) >= abs(end) and len(slash_positions) > start:
            return text[slash_positions[start] + 1:slash_positions[end]].strip()
        
        return text

    def __extract_date_from_libelle(self, libelle: str) -> (tuple[datetime, str] | tuple[None, None]):
        """
        Extrait une date jj/mm/aa après le mot clé 'DU'.
        """
        if "DU" in libelle:
            try:
                start_index = libelle.find("DU") + 3
                date_str = libelle[start_index:start_index+6]
                formatted_date = datetime.strptime(date_str, "%d%m%y")
                new_libelle = libelle[start_index+7:]
                return formatted_date, new_libelle
            except (ValueError, IndexError):
                return None, None
        return None, None

    def __clean_libelle_spacing(self, libelle: str) -> str:
        """
        Supprime le contenu après un double espace.
        """
        double_space_index = libelle.find("  ")
        if double_space_index != -1:
            return libelle[:double_space_index].strip()
        return libelle.strip()
