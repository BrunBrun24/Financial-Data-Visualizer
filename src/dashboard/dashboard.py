from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd

from bank_accounts.bnp_paribas.excel_report_generator import ExcelReportGenerator as BnpParibasExcelReportGenerator
from bank_accounts.bnp_paribas.financial_chart import FinancialChart
from bank_accounts.bnp_paribas.operation_categorizer import OperationCategorizer
from dashboard.data_extractor import DataExtractor
from dashboard.operation_edit_window import OperationEditWindow
from database.bnp_paribas_database import BnpParibasDatabase


class FinancialVisualizerApp(ctk.CTk):
    """Interface principale de l'application Financial Data Visualizer."""

    DB_PATH = "data/bank_account.db"

    def __init__(self):
        super().__init__()

        self.db = BnpParibasDatabase(self.DB_PATH)
        self.db._create_database()
        self.db._verify_category_consistency()

        self.__setup_interface()

    # --- [ Initialisation UI ] ---
    def __setup_interface(self):
        """Création de l'interface graphique et centrage"""

        self.minsize(1000, 800)
        self.title("Financial Data Visualizer - Dashboard")

        # Lancement immédiat en mode maximisé
        self.after(10, lambda: self.wm_state("zoomed"))

        # Le reste de votre configuration...
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.__setup_navigation_frame()
        self.__setup_content_frames()

    def __setup_navigation_frame(self):
        """Crée la barre latérale de navigation."""

        self.nav_frame = ctk.CTkFrame(self, corner_radius=0)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")

        self.nav_label = ctk.CTkLabel(
            self.nav_frame,
            text="Financial Visualizer",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.nav_label.grid(row=0, column=0, padx=20, pady=20)

        # Boutons de navigation
        self.btn_add_banck_account = ctk.CTkButton(
            self.nav_frame,
            text="Gérer les comptes bancaires",
            command=self.__show_bank_accounts_view,
        )
        self.btn_add_banck_account.grid(row=1, column=0, padx=20, pady=10)

    def __setup_content_frames(self):
        """Initialise les conteneurs pour les différentes vues."""

        # Zone principale de contenu
        self.main_view = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_view.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # Placeholder pour le contenu dynamique
        self.content_label = ctk.CTkLabel(
            self.main_view,
            text="Page d'accueil",
            font=ctk.CTkFont(size=16),
        )
        self.content_label.pack(expand=True)

    # --- [ Gestion des Comptes Bancaires ] ---
    def __show_bank_accounts_view(self):
        """Affiche la liste des comptes."""

        for widget in self.main_view.winfo_children():
            widget.destroy()

        # Titre et bouton d'ajout (standard)
        ctk.CTkLabel(
            self.main_view,
            text="Gestion des Comptes Bancaires",
            font=("Arial", 24, "bold"),
        ).pack(pady=(10, 40))

        actions_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        actions_frame.pack(fill="x", pady=10)
        ctk.CTkButton(
            actions_frame,
            text="Ajouter un compte",
            fg_color="#28a745",
            command=self.__handle_add_account_dialog,
        ).pack(side="left", padx=20)

        scroll_frame = ctk.CTkScrollableFrame(self.main_view, width=950, height=450)
        scroll_frame.pack(pady=20, padx=20, fill="both", expand=True)

        header_table = ctk.CTkFrame(scroll_frame, fg_color="gray80")
        header_table.pack(fill="x", pady=(0, 10), padx=10)

        header_table.grid_columnconfigure(0, weight=3, uniform="group_trans")
        header_table.grid_columnconfigure((1, 2, 3), weight=2, uniform="group_trans")
        header_table.grid_columnconfigure((4, 5), weight=0, minsize=85)  # Boutons Modifier / Supprimer

        header_labels = [
            "Nom du compte",
            "Nombre d'opérations",
            "Opérations catégorisées",
            "Opérations restantes",
            "Actions",
        ]

        for i, col_name in enumerate(header_labels):
            if col_name == "Actions":
                ctk.CTkLabel(
                    header_table,
                    text=col_name,
                    font=("Arial", 14, "bold"),
                    text_color="black",
                    anchor="center",
                ).grid(row=0, column=i, columnspan=2, padx=5, pady=5, sticky="nsew")
            else:
                # On centre tout pour que les données soient sous le milieu du titre
                ctk.CTkLabel(header_table, text=col_name, font=("Arial", 14, "bold"), text_color="black").grid(
                    row=0, column=i, padx=10, pady=10, sticky="nsew"
                )

        try:
            bank_account_df = self.db._get_table_df("bank_account")
            if not bank_account_df.empty:
                for index, row in bank_account_df.iterrows():

                    def on_row_click(event, r=row):
                        self.__manage_account_content(r)

                    stats = self.db.get_account_statistics(row["id"])
                    row_bg = "gray95" if index % 2 == 0 else "gray90"

                    row_frame = ctk.CTkFrame(scroll_frame, fg_color=row_bg, cursor="hand2")
                    row_frame.pack(fill="x", pady=2, padx=10)

                    row_frame.grid_columnconfigure(0, weight=3, uniform="group_trans")
                    row_frame.grid_columnconfigure((1, 2, 3), weight=2, uniform="group_trans")
                    row_frame.grid_columnconfigure((4, 5), weight=0, minsize=85)  # Boutons Modifier / Supprimer

                    row_frame.bind("<Button-1>", on_row_click)

                    lbl_name = ctk.CTkLabel(row_frame, text=f"{row['name']}", font=("Arial", 13, "bold"))
                    lbl_name.grid(row=0, column=0, pady=10, sticky="nsew")
                    lbl_name.bind("<Button-1>", on_row_click)

                    lbl_total = ctk.CTkLabel(row_frame, text=str(stats["total"]))
                    lbl_total.grid(row=0, column=1, sticky="nsew")
                    lbl_total.bind("<Button-1>", on_row_click)

                    lbl_proc = ctk.CTkLabel(row_frame, text=f"✅ {stats['processed']}", text_color="#28a745")
                    lbl_proc.grid(row=0, column=2, sticky="nsew")
                    lbl_proc.bind("<Button-1>", on_row_click)

                    rem_color = "#dc3545" if stats["remaining"] > 0 else "#28a745"
                    lbl_rem = ctk.CTkLabel(row_frame, text=f"⏳ {stats['remaining']}", text_color=rem_color)
                    lbl_rem.grid(row=0, column=3, sticky="nsew")
                    lbl_rem.bind("<Button-1>", on_row_click)

                    ctk.CTkButton(
                        row_frame,
                        text="Renommer",
                        width=75,
                        height=22,
                        command=lambda r=row: self.__handle_edit_account_dialog(r["id"], r["name"]),
                    ).grid(row=0, column=4, padx=5, pady=5)

                    ctk.CTkButton(
                        row_frame,
                        text="Supprimer",
                        width=75,
                        height=22,
                        fg_color="#dc3545",
                        command=lambda r=row: self.__handle_delete_account(r["id"], r["name"]),
                    ).grid(row=0, column=5, padx=5, pady=5)

            else:
                ctk.CTkLabel(scroll_frame, text="Aucun compte enregistré.").pack(pady=30)

        except Exception as e:
            ctk.CTkLabel(scroll_frame, text=f"Erreur : {e}", text_color="red").pack(pady=20)

    def __handle_add_account_dialog(self):
        """Ouvre une boîte de dialogue pour créer un nouveau compte bancaire."""

        dialog = ctk.CTkInputDialog(text="Entrez le nom du nouveau compte :", title="Nouveau Compte")
        self.__window_center(dialog)
        dialog.transient(self)
        dialog.attributes("-topmost", False)

        account_name = dialog.get_input()

        if account_name:
            try:
                self.db.add_bank_account(account_name)
                self.__show_bank_accounts_view()
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de créer le compte : {e}")
                raise

    def __handle_delete_account(self, account_id: int, account_name: str):
        """Demande confirmation avant de supprimer un compte et ses données."""

        if messagebox.askyesno(
            "Confirmation",
            f"Supprimer le compte '{account_name}' ?\nCette action est irréversible.",
        ):
            try:
                self.db.delete_bank_account(account_id)
                self.__show_bank_accounts_view()
            except Exception as e:
                messagebox.showerror(f"Erreur lors de la suppression du compte : {str(e)}")
                raise

    def __handle_edit_account_dialog(self, account_id: int, old_name: str):
        """Ouvre un dialogue centré et immobile pour renommer le compte."""

        dialog = ctk.CTkInputDialog(text=f"Nouveau nom pour '{old_name}' :", title="Renommer")
        self.__window_center(dialog)
        dialog.transient(self)
        dialog.attributes("-topmost", False)

        new_name = dialog.get_input()

        if new_name and new_name != old_name:
            try:
                self.db.update_bank_account_name(account_id, new_name)
                self.__update_bilan(new_name)
                self.__show_bank_accounts_view()
            except Exception as e:
                messagebox.showerror(f"Erreur lors de la modification du nom du compte : {str(e)}")
                raise

    # --- [ Gestion des Opérations ] ---
    def __manage_account_content(self, account_row: dict):
        """Affiche l'interface de gestion détaillée d'un compte spécifique."""

        for widget in self.main_view.winfo_children():
            widget.destroy()

        account_id = account_row["id"]
        account_name = account_row["name"]

        # 1. Header de navigation
        nav_header = ctk.CTkFrame(self.main_view, fg_color="transparent")
        nav_header.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            nav_header,
            text="← Retour",
            width=80,
            command=self.__show_bank_accounts_view,
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            self.main_view,
            text=f"Gestion du compte : {account_name}",
            font=("Arial", 22, "bold"),
        ).pack(pady=(5, 15))

        # 2. Barre d'actions
        account_actions_bar = ctk.CTkFrame(self.main_view, fg_color="transparent")
        account_actions_bar.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            account_actions_bar,
            text="Importer des opérations",
            fg_color="#28a745",
            command=lambda: self.__handle_import_process(account_row),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            account_actions_bar,
            text="Ajouter une opération",
            fg_color="#28a745",
            command=lambda: self.__handle_add_operation(account_row),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            account_actions_bar,
            text="Catégoriser les opérations",
            fg_color="#7428a7",
            command=lambda: self.__handle_categorization_process(account_row),
        ).pack(side="left", padx=5)

        # Tableau des opérations
        scroll_frame = ctk.CTkScrollableFrame(self.main_view, width=1100, height=500)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. Configuration de l'en-tête
        header_table = ctk.CTkFrame(scroll_frame, fg_color="gray80")
        header_table.pack(fill="x", pady=(0, 5))

        header_table.grid_columnconfigure(0, weight=0, minsize=40)  # #
        header_table.grid_columnconfigure((1, 3, 4, 5), weight=1, uniform="group_trans")  # Date, Cat, SCat, Montant
        header_table.grid_columnconfigure(2, weight=3, uniform="group_trans")  # Libellé
        header_table.grid_columnconfigure((6, 7), weight=0, minsize=85)  # Boutons Modifier / Supprimer

        columns = [
            "#",
            "Date",
            "Libellé",
            "Catégorie",
            "Sous-Catégorie",
            "Montant",
            "Actions",
        ]

        for i, col_name in enumerate(columns):
            padx = 40 if i == 0 else 5
            anchor_val = "w" if i in [1, 2, 3, 4] else "center"

            if col_name == "Actions":
                ctk.CTkLabel(
                    header_table,
                    text=col_name,
                    font=("Arial", 14, "bold"),
                    text_color="black",
                    anchor="center",
                ).grid(row=0, column=i, columnspan=2, padx=5, pady=5, sticky="nsew")
            else:
                ctk.CTkLabel(
                    header_table,
                    text=col_name,
                    font=("Arial", 14, "bold"),
                    text_color="black",
                    anchor=anchor_val,
                ).grid(row=0, column=i, padx=padx, pady=5, sticky="nsew")

        # 2. Récupération et affichage
        try:
            categorized_operations = self.db.get_operations_by_account(account_id)

            if not categorized_operations.empty:
                # On calcule les IDs par date (ancienne -> récente)
                categorized_operations = categorized_operations.sort_values(by="operation_date", ascending=True)
                categorized_operations["id_view"] = range(1, len(categorized_operations) + 1)
                categorized_operations = categorized_operations.sort_values(by="operation_date", ascending=False)

                for i, (index, operation) in enumerate(categorized_operations.iterrows(), 1):
                    row_bg = "gray95" if i % 2 == 0 else "gray90"
                    row_f = ctk.CTkFrame(scroll_frame, fg_color=row_bg)
                    row_f.pack(fill="x", pady=1)

                    # Répétition de la grille
                    row_f.grid_columnconfigure(0, weight=0, minsize=40)
                    row_f.grid_columnconfigure((1, 3, 4, 5), weight=1, uniform="group_trans")
                    row_f.grid_columnconfigure(2, weight=3, uniform="group_trans")
                    row_f.grid_columnconfigure((6, 7), weight=0, minsize=85)

                    # Données
                    ctk.CTkLabel(
                        row_f,
                        text=str(operation["id_view"]),
                        font=("Arial", 11, "italic"),
                        anchor="center",
                    ).grid(row=0, column=0, padx=40, sticky="nsew")
                    ctk.CTkLabel(row_f, text=operation["operation_date"], anchor="w").grid(
                        row=0, column=1, padx=5, sticky="nsew"
                    )
                    ctk.CTkLabel(row_f, text=operation["libelle_operation"], anchor="w").grid(
                        row=0, column=2, padx=5, sticky="nsew"
                    )
                    ctk.CTkLabel(row_f, text=operation["category"], anchor="w").grid(
                        row=0, column=3, padx=5, sticky="nsew"
                    )
                    ctk.CTkLabel(row_f, text=operation["sub_category"], anchor="w").grid(
                        row=0, column=4, padx=5, sticky="nsew"
                    )

                    if operation["amount"] % 1 == 0:
                        # Montant entier : on formate sans décimales
                        formatted_amount = f"{int(operation['amount']):,}".replace(",", " ")
                    else:
                        # Montant avec centimes : on garde 2 décimales
                        formatted_amount = f"{operation['amount']:,.2f}".replace(",", " ")

                    color = "#dc3545" if operation["amount"] < 0 else "#28a745"
                    ctk.CTkLabel(
                        row_f,
                        text=f"{formatted_amount} €",
                        text_color=color,
                        font=("Arial", 12, "bold"),
                        anchor="center",
                    ).grid(row=0, column=5, padx=5, sticky="nsew")

                    # Boutons d'actions
                    ctk.CTkButton(
                        row_f,
                        text="Modifier",
                        width=75,
                        height=22,
                        command=lambda o=operation: self.__handle_edit_operation(o, account_row),
                        anchor="center",
                    ).grid(row=0, column=6, padx=5, pady=5)

                    ctk.CTkButton(
                        row_f,
                        text="Supprimer",
                        width=75,
                        height=22,
                        fg_color="#dc3545",
                        command=lambda o_id=operation["id"]: self.__handle_delete_operation(account_row, o_id),
                        anchor="center",
                    ).grid(row=0, column=7, padx=5, pady=5)
            else:
                ctk.CTkLabel(scroll_frame, text="Aucune operation.").pack(pady=40)

        except Exception as e:
            ctk.CTkLabel(scroll_frame, text=f"Erreur : {e}", text_color="red").pack(pady=20)

    def __handle_add_operation(self, account_row):
        """Ouvre la fenêtre pour ajouter une nouvelle opération."""

        # On définit les valeurs par défaut pour une nouvelle ligne
        default_op = {
            "id": None,  # None indique à la BDD qu'il s'agit d'une insertion
            "operation_date": datetime.now().strftime("%Y-%m-%d"),
            "libelle_operation": "",
            "amount": "0.00",
            "category": list(self.db._get_categories(account_row["id"]).keys())[0]
            if self.db._get_categories(account_row["id"])
            else "",
            "sub_category": "",
        }

        win = OperationEditWindow(
            parent=self.main_view,
            db=self.db,
            bank_account_id=account_row["id"],
            operation=default_op,
            on_save_callback=lambda data: self.__process_add(data, account_row),
        )
        win.title("Ajouter une opération")

    def __handle_delete_operation(self, account_row: dict, operation_id: int):
        """Gère la suppression d'une opération et rafraîchit l'affichage."""

        self.db.delete_operation(account_row["id"], operation_id)
        self.__update_bilan(account_row["name"])
        self.__manage_account_content(account_row)

    def __handle_edit_operation(self, operation: dict, account_row: dict):
        """Ouvre la fenêtre de modification pour une opération donnée."""

        OperationEditWindow(
            self.main_view,
            self.db,
            account_row["id"],
            operation,
            lambda data: self.__process_update(data, account_row),
        )

    def __handle_import_process(self, account_row: dict):
        """Lance l'extraction et injecte le nom du compte sélectionné dans les données."""

        try:
            extractor = DataExtractor("data/bnp paribas/Compte Chèques/")  # TODO Changer le chemin
            df = extractor.run_extraction(account_row["id"])

            if df is None:
                return

            df["bank_account_id"] = account_row["id"]
            self.db.add_operations(df, False)

            # Catégorise les différentes opérations
            categorizer = OperationCategorizer(self, self.DB_PATH, account_row["id"])
            cat_window = categorizer.categorize()

            if cat_window and cat_window.winfo_exists():
                self.wait_window(cat_window)

            self.__update_bilan(account_row["name"])

            messagebox.showinfo(
                "Succès",
                f"Données importées avec succès pour le compte : {account_row['name']}",
            )
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'insertion : {e}")
            raise

    def __handle_categorization_process(self, account_row: dict):
        """Lance le processus de catégorisation."""

        try:
            categorizer = OperationCategorizer(self, self.DB_PATH, account_row["id"])
            cat_window = categorizer.categorize()

            if cat_window and cat_window.winfo_exists():
                self.wait_window(cat_window)

            if categorizer.has_changed:
                self.__update_bilan(account_row["name"])
                self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la catégorisation : {e}")
            raise

    def __process_add(self, new_operation: dict, account_row: dict):
        """Met à jour la base de données et rafraîchit l'affichage."""

        try:
            df = pd.DataFrame([new_operation])
            df["short_label"] = [""]  # TODO à enlever plus tard avec modification de la BDD
            df["operation_type"] = [""]  # TODO à enlever plus tard avec modification de la BDD
            self.db.add_operations(df, True)
            self.__update_bilan(account_row["name"])
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {e}")
            raise

    def __process_update(self, updated_data: dict, account_row: dict):
        """Met à jour la base de données et rafraîchit l'affichage."""

        try:
            self.db.update_operation(account_row["id"], updated_data)
            self.__update_bilan(account_row["name"])
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour : {e}")
            raise

    def __update_bilan(self, account_name: str):
        """Coordonne la mise à jour complète des fichiers bilan pour un compte bancaire."""

        # Créer les graphiques HTML
        chart_generator = FinancialChart(self.DB_PATH, account_name)
        chart_generator.generate_all_reports()

        # Créer les fichiers Excel
        excel_generator = BnpParibasExcelReportGenerator(self.DB_PATH, account_name)
        excel_generator.generate_all_reports()

    # --- [ Méthodes Annexes ]
    def __window_center(self, window: ctk.CTkInputDialog):
        """Centre une fenêtre au milieu de la fenêtre"""

        # Calcul des coordonnées pour centrer par rapport à l'application (self)
        x = self.winfo_x() + (self.winfo_width() // 2) - (window.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (window.winfo_height() // 2)

        window.geometry(f"+{x}+{y}")

        window.geometry(f"+{x}+{y}")

        window.geometry(f"+{x}+{y}")

        window.geometry(f"+{x}+{y}")

        window.geometry(f"+{x}+{y}")
