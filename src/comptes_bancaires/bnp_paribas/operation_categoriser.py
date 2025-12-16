import tkinter as tk
import re

from database.compte_titre import CompteTireBdd


class OperationCategoriser(CompteTireBdd):
    """
    La classe `OperationCategoriser` fournit une interface graphique Tkinter pour catégoriser des opérations financières 
    issues d'une base de données. Elle permet de :

    - Charger les opérations brutes et les catégories/sous-catégories depuis la base.
    - Afficher chaque opération à catégoriser dans une fenêtre.
    - Catégoriser automatiquement certaines opérations selon des règles prédéfinies.
    - Permettre la catégorisation manuelle via des boutons représentant les catégories et sous-catégories.
    - Passer à l’opération suivante sans catégorisation si nécessaire.
    - Enregistrer les opérations catégorisées dans la base et les marquer comme traitées.

    Cette classe combine automatisation et intervention manuelle pour faciliter la classification des transactions financières.
    
    Arguments du constructeur :
    - db_path (str) : chemin vers la base de données utilisée pour récupérer et stocker les opérations.
    - buttons_per_row (int, optionnel) : nombre de boutons par ligne dans l’interface graphique (par défaut 5).
    """

    def __init__(self, db_path: str, buttons_per_row=5):
        super().__init__(db_path)
        
        self.__buttons_per_row = buttons_per_row
        self.__category = self._get_category()
        self.__operations = self._get_operations_brut()
        self.__category_ids, self.subcategory_ids = self._get_category_ids()
        
        self.__root = tk.Tk()
        self.__window_width = 800
        self.__window_height = 600
        self.__display_label = tk.Label(self.__root, text="", wraplength=self.__window_width - 50)
        self.__display_label.grid(row=(len(self.__category) // self.__buttons_per_row) + 1, column=0, columnspan=self.__buttons_per_row, pady=20)
    
    
    def categoriser(self):
        """
		Lance l'interface graphique pour la catégorisation des opérations.

		Actions :
		- Configure la fenêtre principale
		- Centre la fenêtre à l'écran
		- Affiche la première opération à catégoriser
		- Démarre la boucle principale Tkinter pour gérer les interactions utilisateur
        """
        # Fenêtre principale
        self.__root.title("Catégorisation d'opérations")

        self.__center_window()
        self.__update_display()

        # Démarrer la boucle principale de Tkinter
        self.__root.mainloop()


    def __center_window(self):
        """
		Centre la fenêtre Tkinter sur l'écran en ajustant sa position
		en fonction de la largeur et hauteur de l'écran et de la fenêtre.
        """
        screen_width = self.__root.winfo_screenwidth()
        screen_height = self.__root.winfo_screenheight()

        x = (screen_width // 2) - (self.__window_width // 2)
        y = (screen_height // 2) - (self.__window_height // 2)

        self.__root.geometry(f"{self.__window_width}x{self.__window_height}+{x}+{y}")

    def __update_display(self):
        """
		Met à jour l'affichage de l'interface Tkinter avec l'opération courante.

		- Si aucune opération n'est disponible, ferme la fenêtre.
		- Traite les cas spéciaux automatiquement si applicable.
		- Affiche le texte descriptif de l'opération.
		- Détermine et affiche les boutons des catégories pertinentes selon le montant.
        """
        if not self.__operations:
            self.__root.after(0, self.__root.destroy)
            return

        # Récupère la première opération
        row = self.__operations[0]
        self.current_row = row

        # Traite les cas spéciaux
        afficher_button = self.__process_special_cases(row)

        if not afficher_button:
            # L'opération a déjà été catégorisée automatiquement
            self.__operations.pop(0)
            self.__update_display()
            return

        # Affichage du texte
        self.__display_label.config(
            text=row[4] + "\n\n" + f"{row[1]}   =>   {row[5]}€"
        )

        # Détermine les catégories à afficher
        if row[5] >= 0:
            filtered_buttons = {"Revenus": self.__category["Revenus"]}
        else:
            filtered_buttons = {
                key: self.__category[key]
                for key in sorted(self.__category.keys())
                if key != "Revenus"
            }

        self.__create_buttons(filtered_buttons)

    def __process_special_cases(self, row: list) -> bool:
        """
		Traite automatiquement certains cas particuliers d'opérations bancaires
		et les catégorise selon des règles prédéfinies.

		Returns:
		- bool : True si l'opération nécessite une catégorisation manuelle (afficher les boutons),
		         False si l'opération a été catégorisée automatiquement (ne pas afficher les boutons).
        """
        montant = row[5]
        libelle_court = row[2]
        libelle_operation = row[4]
        
        # Liste des restaurants
        restaurants = ["BURGER KING", "KFC", "MC DO", "O TACOS", "OTACOS", "IZLY SMONEY"]

        # --- Revenus ---
        if libelle_court == "REMISE CHEQUES":
            category = "Revenus"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Chèques reçus"])
            return False

        elif (libelle_operation in ["DE AUBRUN /MOTIF VIREMENT PAUL", "VIREMENT INSTANTANE RECU"]) or (libelle_court == "VIREMENT INSTANTANE RECU"):
            category = "Revenus"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Virements reçus"])
            return False

        elif bool(re.match(r'^DE AUBRUN PAUL EMIL', libelle_operation)) or bool(re.match(r'^DE MR PAUL AUBRUN', libelle_operation)):
            category = "Revenus"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Virements internes"])
            return False

        elif libelle_court == "VIREMENT PERMANENT":
            category = "Revenus"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Virements reçus"])
            return False

        elif libelle_operation == "VIR CPTE A CPTE RECU AUBRUN VIREMENT PAUL":
            category = "Revenus"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Virements reçus"])
            return False

        # --- Banque ---
        elif libelle_court == "COMMISSIONS":
            category = "Banque"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Frais bancaires"])
            return False

        # --- Investissement ---
        elif bool(re.match(r'^TRADE REPUBLIC', libelle_operation)) and montant < 0:
            category = "Investissement"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["CTO"])
            return False

        elif libelle_court == "VIREMENT INTERNE" and montant < 0:
            category = "Épargne"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Livret A"])
            return False

        # --- Loisirs ---
        elif any(rest in libelle_operation for rest in restaurants):
            category = "Loisirs et sorties"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Restaurants - Fast food"])
            return False

        # --- Transports ---
        elif any(station in libelle_operation for station in ["STATION U"]):
            category = "Transports et véhicules"
            self._save_categorized_operation(row, self.__category_ids[category], self.subcategory_ids[category]["Carburant"])
            return False

        return True

    def __create_buttons(self, filtered_buttons: dict):
        """
		Crée dynamiquement des boutons Tkinter pour les catégories et sous-catégories
		filtrées et ajoute un bouton de navigation "Suivant".

		Args:
		- filtered_buttons (dict) : dictionnaire { 'Categorie': ['Sous1', 'Sous2'], ... } 
		  représentant les catégories et sous-catégories à afficher.
        """
        assert isinstance(filtered_buttons, dict), "filtered_buttons doit être un dictionnaire."
        assert all(
            isinstance(label, str)
            and isinstance(sub_labels, list)
            and all(isinstance(sub, str) for sub in sub_labels)
            for label, sub_labels in filtered_buttons.items()
        ), "Les clés doivent être des chaînes et les valeurs des listes de chaînes."

        # Supprimer tous les widgets sauf le label d'affichage
        for widget in self.__root.winfo_children():
            if widget != self.__display_label:
                widget.destroy()

        # Création des boutons
        for i, (label, sub_labels) in enumerate(filtered_buttons.items()):
            row = i // self.__buttons_per_row
            column = i % self.__buttons_per_row

            button = tk.Button(
                self.__root,
                text=label,
                command=lambda l=label: self.__button_clicked(l)
            )
            button.grid(row=row, column=column, padx=10, pady=10, sticky="ew")

        # Bouton "Suivant"
        skip_button = tk.Button(self.__root, text="Suivant", command=self.__skip_entry)
        skip_button.grid(
            row=(len(filtered_buttons) // self.__buttons_per_row) + 10,
            column=self.__buttons_per_row - 1,
            pady=10,
            sticky="ew"
        )

        # Ajustement automatique des colonnes
        for i in range(self.__buttons_per_row):
            self.__root.grid_columnconfigure(i, weight=1)

    def __button_clicked(self, button_name: str):
        """
		Gère le clic sur une catégorie principale.

		Args:
		- button_name (str) : nom de la catégorie cliquée

		Si la catégorie a des sous-catégories :
			- affiche les sous-catégories
			- ajoute un bouton "Retour" pour revenir aux catégories principales
			- ajoute un bouton "Suivant" pour passer à l'opération suivante

		Si la catégorie n'a pas de sous-catégories :
			- catégorise directement l'opération en cours
        """
        assert button_name in self.__category, f"{button_name} n'est pas une catégorie valide."

        sous_cats = self.__category[button_name]

        # Cas : il y a des sous-catégories
        if isinstance(sous_cats, list) and sous_cats:
            # Effacer les anciens boutons (mais garder le label)
            for widget in self.__root.winfo_children():
                if widget != self.__display_label:
                    widget.destroy()

            # Créer les boutons des sous-catégories
            for i, sous_label in enumerate(sous_cats):
                btn = tk.Button(
                    self.__root,
                    text=sous_label,
                    command=lambda s=sous_label, b=button_name: self.__sub_button_clicked(s, b)
                )
                btn.grid(row=i // self.__buttons_per_row,
                        column=i % self.__buttons_per_row,
                        padx=10,
                        pady=10,
                        sticky="ew")

            # Bouton Retour → revient aux catégories principales
            retour_btn = tk.Button(
                self.__root,
                text="Retour",
                command=self.__update_display
            )
            retour_btn.grid(
                row=(len(sous_cats) // self.__buttons_per_row) + 10,
                column=0,
                columnspan=self.__buttons_per_row - 2,
                pady=10,
                sticky="ew"
            )

            # Bouton Suivant → passe à l’opération suivante
            suivant_btn = tk.Button(
                self.__root,
                text="Suivant",
                command=self.__skip_entry
            )
            suivant_btn.grid(
                row=(len(sous_cats) // self.__buttons_per_row) + 10,
                column=self.__buttons_per_row - 1,
                pady=10,
                sticky="ew"
            )

        # Cas : pas de sous-catégories → catégorisation directe
        else:
            self.process_button(button_name)

    def __sub_button_clicked(self, sub_button_name: str, parent_button_name: str):
        """
		Gère le clic sur un bouton de sous-catégorie.

		Args:
		- sub_button_name (str) : nom de la sous-catégorie cliquée
		- parent_button_name (str) : nom de la catégorie parente

		Actions :
		- Enregistre l'opération courante avec la catégorie et sous-catégorie sélectionnées
		- Passe à l'opération suivante dans la liste
        """
        # Sauvegarde
        self._save_categorized_operation(
            self.current_row,
            self.__category_ids[parent_button_name],
            self.subcategory_ids[parent_button_name][sub_button_name]
        )

        # Passe à l'opération suivante
        self.__operations.pop(0)
        self.__update_display()

    def __skip_entry(self):
        """
		Passe à l'opération suivante sans effectuer de catégorisation.

		Actions :
		- Supprime l'opération actuellement affichée de la liste
		- Met à jour l'affichage pour montrer l'opération suivante
        """
        if self.__operations:
            # On enlève la première (celle affichée actuellement)
            self.__operations.pop(0)

        # Mise à jour de l'affichage
        self.__update_display()
