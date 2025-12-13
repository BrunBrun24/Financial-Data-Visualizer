import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import xlrd
from datetime import datetime, timedelta


def select_and_extract_data(initial_dir: str) -> (pd.DataFrame | None):
    """
    Ouvre un dialogue de sélection de fichier Excel dans un dossier donné et retourne les données extraites.

    Arguments :
    - initial_dir (str) : chemin du dossier initial où ouvrir l'explorateur de fichiers.

    Returns :
    - pd.DataFrame ou None : les données extraites si un fichier est sélectionné, sinon None.
    """
    file_path_holder = {"path": None}

    def open_file_dialog(root):
        file_path = filedialog.askopenfilename(
            title="Choisir un fichier",
            initialdir=initial_dir,
            filetypes=[
                ("Fichiers Excel", "*.xls *.xlsx"),
                ("Tous les fichiers", "*.*"),
            ]
        )
        if file_path:
            file_path_holder["path"] = file_path
            root.destroy()

    # Création fenêtre
    root = tk.Tk()
    root.title("Sélection du fichier")
    center_window(root, 400, 200)  # Centrage automatique

    message_label = tk.Label(root, text="Sélectionnez un fichier Excel.")
    message_label.pack(padx=20, pady=20)

    search_button = tk.Button(root, text="Rechercher un fichier", command=lambda: open_file_dialog(root))
    search_button.pack(pady=10)

    root.mainloop()

    if not file_path_holder["path"]:
        return None

    file_path = file_path_holder["path"]
    extension = file_path.lower().split('.')[-1]

    if extension in ["xls", "xlsx"]:
        data = extract_excel_data(file_path, f".{extension}")
    else:
        messagebox.showerror("Erreur", "Type de fichier non supporté.")
        return None

    return data

