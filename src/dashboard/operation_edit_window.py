from datetime import datetime

import customtkinter as ctk

from dashboard.ctk_date_entry import CtkDateEntry
from database.bnp_paribas_database import BnpParibasDatabase


class OperationEditWindow(ctk.CTkToplevel):
    """
    Fenêtre de modification avec listes déroulantes dynamiques.

    Args:
        parent: Vue parente.
        db: Instance de la base de données pour récupérer les listes.
        operation (dict): Données de l'opération (incluant bank_account_id).
        on_save_callback (callable): Callback de validation.
    """

    def __init__(
        self,
        parent,
        db: BnpParibasDatabase,
        bank_account_id: int,
        operation: dict,
        on_save_callback: callable,
    ):
        super().__init__(parent)
        self.title("Modifier l'opération")
        self.transient(parent)
        self.attributes("-topmost", False)

        self.geometry("450x600")
        width, height = 450, 600
        self.__center_window(width, height)

        self.bank_account_id = bank_account_id
        self.db = db
        self._op = operation
        self._on_save = on_save_callback
        self._entries = {}
        self.categories_data = self.db._get_categories(bank_account_id)

        self.__setup_widgets()
        self.grab_set()

    def __setup_widgets(self):
        """Initialise la fenêtre"""

        # Titre dynamique selon si l'ID existe ou non
        title_text = "Modifier l'opération" if self._op.get("id") else "Nouvelle opération"
        ctk.CTkLabel(self, text=title_text, font=("Arial", 18, "bold")).pack(pady=15)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=25)

        # 1. Date avec calendrier
        ctk.CTkLabel(container, text="Date", anchor="w").pack(fill="x", pady=(10, 0))

        # Instance widget natif
        self.date_picker = CtkDateEntry(container, initial_date=self._op["operation_date"])
        self.date_picker.pack(fill="x", pady=5)

        # 2. Autre champs de textes
        self.__create_field(container, "Libellé", "libelle_operation")
        self.__create_field(container, "Montant", "amount")

        # 3. Liste déroulante des catégories disponibles
        ctk.CTkLabel(container, text="Catégorie", anchor="w").pack(fill="x", pady=(10, 0))
        cat_names = list(self.categories_data.keys())

        # Modif pour la liste des catégories (sécurité si vide)
        cat_names = list(self.categories_data.keys())
        if not cat_names:
            cat_names = ["Aucune catégorie"]
            current_cat = "Aucune catégorie"
        else:
            # On prend la catégorie de l'opération ou la première de la liste
            current_cat = self._op.get("category") or cat_names[0]

        self.cat_menu = ctk.CTkOptionMenu(
            container,
            values=cat_names,
            command=self.__update_subcat_list,  # Déclenche la mise à jour des sous-catégories
        )
        self.cat_menu.set(current_cat)
        self.cat_menu.pack(fill="x", pady=5)

        # 4. Liste déroulante des sous-catégories
        ctk.CTkLabel(container, text="Sous-Catégorie", anchor="w").pack(fill="x", pady=(10, 0))
        self.subcat_menu = ctk.CTkOptionMenu(container, values=[])
        self.subcat_menu.pack(fill="x", pady=5)

        # Initialisation de la sous-catégorie
        self.__update_subcat_list(self._op["category"])

        # On définit la sous-catégorie :
        # Si l'opération en a déjà une, on l'utilise
        # Sinon, on prend la première valeur disponible que __update_subcat_list vient d'injecter
        if self._op.get("sub_category"):
            self.subcat_menu.set(self._op["sub_category"])
        else:
            current_values = self.subcat_menu.cget("values")
            if current_values:
                self.subcat_menu.set(current_values[0])

        # Label pour les messages d'erreur (placé juste avant le bouton)
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#ff4d4d",
            font=("Arial", 12),
        )
        self.error_label.pack(pady=(0, 5))

        ctk.CTkButton(self, text="Enregistrer", fg_color="#28a745", command=self.__handle_save).pack(
            pady=25, padx=25, fill="x"
        )

    def __create_field(self, parent, label, key):
        """Crée un ensemble Label + Entry dans l'interface et l'enregistre pour récupération."""

        ctk.CTkLabel(parent, text=label, anchor="w").pack(fill="x", pady=(10, 0))
        entry = ctk.CTkEntry(parent)
        entry.insert(0, str(self._op[key]))
        entry.pack(fill="x", pady=5)
        self._entries[key] = entry

    def __update_subcat_list(self, selected_category):
        """Met à jour les options du menu sous-catégorie selon la catégorie choisie."""

        new_subcats = self.categories_data.get(selected_category, [])
        self.subcat_menu.configure(values=new_subcats)
        if new_subcats:
            self.subcat_menu.set(new_subcats[0])

    def __handle_save(self):
        """Récupère, valide et transmet les données de l'opération."""

        # 1. Extraction des données brutes
        data = {key: entry.get() for key, entry in self._entries.items()}

        # On récupère la date via notre widget personnalisé
        raw_date = self.date_picker.get()

        data["category"] = self.cat_menu.get()
        data["sub_category"] = self.subcat_menu.get()
        data["id"] = self._op["id"]
        data["bank_account_id"] = self.bank_account_id

        # 2. Validation de la DATE
        # On vérifie si la date est présente et suit le format attendu (YYYY-MM-DD)
        try:
            # datetime.strptime lève une erreur si le format est incorrect
            datetime.strptime(raw_date, "%Y-%m-%d")
            data["operation_date"] = raw_date
        except (ValueError, TypeError):
            self.error_label.configure(text="Erreur : Format de date invalide (AAAA-MM-JJ).")
            return

        # 3. Validation du MONTANT
        amount_str = data["amount"].replace(",", ".")
        try:
            data["amount"] = float(amount_str)
        except ValueError:
            self.error_label.configure(text="Erreur : Le montant doit être un nombre valide.")
            return

        # 4. Validation du LIBELLÉ
        if not data["libelle_operation"].strip():
            self.error_label.configure(text="Erreur : Le libellé ne peut pas être vide.")
            return

        # 5. Finalisation
        self.error_label.configure(text="")
        self._on_save(data)
        self.destroy()

    def __center_window(self, width: int, height: int):
        """Calcule et applique la position centrale sur l'écran."""

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calcul des coordonnées (x, y) pour le centre
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")

        self.geometry(f"{width}x{height}+{x}+{y}")
