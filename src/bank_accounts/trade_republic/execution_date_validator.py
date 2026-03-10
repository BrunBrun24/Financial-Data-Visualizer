import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog

import pandas as pd


class ExecutionDateValidator:
    """
    Cette classe gère une interface utilisateur Tkinter permettant de valider ou de 
    corriger les dates d'exécution au sein d'un DataFrame financier.

    L'encapsulation est stricte et les noms de colonnes ('date' et 'ticker') 
    sont prédéfinis selon la structure standard des transactions.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialise l'interface avec le DataFrame fourni.

        Args:
            data (pd.DataFrame): Le jeu de données contenant les colonnes 'date' et 'ticker'.
        """
        assert isinstance(data, pd.DataFrame), "Le paramètre data doit être un DataFrame."
        assert 'date' in data.columns, "La colonne 'date' est absente du DataFrame."
        assert 'ticker' in data.columns, "La colonne 'ticker' est absente du DataFrame."
        
        self.__data = data.copy()
        self.__date_column = 'date'
        self.__ticker_column = 'ticker'
        self.__unique_dates = sorted(self.__data[self.__date_column].unique())
        self.__index = 0

        # Configuration de la fenêtre principale
        self.__root = tk.Tk()
        self.__root.title("Validation de la Date d'Exécution")
        self.__setup_window_geometry()


    # --- [ Interface Utilisateur & Validation ] ---
    def run(self) -> pd.DataFrame:
        """
        Lance la boucle principale de l'interface graphique.

        Returns:
            pd.DataFrame: Le DataFrame avec les dates potentiellement corrigées.
        """
        if self.__data is not None and not self.__data.empty:
            self.__display_next_step()
            self.__root.mainloop()
        return self.__data

    def __display_next_step(self):
        """Détermine si une nouvelle date doit être affichée ou si le processus est fini"""
        if self.__index < len(self.__unique_dates):
            current_date = self.__unique_dates[self.__index]
            # Filtrage des tickers associés à la date actuelle
            tickers = self.__data[self.__data[self.__date_column] == current_date][self.__ticker_column].tolist()
            self.__ask_user_validation(current_date, tickers)
        else:
            self.__root.quit()
            self.__root.destroy()

    def __process_confirmation(self):
        """Passe à la date suivante après validation positive"""
        self.__index += 1
        self.__display_next_step()

    def __process_correction(self, original_date: datetime):
        """Ouvre un dialogue pour corriger la date avant de passer à la suivante"""
        current_date_ref = self.__unique_dates[self.__index]

        while True:
            default_val = original_date.strftime("%Y-%m-%d") if hasattr(original_date, 'strftime') else str(original_date)            
            user_input = simpledialog.askstring(
                "Correction",
                "Entrez la date (YYYY-MM-DD) :",
                initialvalue=default_val,
                parent=self.__root
            )

            if user_input:
                try:
                    new_date_obj = datetime.strptime(user_input, "%Y-%m-%d").date()
                    # Mise à jour de toutes les lignes correspondant à l'ancienne date
                    self.__data.loc[self.__data[self.__date_column] == current_date_ref, self.__date_column] = new_date_obj
                    self.__index += 1
                    break
                except ValueError:
                    messagebox.showerror("Erreur", "Format invalide (YYYY-MM-DD requis).")
            else:
                messagebox.showinfo("Info", "Aucune modification, passage au suivant.")
                self.__index += 1
                break

        self.__display_next_step()

    def __setup_window_geometry(self):
        """Calcule et applique le centrage de la fenêtre sur l'écran"""
        width, height = 1250, 650
        screen_w = self.__root.winfo_screenwidth()
        screen_h = self.__root.winfo_screenheight()
        pos_x = int(screen_w / 2 - width / 2)
        pos_y = int(screen_h / 2 - height / 2)
        self.__root.geometry(f'{width}x{height}+{pos_x}+{pos_y}')

    def __ask_user_validation(self, execution_date: datetime, tickers: list):
        """
        Affiche une interface de confirmation utilisateur pour valider la date 
        d'exécution et la liste des actifs financiers (tickers).

        Args:
            execution_date (datetime): La date prévue pour l'exécution des opérations.
            tickers (list): Liste des symboles d'actifs financiers à vérifier.
        """
        self.__clear_layout()

        # Formatage de la date pour l'affichage (ex: 4 December 2023)
        try:
            formatted_date = f"{execution_date.day} {execution_date.strftime('%B')} {execution_date.year}"
        except AttributeError:
            formatted_date = str(execution_date)

        header_text = f"La date d'exécution suivante est-elle correcte ?\n\n📅 {formatted_date}"
        tk.Label(self.__root, text=header_text, font=("Arial", 14), pady=10).pack()

        # Affichage conditionnel selon le nombre de tickers
        if len(tickers) > 40:
            self.__build_scrollable_list(tickers)
        else:
            self.__build_grid_list(tickers)

        # Zone des boutons d'action
        actions_frame = tk.Frame(self.__root)
        actions_frame.pack(side="bottom", pady=20)

        tk.Button(actions_frame, text="Oui", bg="lightgreen", padx=20, pady=10,
                  command=self.__process_confirmation).pack(side="left", padx=10)

        tk.Button(actions_frame, text="Non", bg="salmon", padx=20, pady=10,
                  command=lambda: self.__process_correction(execution_date)).pack(side="right", padx=10)

    def __build_scrollable_list(self, tickers: list):
        """
        Génère et affiche une zone de texte interactive avec barre de défilement 
        pour visualiser une liste importante de tickers.

        Args:
            tickers (list): Liste des symboles financiers à afficher.
        """
        container = tk.Frame(self.__root)
        container.pack(pady=10)
        
        scroll = tk.Scrollbar(container)
        scroll.pack(side="right", fill="y")

        text_area = tk.Text(container, height=15, width=50, font=("Arial", 12), yscrollcommand=scroll.set)
        text_area.pack(side="left", fill="both", expand=True)
        scroll.config(command=text_area.yview)

        for ticker in tickers:
            text_area.insert("end", f"• {ticker}\n")
        text_area.config(state="disabled")

    def __build_grid_list(self, tickers: list):
        """
        Génère une disposition en grille pour afficher les tickers de manière 
        organisée et compacte sur plusieurs colonnes.

        Args:
            tickers (list): Liste des symboles financiers à afficher.
        """
        grid_container = tk.Frame(self.__root)
        grid_container.pack(pady=10)

        for i, ticker in enumerate(tickers):
            tk.Label(grid_container, text=f"• {ticker}", font=("Arial", 12), padx=10, pady=5).grid(
                row=i // 5, column=i % 5, padx=5, pady=5
            )

    def __clear_layout(self):
        """Supprime tous les widgets existants dans la fenêtre avant de redessiner"""
        for widget in self.__root.winfo_children():
            widget.destroy()