def center_window(window, width, height):
    """
    Centre une fenêtre Tkinter à l'écran.

    Args:
        window (tk.Tk): La fenêtre à centrer.
        width (int): La largeur de la fenêtre.
        height (int): La hauteur de la fenêtre.
    """
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    position_x = (screen_width // 2) - (width // 2)
    position_y = (screen_height // 2) - (height // 2)

    window.geometry(f'{width}x{height}+{position_x}+{position_y}')

def extract_excel_data(file_path, extension) -> (pd.DataFrame | None):
    """
    Extrait les données d'un fichier Excel (.xlsx ou .xls) et les formate en DataFrame.

    Args:
        file_path (str): Le chemin du fichier Excel à extraire.
        extension (str): L'extension du fichier ('.xlsx' ou '.xls').

    Returns:
        pd.DataFrame: Les données extraites et formatées en DataFrame.
    """
    assert isinstance(file_path, str), f"file_path doit être une chaîne de caractères, mais c'est {type(file_path).__name__}."
    assert isinstance(extension, str), f"extension doit être une chaîne de caractères, mais c'est {type(extension).__name__}."
    assert extension in ['.xlsx', '.xls'], f"L'extension doit être '.xlsx' ou '.xls', mais c'est {extension}."

    try:
        if extension == ".xls":
            data = []
            workbook = xlrd.open_workbook(file_path)
            sheet = workbook.sheet_by_index(0)
            for row_index in range(3, sheet.nrows):
                row = sheet.row_values(row_index, start_colx=0, end_colx=5)
                data.append(row)

        elif extension == ".xlsx":
            df = pd.read_excel(file_path, engine='openpyxl', skiprows=3, usecols="A:E", header=None)
            data = df.values.tolist()

        result = pd.DataFrame(data, columns=["date_operation", "libelle_court", "type_operation", "libelle_operation", "montant"])

        if not pd.api.types.is_datetime64_any_dtype(result["date_operation"]):
            result["date_operation"] = result["date_operation"].apply(excel_date_to_datetime)
            result["date_operation"] = pd.to_datetime(result["date_operation"])

        update_date_operation(result)
        result.sort_index(axis=1)
        return result

    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur s'est produite lors de la lecture du fichier Excel : {str(e)}")
        return None

def update_date_operation(df) -> pd.DataFrame:
    """
    Met à jour les dates dans la colonne 'date_operation' et nettoie 'libelle_operation' pour certains types d'opérations.

    Args:
        df (pd.DataFrame): Le DataFrame contenant les colonnes à mettre à jour.
    """
    assert isinstance(df, pd.DataFrame), f"df doit être un DataFrame, mais c'est {type(df).__name__}."
    name_columns = ["libelle_court", "date_operation", "type_operation"]
    for col in name_columns:
        assert col in df.columns, f"La colonne '{col}' est manquante dans le DataFrame."

    for index, row in df.iterrows():
        if row["libelle_court"] == "PAIEMENT CB":
            df.at[index, "libelle_operation"] = extract_between_slashes(row["libelle_operation"], 0, -2)
            new_date, new_libelle = extract_date_from_libelle(row["libelle_operation"])
            if new_date:
                df.at[index, "date_operation"] = new_date
            if new_libelle:
                df.at[index, "libelle_operation"] = clean_libelle(new_libelle)

        elif row["type_operation"] == "VIR CPTE A CPTE EMIS":
            df.at[index, "libelle_operation"] = clean_libelle(extract_between_slashes(row["libelle_operation"], 0, -2))

        elif row["type_operation"] in ["VIR CPTE A CPTE RECU", "VIR SEPA RECU"]:
            df.at[index, "libelle_operation"] = clean_libelle(extract_between_slashes(row["libelle_operation"], 0, -1))

        elif row["type_operation"] == "REMISE CHEQUES":
            df.at[index, "libelle_operation"] = clean_libelle(extract_between_slashes(row["libelle_operation"], 0, 0))

    return df

def excel_date_to_datetime(excel_date) -> datetime:
    """
    Convertit une date Excel en un objet datetime.

    Args:
        excel_date (float): La date au format Excel.

    Returns:
        datetime: La date convertie.
    """
    assert isinstance(excel_date, (int, float)), "excel_date doit être un nombre."
    return datetime(1899, 12, 30) + timedelta(days=excel_date)

def extract_between_slashes(text: str, start: int, end: int) -> str:
    """
    Extrait le texte entre différentes positions des '/' dans une chaîne.

    Args:
        text (str): La chaîne contenant plusieurs '/'.
        start (int): L'indice de départ pour l'extraction (position du premier '/').
        end (int): L'indice de fin pour l'extraction (position du dernier '/').
    
    Returns:
        str: Le texte extrait entre les positions 'start' et 'end'. Si les indices ne sont pas valides, retourne le texte original.
    """
    # Trouver tous les indices des '/'
    slash_positions = [i for i, char in enumerate(text) if char == '/']

    # Si 'end' est 0, on extrait avant le premier '/'
    if end == 0 and slash_positions:
        return text[:slash_positions[0]].strip()

    # S'assurer qu'il y a suffisamment de '/' pour les indices start et end
    if len(slash_positions) >= abs(end) and len(slash_positions) > start:
        start_text = slash_positions[start]
        end_text = slash_positions[end]

        # Extraire le texte entre les deux positions
        return text[start_text + 1:end_text].strip()
    else:
        # Si les indices ne correspondent pas aux positions disponibles, retourner le texte original
        return text

def extract_date_from_libelle(libelle: str) -> (tuple[datetime, str] | tuple[None, None]):
    """
    Extrait la date au format jj/mm/aa depuis la chaîne après 'DU' et retourne le reste du libellé.

    Args:
        libelle (str): Texte contenant l'opération avec la date.

    Returns:
        tuple: 
            - La date extraite en objet datetime ou None si non trouvée.
            - Le reste du libellé après la date ou None si non trouvée.
    """
    if "DU" in libelle:
        try:
            # Trouver l'indice de 'DU' et extraire la date (6 caractères après 'DU')
            start_index = libelle.find("DU") + 3
            date_str = libelle[start_index:start_index+6]

            # Convertir en datetime
            formatted_date = datetime.strptime(date_str, "%d%m%y")
            new_libelle = libelle[start_index+7:]
            return formatted_date, new_libelle
        except ValueError:
            return None, None
    return None, None

def clean_libelle(libelle: str) -> str:
    """
    Nettoie le libellé en supprimant le texte après le premier double espace.

    Args:
        libelle (str): Le texte du libellé à nettoyer.

    Returns:
        str: Le libellé nettoyé, sans le texte après le premier double espace.
    """
    # Trouver l'index du premier double espace
    double_space_index = libelle.find("  ")
    
    if double_space_index != -1:
        new_libelle = libelle[:double_space_index]
        return new_libelle.strip()

    # Si aucun double espace n'est trouvé, retourner le libellé tel quel
    return libelle
