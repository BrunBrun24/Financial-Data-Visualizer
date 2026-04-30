import os
import shutil
import subprocess
import unicodedata
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
from PIL import Image

from bank_accounts.bnp_paribas.excel_report_generator import ExcelReportGenerator as BnpParibasExcelReportGenerator
from bank_accounts.bnp_paribas.financial_chart import FinancialChart
from bank_accounts.bnp_paribas.operation_categorizer import OperationCategorizer
from config import load_config, save_config
from dashboard.data_extractor import DataExtractor
from dashboard.operation_edit_window import OperationEditWindow
from database.bnp_paribas_database import BnpParibasDatabase


class Dashboard(ctk.CTk):
    """Interface principale de l'application Financial Data Visualizer."""

    def __init__(self) -> None:
        super().__init__()

        self.__config = load_config()
        self.__theme = self.__config["theme"]
        self.__db_path = self.__config["database"]["database_path"]
        self.__db = BnpParibasDatabase(self.__db_path)

        # Tri des opérations pour la gestion des comptes
        self.__sort_column = "operation_date"
        self.__sort_ascending = False

        self.__setup_interface()

    # --- [ Initialisation UI ] ---
    def __setup_interface(self) -> None:
        """Création de l'interface graphique et centrage"""

        self.title("Financial Data Visualizer - Dashboard")
        self.minsize(1000, 800)

        # Lancement immédiat en mode maximisé
        self.after(10, lambda: self.wm_state("zoomed"))

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Zone principale de contenu
        self.main_view = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_view.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.__setup_navigation_frame()
        self.__home_page()

    def __setup_navigation_frame(self) -> None:
        """Crée une barre latérale étroite avec des icônes."""

        # Configuration de la largeur de la barre
        self.nav_frame = ctk.CTkFrame(self, corner_radius=0, width=70)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_rowconfigure(4, weight=1)

        icon_size = (28, 28)
        home_icon = ctk.CTkImage(light_image=Image.open("src/static/img/home.png"), size=icon_size)
        account_icon = ctk.CTkImage(light_image=Image.open("src/static/img/account.png"), size=icon_size)
        stock_icon = ctk.CTkImage(light_image=Image.open("src/static/img/stock.png"), size=icon_size)
        heritage_icon = ctk.CTkImage(light_image=Image.open("src/static/img/heritage.png"), size=icon_size)
        edit_icon = ctk.CTkImage(light_image=Image.open("src/static/img/edit.png"), size=icon_size)
        information_icon = ctk.CTkImage(light_image=Image.open("src/static/img/information.png"), size=icon_size)

        # Bouton home
        ctk.CTkButton(
            self.nav_frame,
            text="",
            image=home_icon,
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=self.__home_page,
        ).grid(row=0, column=0, padx=10, pady=(20, 10))

        # Bouton account
        ctk.CTkButton(
            self.nav_frame,
            text="",
            image=account_icon,
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=self.__show_accounts_view,
        ).grid(row=1, column=0, padx=10, pady=(10, 20))

        # Bouton stock
        ctk.CTkButton(
            self.nav_frame,
            text="",
            image=stock_icon,
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=self.__home_page,  # TODO
        ).grid(row=2, column=0, padx=10, pady=(10, 20))

        # Bouton heritage
        ctk.CTkButton(
            self.nav_frame,
            text="",
            image=heritage_icon,
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=self.__home_page,  # TODO
        ).grid(row=3, column=0, padx=10, pady=(10, 20))

        # Bouton edit
        ctk.CTkButton(
            self.nav_frame,
            text="",
            image=edit_icon,
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=self.__manage_config_view,
        ).grid(row=5, column=0, padx=10, pady=10)

        # Bouton information
        ctk.CTkButton(
            self.nav_frame,
            text="",
            image=information_icon,
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
            command=self.__home_page,  # TODO
        ).grid(row=6, column=0, padx=10, pady=10)

    # -- [ Modification des informations ] ---
    def __manage_config_view(self) -> None:
        """Affiche la page de configuration"""

        self.__destroy_widgets()

        # 1. Header
        header_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        # On met un pady en bas pour créer l'espace avec les cartes
        header_frame.pack(fill="x", padx=20, pady=(40, 20))

        title_label = ctk.CTkLabel(header_frame, text="Configuration", font=("Arial", 60, "bold"))
        title_label.pack()

        # 2. Conteneur principal (prend toute la largeur)
        grid_container = ctk.CTkFrame(self.main_view, fg_color="transparent")
        grid_container.pack(fill="x", pady=40)

        # 3. Conteneur interne (centré horizontalement par défaut avec pack)
        # Ce frame contiendra les colonnes de cartes
        inner_container = ctk.CTkFrame(grid_container, fg_color="transparent")
        inner_container.pack()

        # Banque
        self.__create_module_card(
            inner_container,
            0,
            0,
            "Source Bancaire",
            "Renseignez ici les établissements bancaires que vous utilisez au quotidien, tels que la BNP Paribas, Boursorama ou le Crédit Agricole. Cette étape est essentielle pour identifier la provenance de vos flux financiers et permettre à l'application d'extraire et de traiter correctement vos données par la suite pour vos analyses.",
            "src/static/img/account.png",
            self.__config["bank"],
            command=self.__update_config_bank,
            widget_type="menu",
            menu_values=["Non défini", "BNP Paribas"],
            width=550,
            height=300,
        )

        # Exemple avec une carte standard
        self.__create_module_card(
            inner_container,
            0,
            1,
            "Architecture",
            "Optimisez la structure de votre budget en créant un système personnalisé de catégories et de sous-catégories. Cette flexibilité vous permet de classer précisément chaque transaction, qu'il s'agisse de revenus récurrents ou de dépenses imprévues, pour une analyse financière détaillée.",
            "src/static/img/file.png",
            "Gérer",
            command=self.__manage_config_categorization,
            width=550,
            height=300,
        )

    def __create_module_card(
        self,
        parent,
        row,
        col,
        title,
        desc,
        icon_path,
        action_text,
        command,
        widget_type="button",
        menu_values=None,
        color="blue_01",
        width=320,
        height=360,
    ) -> None:
        """Créez une carte spécialisée"""

        # Création de la carte avec taille fixe
        card = ctk.CTkFrame(parent, corner_radius=20, border_width=1, width=width, height=height)
        card.grid(row=row, column=col, padx=15, pady=15, sticky="n")

        # Bloque la taille pour qu'elle ne bouge pas
        card.pack_propagate(False)

        # Icône
        img = ctk.CTkImage(light_image=Image.open(icon_path), size=(45, 45))
        ctk.CTkLabel(card, image=img, text="").pack(pady=(25, 10))

        # Titre
        ctk.CTkLabel(card, text=title, font=("Arial", 20, "bold")).pack(pady=5)

        # Description
        ctk.CTkLabel(
            card, text=desc, text_color="gray", font=("Arial", 13), wraplength=width - 40, justify="center"
        ).pack(pady=5, padx=20)

        spacer = ctk.CTkFrame(card, fg_color="transparent", height=0)
        spacer.pack(expand=True, fill="both")

        # On place le widget dans un petit frame en bas pour assurer sa visibilité
        action_container = ctk.CTkFrame(card, fg_color="transparent")
        action_container.pack(side="bottom", pady=(0, 25))

        if widget_type == "menu":
            self.temp_var = ctk.StringVar(value=action_text)
            widget = ctk.CTkOptionMenu(
                action_container,
                values=menu_values if menu_values else ["Options"],
                variable=self.temp_var,
                command=command,
                width=width * 0.25,
                height=30,
                corner_radius=10,
                fg_color=self.__theme[color]["fg_color"],
                button_color=self.__theme[color]["hover_color"],
            )
        else:
            widget = ctk.CTkButton(
                action_container,
                text=action_text,
                command=command,
                width=width * 0.25,
                height=30,
                corner_radius=10,
                fg_color=self.__theme[color]["fg_color"],
                hover_color=self.__theme[color]["hover_color"],
            )

        widget.pack()

    def __update_config_bank(self, bank: str):
        """Met à jour la banque dans le fichier de configuration"""

        try:
            full_config = load_config()
            full_config["bank"] = bank

            save_config(full_config)
            self.__config = load_config()
            self.__db = BnpParibasDatabase(self.__db_path)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'écriture du fichier : {e}")
            raise

    def __manage_config_categorization(self) -> None:
        """Affiche la page de gestion des catégories et sous-catégories."""

        self.__destroy_widgets()

        # On stocke une copie de travail pour ne pas modifier le fichier instantanément
        self.temp_config = load_config()
        self.entry_widgets = {"incomes": {}, "expenses": {}}

        # Header
        header_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(header_frame, text="Configuration des Catégories", font=("Arial", 30, "bold")).pack(pady=(5, 10))

        # Zone d'onglets
        tabview = ctk.CTkTabview(
            self.main_view,
            corner_radius=15,
            segmented_button_selected_color=self.__theme["blue_01"]["fg_color"],
        )
        tabview.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_inc = tabview.add("Revenus")
        self.tab_exp = tabview.add("Dépenses")

        # Remplissage initial
        self.__draw_config_form("incomes")
        self.__draw_config_form("expenses")

        # Bouton Enregistrer Global
        save_all_btn = ctk.CTkButton(
            self.main_view,
            text="ENREGISTRER TOUTES LES MODIFICATIONS",
            font=("Arial", 14, "bold"),
            height=45,
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=self.__validate_and_save_all,
        )
        save_all_btn.pack(fill="x", padx=20, pady=15)

    def __draw_config_form(self, section_key: str) -> None:
        """Dessine les catégories avec un système d'accordéon (caché par défaut)."""

        tab = self.tab_inc if section_key == "incomes" else self.tab_exp
        for widget in tab.winfo_children():
            widget.destroy()

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # On récupère les catégories et on les transforme en liste pour gérer par index
        categories_dict = self.temp_config["database"][section_key]["categories_subcategories"]
        cat_names_list = list(categories_dict.keys())

        self.entry_widgets[section_key]["categories_subcategories"] = {}

        for cat_id, cat_name in enumerate(cat_names_list):
            sub_cats = categories_dict[cat_name]

            # Frame principale de la ligne catégorie
            cat_row_frame = ctk.CTkFrame(scroll, fg_color=("gray95", "gray20"), corner_radius=10)
            cat_row_frame.pack(fill="x", pady=8, padx=5)

            # Header : Flèche | Nom | Poubelle
            header_line = ctk.CTkFrame(cat_row_frame, fg_color="transparent")
            header_line.pack(fill="x", padx=10, pady=5)

            # Zone grid pour les sous catégories (Cachée par défaut)
            sub_container = ctk.CTkFrame(cat_row_frame, fg_color="transparent")

            # Fonction pour basculer l'affichage
            def toggle_subcats(c=sub_container, b=None):
                if c.winfo_viewable():
                    c.pack_forget()
                    b.configure(text="▶")
                else:
                    c.pack(fill="x", padx=10, pady=(0, 10))
                    b.configure(text="▼")

            # Bouton Flèche pour ouvrir/fermer
            toggle_btn = ctk.CTkButton(
                header_line,
                text="▶",
                width=30,
                height=30,
                fg_color="transparent",
                text_color=("black", "white"),
                font=("Arial", 16, "bold"),
                hover_color=("gray80", "gray40"),
            )
            toggle_btn.configure(command=lambda c=sub_container, b=toggle_btn: toggle_subcats(c, b))
            toggle_btn.pack(side="left", padx=(0, 5))

            # Entrée pour le nom de la catégorie
            name_entry = ctk.CTkEntry(header_line, width=250, placeholder_text="Catégorie", font=("Arial", 13, "bold"))

            # On n'insère le texte que si ce n'est pas une "Nouvelle_cat_"
            if not cat_name.startswith("Nouvelle_cat_"):
                name_entry.insert(0, cat_name)

            name_entry.pack(side="left", pady=5)

            # Bouton Supprimer
            ctk.CTkButton(
                header_line,
                text="Supprimer",
                width=30,
                height=30,
                fg_color=self.__theme["red"]["fg_color"],
                hover_color=self.__theme["red"]["hover_color"],
                command=lambda s=section_key, i=cat_id: self.__remove_temp_row_by_index(s, i),
            ).pack(side="right", padx=5)

            # Logique interne des sous-catégories
            sub_container.badge_frames = []
            current_sub_entries = []

            def refresh_sub_layout(container=sub_container):
                max_cols = 5
                for col in range(max_cols):
                    container.grid_columnconfigure(col, weight=1, uniform="sub_cat_col")

                for child in container.winfo_children():
                    child.grid_forget()

                for i, badge_frame in enumerate(container.badge_frames):
                    r, c = divmod(i, max_cols)
                    badge_frame.grid(row=r, column=c, padx=5, pady=3, sticky="ew")

                idx_next = len(container.badge_frames)
                r_btn, c_btn = divmod(idx_next, max_cols)
                container.add_btn_widget.grid(row=r_btn, column=c_btn, padx=5, pady=5, sticky="w")

            def add_sub_logic(val="", container=sub_container, entries_list=current_sub_entries, rf=refresh_sub_layout):
                badge_fr, entry_widget = self.__create_sub_badge(container, val, entries_list, rf)
                container.badge_frames.append(badge_fr)
                entries_list.append(entry_widget)
                rf()

            sub_container.add_btn_widget = ctk.CTkButton(
                sub_container, text="+", width=28, height=28, corner_radius=14, command=add_sub_logic
            )

            for s_name in sub_cats:
                add_sub_logic(s_name)

            # Stockage des widgets pour la sauvegarde
            self.entry_widgets[section_key]["categories_subcategories"][cat_id] = (name_entry, current_sub_entries)

        # Bouton d'Ajout
        add_cat_container = ctk.CTkFrame(scroll, fg_color="transparent")
        add_cat_container.pack(fill="x", pady=10)

        ctk.CTkButton(
            add_cat_container,
            text="+ Ajouter une catégorie",
            width=200,
            height=35,
            fg_color=("gray80", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray75", "gray35"),
            command=lambda s=section_key: self.__add_temp_row(s),
        ).pack(side="left", padx=20)

    def __add_temp_row(self, section: str) -> None:
        """Ajoute une ligne vide seulement si toutes les catégories actuelles sont remplies."""

        # 1. On synchronise d'abord pour vérifier l'état réel des Entry
        self.__update_temp_config_from_ui()

        # 2. Vérification : y a-t-il une catégorie sans nom (clé commençant par "Nouvelle_cat_")
        # ou dont l'utilisateur n'a pas changé le texte ?
        for cat_name in self.temp_config["database"][section]["categories_subcategories"].keys():
            if cat_name.startswith("Nouvelle_cat_"):
                messagebox.showwarning(
                    "Champs vides", "Veuillez nommer la catégorie précédente avant d'en ajouter une nouvelle."
                )
                return

        # 3. Si tout est rempli, on crée la nouvelle clé unique
        unique_key = f"Nouvelle_cat_{len(self.temp_config['database'][section]) + 1}"
        self.temp_config["database"][section]["categories_subcategories"][unique_key] = [""]

        self.__draw_config_form(section)

    def __create_sub_badge(
        self, container: ctk.CTkFrame, value: str, entries_list: list, refresh_callback: callable
    ) -> tuple[ctk.CTkFrame, ctk.CTkEntry]:
        """Crée et configure un widget "badge" éditable pour une sous-catégorie."""

        badge_frame = ctk.CTkFrame(container, fg_color=("gray85", "gray30"), corner_radius=15)

        entry = ctk.CTkEntry(
            badge_frame,
            width=120,
            height=28,
            border_width=0,
            placeholder_text="Sous-catégorie",
            fg_color="transparent",
            font=("Arial", 12),
        )
        if value:
            entry.insert(0, value)

        entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        def delete_this():
            badge_frame.destroy()
            if badge_frame in container.badge_frames:
                container.badge_frames.remove(badge_frame)
            if entry in entries_list:
                entries_list.remove(entry)
            refresh_callback()

        del_btn = ctk.CTkButton(
            badge_frame,
            text="x",
            width=20,
            height=20,
            fg_color="transparent",
            text_color=self.__theme["red"]["fg_color"],
            font=("Arial", 14, "bold"),
            command=delete_this,
        )
        del_btn.pack(side="right", padx=(2, 5))

        return badge_frame, entry

    def __remove_temp_row_by_index(self, section: str, index: int) -> None:
        """Supprime une catégorie en utilisant son index dans le dictionnaire."""

        # 1. On synchronise les dernières saisies
        self.__update_temp_config_from_ui()

        # 2. On récupère la liste des clés actuelles
        keys = list(self.temp_config["database"][section]["categories_subcategories"].keys())

        # S'il n'y a qu'une seule catégorie, on interdit la suppression
        if len(keys) <= 1:
            section_name = "revenus" if section == "incomes" else "dépenses"
            messagebox.showerror(
                "Suppression impossible", f"Vous devez garder au moins une catégorie dans la section {section_name}."
            )
            return

        if index >= len(keys):
            return  # Sécurité si l'index n'existe plus

        cat_to_delete = keys[index]

        # 3. Confirmation avec le nom réel (ou 'cette catégorie' si vide)
        display_name = cat_to_delete if not cat_to_delete.startswith("Nouvelle_cat_") else "cette nouvelle catégorie"

        if not messagebox.askyesno("Confirmation", f"Supprimer {display_name} et ses sous-catégories ?"):
            return

        # 4. Suppression réelle
        del self.temp_config["database"][section]["categories_subcategories"][cat_to_delete]

        # 5. On redessine tout
        self.__draw_config_form(section)

    def __update_temp_config_from_ui(self) -> None:
        """Synchronise sans polluer l'interface avec des noms génériques."""

        for section in ["incomes", "expenses"]:
            updated_section = {}
            for cat_id, (name_widget, sub_widgets) in self.entry_widgets[section]["categories_subcategories"].items():
                raw_name = name_widget.get().strip()

                # On garde "Nouvelle_cat_X" uniquement comme clé INTERNE si le champ est vide
                # Cela permet au bouton supprimer de trouver la bonne clé
                if not raw_name:
                    name = f"Nouvelle_cat_{cat_id}"
                else:
                    name = raw_name

                # Pour les sous-catégories, on ne garde que celles qui ont du texte
                subs = [w.get().strip() for w in sub_widgets if w.get().strip()]

                # Si vraiment vide, on laisse une liste avec un string vide pour l'UI
                updated_section[name] = subs if subs else [""]

            self.temp_config["database"][section]["categories_subcategories"] = updated_section

    def __validate_and_save_all(self) -> None:
        """Récupère toutes les données des Entry, valide et sauvegarde."""

        new_db_config = {"incomes": {}, "expenses": {}}
        errors = []

        for section in ["incomes", "expenses"]:
            for cat_id, (name_widget, sub_widgets_list) in self.entry_widgets[section][
                "categories_subcategories"
            ].items():
                name = name_widget.get().strip()

                if not name:
                    errors.append(f"[{section.upper()}] Une catégorie n'a pas de nom.")
                    continue

                # On récupère les valeurs de tous les petits widgets Entry
                subs = [w.get().strip() for w in sub_widgets_list if w.get().strip()]

                if not subs:
                    errors.append(
                        f"[{section.upper()}] La catégorie '{name}' doit avoir au moins une sous-catégorie valide."
                    )
                    continue

                new_db_config[section][name] = subs

        # Vérification finale des erreurs
        if errors:
            error_msg = "\n".join(errors)
            messagebox.showerror("Erreurs de validation", f"Veuillez corriger les points suivants :\n\n{error_msg}")
            return

        # Si tout est OK, on met à jour la config globale et on sauvegarde
        try:
            full_config = load_config()
            full_config["database"]["incomes"]["categories_subcategories"] = new_db_config["incomes"]
            full_config["database"]["expenses"]["categories_subcategories"] = new_db_config["expenses"]

            save_config(full_config)
            self.__config = load_config()
            self.__db = BnpParibasDatabase(self.__db_path)

            messagebox.showinfo("Succès", "Toutes les catégories ont été mises à jour avec succès !")
            self.__home_page()

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'écriture du fichier : {e}")
            raise

    # -- [ Page d'accueil ] ---
    def __home_page(self) -> None:
        """Affiche la page d'accueil avec un message de bienvenue et des statistiques globales."""

        self.__destroy_widgets()

        # Header
        header_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)

        title_label = ctk.CTkLabel(header_frame, text="Accueil", font=("Arial", 60, "bold"))
        title_label.pack(expand=True)

        # Conteneur principal agrandi
        container = ctk.CTkFrame(self.main_view, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=40)

        actions = [
            {
                "name": "Comptes",
                "desc": "Gérer vos différents\ncomptes.",
                "fg_color": self.__theme["green"]["fg_color"],
                "hover_color": self.__theme["green"]["hover_color"],
                "icon_path": "src/static/img/account.png",
                "cmd": lambda: self.__show_accounts_view(),
            },
            {
                "name": "Bourse",
                "desc": "Suivre vos placements\net investissements.",
                "fg_color": self.__theme["green"]["fg_color"],
                "hover_color": self.__theme["green"]["hover_color"],
                "icon_path": "src/static/img/stock.png",
                "cmd": lambda: self.__home_page(),  # TODO
            },
            {
                "name": "Patrimoine",
                "desc": "Visualisez l'évolution de votre\npatrimoine.",
                "fg_color": self.__theme["green"]["fg_color"],
                "hover_color": self.__theme["green"]["hover_color"],
                "icon_path": "src/static/img/heritage.png",
                "cmd": lambda: self.__home_page(),  # TODO
            },
            {
                "name": "Configuration",
                "desc": "Configurez ici l'ensemble de\nvos préférences et réglages.",
                "fg_color": self.__theme["blue_03"]["fg_color"],
                "hover_color": self.__theme["blue_03"]["hover_color"],
                "icon_path": "src/static/img/edit.png",
                "cmd": lambda: self.__manage_config_view(),
            },
            {
                "name": "Informations",
                "desc": "Consulter l'aide et\nles mentions légales.",
                "fg_color": self.__theme["blue_03"]["fg_color"],
                "hover_color": self.__theme["blue_03"]["hover_color"],
                "icon_path": "src/static/img/information.png",
                "cmd": lambda: self.__home_page(),  # TODO
            },
        ]

        self.__create_card_grid(container, actions)

    def __create_card_grid(self, container: ctk.CTkFrame, items: list) -> None:
        """Crée une grille de cartes (3 max par ligne) parfaitement centrées."""

        # On vide le container au cas où
        for child in container.winfo_children():
            child.destroy()

        # On utilise 6 colonnes pour permettre de centrer 1, 2 ou 3 cartes proprement
        container.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        total = len(items)

        for i, item in enumerate(items):
            row = i // 3
            col_in_row = i % 3

            # On calcule combien d'items il y a sur la ligne actuelle
            remaining = total - (row * 3)
            items_on_this_row = min(3, remaining)

            card = ctk.CTkFrame(container, corner_radius=20, border_width=1)

            # Logique de placement
            if items_on_this_row == 3:
                # On prend 2 colonnes par carte (Total 6)
                card.grid(row=row, column=col_in_row * 2, columnspan=2, padx=15, pady=15, sticky="nsew")

            elif items_on_this_row == 2:
                # On place les cartes sur les colonnes 1-2 et 3-4 (On laisse 0 et 5 vides)
                start_col = 1 if col_in_row == 0 else 3
                card.grid(row=row, column=start_col, columnspan=2, padx=15, pady=15, sticky="nsew")

            elif items_on_this_row == 1:
                # On place la carte sur les colonnes 2-3 (Milieu parfait)
                card.grid(row=row, column=2, columnspan=2, padx=15, pady=15, sticky="nsew")

            img_data = Image.open(item["icon_path"])
            ctk_icon = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(40, 40))

            # Icône
            icon_circle = ctk.CTkLabel(
                card,
                image=ctk_icon,
                text="",
                font=("Arial", 40),
                fg_color=item["fg_color"],
                width=80,
                height=80,
                corner_radius=40,
            )
            icon_circle.pack(pady=(30, 10))

            ctk.CTkLabel(card, text=item["name"], font=("Arial", 20, "bold")).pack()
            ctk.CTkLabel(card, text=item["desc"], text_color="gray").pack(pady=10, padx=20)

            # Spacer invisible pour pousser le bouton en bas et garder la hauteur uniforme
            ctk.CTkLabel(card, text="", height=1).pack(expand=True)

            # Bouton
            ctk.CTkButton(
                card,
                text="Accéder",
                fg_color=item["fg_color"],
                hover_color=item["hover_color"],
                command=item["cmd"],
                corner_radius=10,
                height=35,
                font=("Arial", 15, "bold"),
            ).pack(side="bottom", pady=20, padx=20, fill="x")

    # --- [ Gestion des Comptes Bancaires ] ---
    def __show_accounts_view(self) -> None:
        """Affiche le Dashboard global avec les comptes sous forme de cartes."""

        self.__destroy_widgets()

        # Titre et Résumé Global
        title_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(title_frame, text="Tableau de Bord", font=("Arial", 32, "bold")).pack(side="left")

        ctk.CTkButton(
            title_frame,
            text="+ Ajouter un compte",
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=self.__handle_add_account,
        ).pack(side="right")

        # Grille des comptes
        # On utilise une Frame scrollable pour la grille
        scroll_container = ctk.CTkScrollableFrame(self.main_view, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=20, pady=10)

        # Configuration de la grille (3 colonnes pour que ce soit aéré)
        scroll_container.grid_columnconfigure((0, 1, 2), weight=1, pad=20)

        try:
            account_df = self.__db.get_all_accounts()
            if not account_df.empty:
                for index, row in account_df.iterrows():
                    self.__create_account_card(scroll_container, row, index)
            else:
                ctk.CTkLabel(scroll_container, text="Aucun compte. Cliquez sur 'Ajouter' pour commencer.").grid(
                    row=0, column=0, columnspan=3, pady=50
                )
        except Exception as e:
            raise e

    def __create_account_card(self, master: ctk.CTkScrollableFrame, row: pd.Series, index: int) -> None:
        """Crée une carte stylisée pour un compte bancaire incluant le solde total."""

        # Positionnement de la carte dans la grille principale
        r, c = divmod(index, 3)
        card = ctk.CTkFrame(master, corner_radius=15, height=240, width=280, border_width=2)
        card.grid(row=r, column=c, padx=15, pady=15, sticky="nsew")
        card.grid_propagate(False)

        # Nom du compte
        lbl_name = ctk.CTkLabel(card, text=row["name"], font=("Arial", 20, "bold"))
        lbl_name.pack(pady=(15, 2))

        # Récupération des statistiques
        stats = self.__db.get_account_statistics(row["id"])

        total_amount = stats.get("account_amount", 0.0)

        # Formatage du texte
        formatted_balance = f"{total_amount:,.2f}".replace(",", " ").replace(".", ",") + " €"
        balance_color = self.__theme["green"]["fg_color"] if total_amount >= 0 else self.__theme["red"]["fg_color"]

        lbl_balance = ctk.CTkLabel(card, text=formatted_balance, font=("Arial", 24, "bold"), text_color=balance_color)
        lbl_balance.pack(pady=10)

        # Nombre d'opérations
        lbl_ops = ctk.CTkLabel(
            card,
            text=f"{stats.get('total', 0)} opérations enregistrées",
            text_color="gray",
            font=("Arial", 12, "italic"),
        )
        lbl_ops.pack(pady=(0, 5))

        # Conteneur pour les boutons
        button_container = ctk.CTkFrame(card, fg_color="transparent")
        button_container.pack(side="bottom", padx=10, pady=15)
        button_container.columnconfigure((0, 1, 2), weight=1)

        # Configuration des boutons
        btn_configs = [
            {
                "text": "Ouvrir",
                "fg_color": self.__theme["green"]["fg_color"],
                "hover_color": self.__theme["green"]["hover_color"],
                "cmd": lambda: self.__show_account_hub(row),
            },
            {
                "text": "Éditer",
                "fg_color": self.__theme["blue_01"]["fg_color"],
                "hover_color": self.__theme["blue_01"]["hover_color"],
                "cmd": lambda: self.__handle_edit_account(row["id"], row["name"]),
            },
            {
                "text": "Supprimer",
                "fg_color": self.__theme["red"]["fg_color"],
                "hover_color": self.__theme["red"]["hover_color"],
                "cmd": lambda: self.__handle_delete_account(row["id"], row["name"]),
            },
        ]

        for i, config in enumerate(btn_configs):
            btn = ctk.CTkButton(
                button_container,
                text=config["text"],
                width=75,
                height=28,
                fg_color=config["fg_color"],
                hover_color=config["hover_color"],
                command=config["cmd"],
            )
            btn.grid(row=0, column=i, padx=5)

    def __show_account_hub(self, account_row: pd.Series) -> None:
        """Affiche les différentes actions que l'on peut effectuer sur un compte"""

        self.__destroy_widgets()

        # On crée un frame qui prend toute la largeur
        header_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)

        # Bouton de retour placé en absolu pour ne pas gêner le centrage du label
        back_btn = ctk.CTkButton(
            header_frame,
            text="←",
            fg_color=self.__theme["blue_01"]["fg_color"],
            hover_color=self.__theme["blue_01"]["hover_color"],
            width=40,
            command=self.__show_accounts_view,
        )
        back_btn.place(x=0, y=15)

        title_label = ctk.CTkLabel(header_frame, text=f"{account_row['name']}", font=("Arial", 60, "bold"))
        title_label.pack(expand=True)

        # Conteneur principal
        container = ctk.CTkFrame(self.main_view, fg_color="transparent")
        container.pack(fill="x", pady=200)
        container.grid_columnconfigure((0, 1, 2), weight=1)

        # Configuration des actions
        actions = [
            {
                "name": "Données",
                "desc": "Importer ou modifier\nvos transactions.",
                "fg_color": self.__theme["blue_02"]["fg_color"],
                "hover_color": self.__theme["blue_02"]["hover_color"],
                "icon_path": "src/static/img/directory.png",
                "cmd": lambda: self.__manage_account_content(account_row),
            },
            {
                "name": "Analyses",
                "desc": "Visualiser la santé\nde vos finances.",
                "fg_color": self.__theme["blue_03"]["fg_color"],
                "hover_color": self.__theme["blue_03"]["fg_color"],
                "icon_path": "src/static/img/chart.png",
                "cmd": lambda: self.__visualize_charts_html(account_row),
            },
            {
                "name": "Rapports",
                "desc": "Générer un fichier\nExcel complet.",
                "fg_color": self.__theme["magenta"]["fg_color"],
                "hover_color": self.__theme["magenta"]["hover_color"],
                "icon_path": "src/static/img/file.png",
                "cmd": lambda: self.__visualize_bilan_excel(account_row),
            },
        ]

        self.__create_card_grid(container, actions)

    def __handle_add_account(self) -> None:
        """Ouvre une boîte de dialogue pour créer un nouveau compte bancaire."""

        dialog = ctk.CTkInputDialog(text="Entrez le nom du nouveau compte :", title="Nouveau Compte")
        self.__center_window(dialog)
        dialog.transient(self)
        dialog.attributes("-topmost", False)

        account_name = dialog.get_input()

        if account_name:
            try:
                self.__db.add_account(account_name)
                self.__show_accounts_view()

            except ValueError as e:
                messagebox.showwarning("Doublon", str(e))
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de créer le compte : {e}")
                raise

    def __handle_delete_account(self, account_id: int, account_name: str) -> None:
        """Demande confirmation avant de supprimer un compte et ses données."""

        if messagebox.askyesno(
            "Confirmation",
            f"Supprimer le compte '{account_name}' ?\nCette action est irréversible.",
        ):
            try:
                # Supprime le dossier bilan du compte
                path = os.path.join(self.__config["destination_path"], account_name)
                if os.path.exists(path):
                    shutil.rmtree(path)

                self.__db.delete_account(account_id)
                self.__show_accounts_view()
            except Exception as e:
                messagebox.showerror(
                    "Erreur de suppression", f"Impossible de supprimer le compte ou ses fichiers :\n{str(e)}"
                )
                raise

    def __handle_edit_account(self, account_id: int, old_name: str) -> None:
        """Ouvre un dialogue centré et immobile pour renommer le compte."""

        dialog = ctk.CTkInputDialog(
            text=f"Nouveau nom pour '{old_name}' :",
            title="Renommer",
            button_fg_color=self.__theme["blue_01"]["fg_color"],
            button_hover_color=self.__theme["blue_01"]["hover_color"],
        )
        self.__center_window(dialog)
        dialog.transient(self)
        dialog.attributes("-topmost", False)

        new_name = dialog.get_input()

        if new_name and new_name != old_name:
            try:
                self.__db.update_account_name(account_id, new_name)
                self.__update_bilan(account_id, new_name)
                self.__show_accounts_view()

            except Exception as e:
                messagebox.showerror(f"Erreur lors de la modification du nom du compte : {str(e)}")
                raise

    # --- [ Gestion des Opérations ] ---
    def __manage_account_content(self, account_row: pd.Series, page: int = 1) -> None:
        """Initialise la structure fixe (Header, Actions) et lance le chargement du tableau."""

        self.__destroy_widgets()

        # Header de navigation
        nav_header = ctk.CTkFrame(self.main_view, fg_color="transparent")
        nav_header.pack(fill="x", padx=20, pady=10)

        back_btn = ctk.CTkButton(
            nav_header,
            text="←",
            fg_color=self.__theme["blue_01"]["fg_color"],
            hover_color=self.__theme["blue_01"]["hover_color"],
            width=40,
            command=lambda: self.__show_account_hub(account_row),
        )
        back_btn.place(x=0, y=15)

        ctk.CTkLabel(
            nav_header,
            text="Gestion du compte",
            font=("Arial", 40, "bold"),
        ).pack(pady=(5, 30))

        # Barre d'actions
        account_actions_bar = ctk.CTkFrame(self.main_view, fg_color="transparent")
        account_actions_bar.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            account_actions_bar,
            text="Importer des opérations",
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=lambda: self.__handle_import_process(account_row),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            account_actions_bar,
            text="Ajouter une opération",
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=lambda: self.__handle_add_operation(account_row),
        ).pack(side="left", padx=5)

        operations = self.__db.get_unprocessed_raw_operations(account_row["id"])
        ctk.CTkButton(
            account_actions_bar,
            text="Catégoriser les opérations",
            fg_color=self.__theme["blue_01"]["fg_color"],
            hover_color=self.__theme["blue_01"]["hover_color"],
            state="normal" if operations else "disabled",
            command=lambda: self.__handle_categorization_process(account_row),
        ).pack(side="left", padx=5)

        # Zone d'affichage
        self.table_container_wrapper = ctk.CTkFrame(self.main_view, fg_color="transparent")
        self.table_container_wrapper.pack(fill="both", expand=True, padx=20, pady=10)

        # Premier chargement du tableau
        self.__update_table_content(account_row, page)

    def __update_table_content(self, account_row: pd.Series, page: int) -> None:
        """Rafraîchit uniquement le tableau avec une zone de lignes à hauteur fixe."""

        # Nettoyage du conteneur dynamique
        for widget in self.table_container_wrapper.winfo_children():
            widget.destroy()

        account_id = account_row["id"]
        items_per_page = 21

        try:
            df = self.__db.get_operations_by_account(account_id)

            if not df.empty:
                # Logique de Tri et Pagination
                df = df.sort_values(by="operation_date", ascending=True)
                df["id_view"] = range(1, len(df) + 1)

                # Application du tri dynamique choisi par l'utilisateur
                df = df.sort_values(
                    by=[self.__sort_column, "id_view"],
                    ascending=[self.__sort_ascending, False],
                    key=lambda col: col.map(
                        lambda x: self.__remove_accents(str(x).lower()) if isinstance(x, str) else x
                    ),
                )

                total_ops = len(df)
                total_pages = max(1, (total_ops // items_per_page) + (1 if total_ops % items_per_page > 0 else 0))
                page = max(1, min(page, total_pages))

                start_idx = (page - 1) * items_per_page
                page_data = df.iloc[start_idx : start_idx + items_per_page]

                # Header du Tableau
                header_table = ctk.CTkFrame(self.table_container_wrapper, fg_color="gray80", height=40)
                header_table.pack(fill="x", pady=(0, 5))
                header_table.pack_propagate(False)

                header_table.grid_columnconfigure(0, weight=0)
                header_table.grid_columnconfigure((1, 3, 4, 5), weight=1, uniform="group_trans")
                header_table.grid_columnconfigure(2, weight=3, uniform="group_trans")
                header_table.grid_columnconfigure((6, 7), weight=0, minsize=85)

                columns = ["#", "Date", "Libellé", "Catégorie", "Sous-Catégorie", "Montant", "Actions"]

                # Mapping des noms de colonnes pour le tri
                col_map = {
                    "#": "id_view",
                    "Date": "operation_date",
                    "Libellé": "label",
                    "Catégorie": "category",
                    "Sous-Catégorie": "sub_category",
                    "Montant": "amount",
                }

                for i, col_name in enumerate(columns):
                    padx_val = (25, 60) if i == 0 else 5
                    anchor_val = "w" if i in [1, 2, 3, 4] else "center"

                    # On crée le texte avec la petite flèche de tri
                    display_text = col_name
                    if col_name in col_map:
                        if self.__sort_column == col_map[col_name]:
                            display_text += " ▲" if self.__sort_ascending else " ▼"

                    # On crée un Label
                    lbl = ctk.CTkLabel(
                        header_table,
                        text=display_text,
                        font=("Arial", 14, "bold"),
                        text_color="black",
                        anchor=anchor_val if col_name != "Actions" else "center",
                    )
                    lbl.grid(
                        row=0,
                        column=i,
                        columnspan=2 if col_name == "Actions" else 1,
                        padx=padx_val,
                        pady=5,
                        sticky="nsew",
                    )

                    # On rend le Label cliquable uniquement s'il est dans col_map
                    if col_name in col_map:
                        lbl.configure(cursor="hand2")
                        lbl.bind("<Button-1>", lambda event, c=col_map[col_name]: self.__sort_handler(account_row, c))

                    if col_name == "#":
                        lbl.configure(width=50, anchor="center")

                # Zone dédiée aux lignes
                rows_container = ctk.CTkFrame(self.table_container_wrapper, fg_color="transparent", height=680)
                rows_container.pack(fill="x")
                rows_container.pack_propagate(False)

                for i, (index, operation) in enumerate(page_data.iterrows(), 1):
                    row_bg = "gray95" if i % 2 == 0 else "gray90"
                    row_f = ctk.CTkFrame(rows_container, fg_color=row_bg, height=30)
                    row_f.pack(fill="x", pady=1)

                    row_f.grid_columnconfigure(0, weight=0)
                    row_f.grid_columnconfigure((1, 3, 4, 5), weight=1, uniform="group_trans")
                    row_f.grid_columnconfigure(2, weight=3, uniform="group_trans")
                    row_f.grid_columnconfigure((6, 7), weight=0, minsize=85)

                    ctk.CTkLabel(
                        row_f, text=str(operation["id_view"]), font=("Arial", 11, "italic"), width=50, anchor="center"
                    ).grid(row=0, column=0, padx=(25, 60), sticky="nsew")

                    ctk.CTkLabel(row_f, text=operation["operation_date"], anchor="w").grid(
                        row=0, column=1, padx=5, sticky="nsew"
                    )
                    ctk.CTkLabel(row_f, text=operation["label"], anchor="w").grid(
                        row=0, column=2, padx=(5, 60), sticky="nsew"
                    )
                    ctk.CTkLabel(row_f, text=operation["category"], anchor="w").grid(
                        row=0, column=3, padx=5, sticky="nsew"
                    )
                    ctk.CTkLabel(row_f, text=operation["sub_category"], anchor="w").grid(
                        row=0, column=4, padx=5, sticky="nsew"
                    )

                    amt = operation["amount"]
                    formatted_amt = f"{amt:,.2f}".replace(",", " ") + " €"
                    color = self.__theme["red"]["fg_color"] if amt < 0 else self.__theme["green"]["fg_color"]
                    ctk.CTkLabel(row_f, text=formatted_amt, text_color=color, font=("Arial", 12, "bold")).grid(
                        row=0, column=5, padx=5, sticky="nsew"
                    )

                    ctk.CTkButton(
                        row_f,
                        text="Modifier",
                        width=75,
                        height=22,
                        fg_color=self.__theme["blue_01"]["fg_color"],
                        hover_color=self.__theme["blue_01"]["hover_color"],
                        command=lambda o=operation: self.__handle_edit_operation(o, account_row),
                    ).grid(row=0, column=6, padx=5, pady=5)

                    ctk.CTkButton(
                        row_f,
                        text="Supprimer",
                        width=75,
                        height=22,
                        fg_color=self.__theme["red"]["fg_color"],
                        hover_color=self.__theme["red"]["hover_color"],
                        command=lambda o_id=operation["id"]: self.__handle_delete_operation(account_row, o_id),
                    ).grid(row=0, column=7, padx=5, pady=5)

                # Barre de Pagination
                pagination_container = ctk.CTkFrame(self.table_container_wrapper, fg_color="transparent")
                pagination_container.pack(fill="x", pady=20)

                center_frame = ctk.CTkFrame(pagination_container, fg_color="transparent")
                center_frame.pack(expand=True)

                # Saut de -10 pages
                ctk.CTkButton(
                    center_frame,
                    text=" << ",
                    width=40,
                    state="normal" if page > 1 else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(account_row, max(1, page - 10)),
                ).pack(side="left", padx=5)

                # Précédent
                ctk.CTkButton(
                    center_frame,
                    text=" < ",
                    width=40,
                    state="normal" if page > 1 else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(account_row, page - 1),
                ).pack(side="left", padx=5)

                ctk.CTkLabel(
                    center_frame, text=f"Page {page} / {total_pages}", font=("Arial", 13, "bold"), width=120
                ).pack(side="left", padx=15)

                # Suivant
                ctk.CTkButton(
                    center_frame,
                    text=" > ",
                    width=40,
                    state="normal" if page < total_pages else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(account_row, page + 1),
                ).pack(side="left", padx=5)

                # Saut de +10 pages
                ctk.CTkButton(
                    center_frame,
                    text=" >> ",
                    width=40,
                    state="normal" if page < total_pages else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(account_row, min(total_pages, page + 10)),
                ).pack(side="left", padx=5)

            else:
                ctk.CTkLabel(self.table_container_wrapper, text="Aucune opération enregistrée.").pack(pady=40)

        except Exception as e:
            ctk.CTkLabel(self.table_container_wrapper, text=f"Erreur de chargement : {e}", text_color="red").pack(
                pady=20
            )

    def __sort_handler(self, account_row: pd.Series, column_name: str) -> None:
        """Tri une colonne en particulier dans l'ordre croissant"""

        if self.__sort_column == column_name:
            self.__sort_ascending = not self.__sort_ascending
        else:
            self.__sort_column = column_name
            self.__sort_ascending = True

        self.__update_table_content(account_row, page=1)

    def __handle_add_operation(self, account_row: pd.Series) -> None:
        """Ouvre la fenêtre pour ajouter une nouvelle opération."""

        # On définit les valeurs par défaut pour une nouvelle ligne
        default_op = {
            "id": None,  # None indique à la BDD qu'il s'agit d'une insertion
            "operation_date": datetime.now().strftime("%Y-%m-%d"),
            "label": "",
            "amount": "0.00",
            "category": "",
            "sub_category": "",
        }

        win = OperationEditWindow(
            parent=self.main_view,
            db=self.__db,
            account_id=account_row["id"],
            operation=default_op,
            on_save_callback=lambda data: self.__process_add(data, account_row),
        )
        win.title("Ajouter une opération")

    def __handle_delete_operation(self, account_row: pd.Series, operation_id: int) -> None:
        """Gère la suppression d'une opération et rafraîchit l'affichage."""

        try:
            self.__db.delete_operation(account_row["id"], operation_id)
            self.__update_bilan(account_row["id"], account_row["name"])
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror(f"Erreur lors de la suppression d'une opération' : {str(e)}")
            raise

    def __handle_edit_operation(self, operation: pd.Series, account_row: pd.Series) -> None:
        """Ouvre la fenêtre de modification pour une opération donnée."""

        OperationEditWindow(
            self.main_view,
            self.__db,
            account_row["id"],
            operation,
            lambda data: self.__process_update(data, account_row),
        )

    def __handle_import_process(self, account_row: pd.Series) -> None:
        """Lance l'extraction et injecte le nom du compte sélectionné dans les données."""

        try:
            extractor = DataExtractor()
            df = extractor.run_extraction(account_row["id"])

            if df is None:
                return

            df["account_id"] = account_row["id"]
            self.__db.add_operations(df)

            # Catégorise les différentes opérations
            categorizer = OperationCategorizer(self, self.__db, account_row["id"])
            cat_window = categorizer.categorize()

            if cat_window and cat_window.winfo_exists():
                self.wait_window(cat_window)

            self.__update_bilan(account_row["id"], account_row["name"])

            messagebox.showinfo(
                "Succès",
                f"Données importées avec succès pour le compte : {account_row['name']}",
            )
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'insertion : {e}")
            raise

    def __handle_categorization_process(self, account_row: pd.Series) -> None:
        """Lance le processus de catégorisation."""

        try:
            categorizer = OperationCategorizer(self, self.__db, account_row["id"])
            cat_window = categorizer.categorize()

            if cat_window and cat_window.winfo_exists():
                self.wait_window(cat_window)

            if categorizer.has_changed:
                self.__update_bilan(account_row["id"], account_row["name"])
                self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la catégorisation : {e}")
            raise

    def __process_add(self, new_operation: dict, account_row: pd.Series) -> None:
        """Met à jour la base de données et rafraîchit l'affichage."""

        try:
            df = pd.DataFrame([new_operation])
            self.__db.add_operations(df)
            self.__update_bilan(account_row["id"], account_row["name"])
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {e}")
            raise

    def __process_update(self, updated_data: dict, account_row: pd.Series) -> None:
        """Met à jour la base de données et rafraîchit l'affichage."""

        try:
            self.__db.update_operation(account_row["id"], updated_data)
            self.__update_bilan(account_row["id"], account_row["name"])
            self.__manage_account_content(account_row)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour : {e}")
            raise

    def __update_bilan(self, account_id: int, account_name: str) -> None:
        """Coordonne la mise à jour complète des fichiers bilan pour un compte bancaire."""

        # Supprime le dossier bilan du compte pour que les données soient à jour
        path = os.path.join(self.__config["destination_path"], account_name)
        if os.path.exists(path):
            shutil.rmtree(path)

        # Créer les graphiques HTML
        chart_generator = FinancialChart(self.__db, account_name)
        chart_generator.generate_all_reports(account_id)

        # Créer les fichiers Excel
        excel_generator = BnpParibasExcelReportGenerator(self.__db, account_name)
        excel_generator.generate_all_reports(account_id)

    # --- [ Visualitation des Bilans ] ---
    def __visualize_charts_html(self, account_row: pd.Series) -> None:
        """Affiche les années disponibles sous forme de cartes pour accéder au bilan HTML"""

        self.__destroy_widgets()

        # Configuration du chemin
        bilan_dir = os.path.join(self.__config["destination_path"], account_row["name"])

        # Créer le dossier s'il n'existe pas
        if not os.path.exists(bilan_dir):
            os.makedirs(bilan_dir)

        # Header avec bouton retour
        header_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(10, 60))

        back_btn = ctk.CTkButton(
            header_frame,
            text="←",
            fg_color=self.__theme["blue_03"]["fg_color"],
            hover_color=self.__theme["blue_03"]["hover_color"],
            width=40,
            command=lambda: self.__show_account_hub(account_row),
        )
        back_btn.place(x=0, y=15)

        title_label = ctk.CTkLabel(header_frame, text="Bilans Graphiques", font=("Arial", 60, "bold"))
        title_label.pack(expand=True)

        # Scan des fichiers HTML disponibles
        # On cherche les fichiers qui finissent par .html (ex: Bilan 2026.html, Bilan 2020-2026.html)
        available_years = []
        for file in os.listdir(bilan_dir):
            if file.endswith(".html"):
                # Extraction : "Bilan 2026.html" -> "2026"
                year_name = file.replace("Bilan ", "").replace(".html", "")

                # On construit le chemin relatif vers le fichier
                file_path = os.path.join(bilan_dir, file)
                available_years.append({"year": year_name, "path": file_path})

        # Trier les années par ordre décroissant
        available_years.sort(key=lambda x: (1 if "-" in x["year"] else 0, x["year"]), reverse=True)

        # Conteneur pour les cartes
        scroll_container = ctk.CTkScrollableFrame(self.main_view, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, pady=40, padx=40)

        # On définit une grille de 4 colonnes
        scroll_container.grid_columnconfigure((0, 1, 2, 3), weight=1)

        if not available_years:
            ctk.CTkLabel(scroll_container, text="Aucun bilan généré pour le moment.", font=("Arial", 16)).pack(pady=100)
            return

        download_icon = ctk.CTkImage(light_image=Image.open("src/static/img/download.png"), size=(24, 24))
        calendar_logo = ctk.CTkImage(light_image=Image.open("src/static/img/chart.png"), size=(48, 48))

        # Génération des cartes d'années
        for i, data in enumerate(available_years):
            # Création de la carte
            card = ctk.CTkFrame(scroll_container, corner_radius=15, border_width=1, height=200)
            card.grid(row=i // 4, column=i % 4, padx=15, pady=15, sticky="nsew")
            card.grid_propagate(False)

            download_btn = ctk.CTkButton(
                card,
                text="",
                image=download_icon,
                width=32,
                height=32,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda p=data["path"]: self.__handle_download(p),
            )
            download_btn.place(relx=1.0, x=-10, y=10, anchor="ne")

            # Icône Calendrier
            ctk.CTkLabel(card, text="", image=calendar_logo).pack(pady=(20, 5))

            # Année
            ctk.CTkLabel(card, text=data["year"], font=("Arial", 22, "bold")).pack()

            # Bouton Voir
            ctk.CTkButton(
                card,
                text="Voir le bilan",
                fg_color=self.__theme["blue_03"]["fg_color"],
                hover_color=self.__theme["blue_03"]["hover_color"],
                command=lambda p=data["path"]: self.__open_in_browser(p),
                corner_radius=8,
                height=30,
                font=("Arial", 12, "bold"),
            ).pack(side="bottom", pady=15, padx=15, fill="x")

    def __open_in_browser(self, file_path: str) -> None:
        """Ouvre le fichier HTML dans le navigateur par défaut de l'utilisateur"""

        absolute_path = os.path.abspath(file_path)

        if os.path.exists(absolute_path):
            # Utilisation du module webbrowser pour lancer le navigateur par défaut
            # new=2 ouvre dans un nouvel onglet si possible
            webbrowser.open(f"file://{absolute_path}", new=2)

    def __visualize_bilan_excel(self, account_row: pd.Series) -> None:
        """Affiche les années disponibles sous forme de cartes pour accéder au bilan Excel"""

        self.__destroy_widgets()

        bilan_dir = os.path.join(self.__config["destination_path"], account_row["name"])

        # Créer le dossier s'il n'existe pas
        if not os.path.exists(bilan_dir):
            os.makedirs(bilan_dir)

        # Header avec bouton retour
        header_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(10, 60))

        back_btn = ctk.CTkButton(
            header_frame,
            text="←",
            fg_color=self.__theme["magenta"]["fg_color"],
            hover_color=self.__theme["magenta"]["hover_color"],
            width=40,
            command=lambda: self.__show_account_hub(account_row),
        )
        back_btn.place(x=0, y=15)

        title_label = ctk.CTkLabel(header_frame, text="Bilans Excel", font=("Arial", 60, "bold"))
        title_label.pack(expand=True)

        # Scan des fichiers HTML disponibles
        # On cherche les fichiers qui finissent par .xlsx (ex: Bilan 2026.xlsx, Bilan 2020-2026.xlsx)
        available_years = []
        for file in os.listdir(bilan_dir):
            if file.endswith(".xlsx"):
                # Extraction : "Bilan 2026.xlsx" -> "2026"
                year_name = file.replace("Bilan ", "").replace(".xlsx", "")

                # On construit le chemin relatif vers le fichier
                file_path = os.path.join(bilan_dir, file)
                available_years.append({"year": year_name, "path": file_path})

        # Trier les années par ordre décroissant
        available_years.sort(key=lambda x: (1 if "-" in x["year"] else 0, x["year"]), reverse=True)

        # Conteneur pour les cartes
        scroll_container = ctk.CTkScrollableFrame(self.main_view, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, pady=40, padx=40)

        # On définit une grille de 4 colonnes
        scroll_container.grid_columnconfigure((0, 1, 2, 3), weight=1)

        if not available_years:
            ctk.CTkLabel(scroll_container, text="Aucun bilan généré pour le moment.", font=("Arial", 16)).pack(pady=100)
            return

        download_logo = ctk.CTkImage(light_image=Image.open("src/static/img/download.png"), size=(24, 24))
        excel_logo = ctk.CTkImage(light_image=Image.open("src/static/img/file.png"), size=(48, 48))

        # Génération des cartes d'années
        for i, data in enumerate(available_years):
            # Création de la carte
            card = ctk.CTkFrame(scroll_container, corner_radius=15, border_width=1, height=200)
            card.grid(row=i // 4, column=i % 4, padx=15, pady=15, sticky="nsew")
            card.grid_propagate(False)

            download_btn = ctk.CTkButton(
                card,
                text="",
                image=download_logo,
                width=32,
                height=32,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda p=data["path"]: self.__handle_download(p),
            )
            download_btn.place(relx=1.0, x=-10, y=10, anchor="ne")

            # Icône file
            ctk.CTkLabel(card, text="", image=excel_logo).pack(pady=(20, 5))

            # Année
            ctk.CTkLabel(card, text=data["year"], font=("Arial", 22, "bold")).pack()

            # Bouton Voir
            ctk.CTkButton(
                card,
                text="Ouvrir dans Excel",
                fg_color=self.__theme["magenta"]["fg_color"],
                hover_color=self.__theme["magenta"]["hover_color"],
                command=lambda p=data["path"]: self.__open_xlsx_window(p),
                corner_radius=8,
                height=30,
                font=("Arial", 12, "bold"),
            ).pack(side="bottom", pady=15, padx=15, fill="x")

    def __open_xlsx_window(self, file_path: str) -> None:
        """Ouvre le fichier Excel."""

        if not os.path.exists(file_path):
            messagebox.showerror("Erreur", "Le fichier Excel est introuvable.")
            return

        try:
            subprocess.Popen(["start", "excel", "/r", os.path.abspath(file_path)], shell=True)

        except (OSError, subprocess.SubprocessError):
            try:
                os.startfile(file_path)
            except OSError:
                messagebox.showerror(
                    "Erreur critique", f"Aucun logiciel n'est associé aux fichiers {os.path.splitext(file_path)[1]}"
                )

    def __handle_download(self, file_path: str) -> None:
        """Permet à l'utilisateur de copier le bilan HTML vers un emplacement local."""

        try:
            # Vérifier si le fichier source existe
            if not os.path.exists(file_path):
                messagebox.showerror("Erreur", "Le fichier source est introuvable.")
                return

            # Extraire le nom du fichier par défaut
            default_filename = os.path.basename(file_path)

            # Ouvrir la boîte de dialogue pour choisir la destination
            destination_path = filedialog.asksaveasfilename(
                defaultextension=".html",
                initialfile=default_filename,
                filetypes=[("Fichier HTML", "*.html"), ("Tous les fichiers", "*.*")],
                title="Télécharger le bilan",
            )

            # Si l'utilisateur n'a pas annulé, on copie le fichier
            if destination_path:
                shutil.copy2(file_path, destination_path)
                messagebox.showinfo(
                    "Succès", f"Le bilan a été téléchargé avec succès :\n{os.path.basename(destination_path)}"
                )

        except Exception as e:
            messagebox.showerror("Erreur", f"Échec du téléchargement : {str(e)}")
            raise

    # --- [ Méthodes Annexes ]
    def __center_window(self, window: ctk.CTkInputDialog) -> None:
        """Centre une fenêtre au milieu de l'écran"""

        # Calcul des coordonnées pour centrer par rapport à l'application (self)
        x = self.winfo_x() + (self.winfo_width() // 2) - (window.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (window.winfo_height() // 2)

        window.geometry(f"+{x}+{y}")

    def __destroy_widgets(self) -> None:
        """
        Supprime tous les widgets de la vue principale et force le rafraîchissement
        de l'affichage avant de continuer.
        """

        # Récupération de tous les enfants de la vue principale
        for widget in self.main_view.winfo_children():
            widget.destroy()

        # Force Tkinter à traiter tous les événements de destruction en attente
        # Cela garantit que les widgets sont réellement enlevés de l'écran
        self.main_view.update_idletasks()

    @staticmethod
    def __remove_accents(input_str: str) -> str:
        """Remplace les lettre avec des accents"""

        if not isinstance(input_str, str):
            return input_str

        # Normalise les caractères (ex: 'É' devient 'E')
        nfkd_form = unicodedata.normalize("NFKD", input_str)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
