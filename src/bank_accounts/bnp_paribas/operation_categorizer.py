import re
import tkinter as tk
import unicodedata

from database.bnp_paribas_database import BnpParibasDatabase


class OperationCategorizer(BnpParibasDatabase):
    """
    Fournit une interface graphique pour la catégorisation des opérations financières.

    - Charger les opérations brutes et les catégories/sous-catégories depuis la base.
    - Afficher chaque opération à catégoriser dans une fenêtre.
    - Catégoriser automatiquement certaines opérations selon des règles prédéfinies.
    - Permettre la catégorisation manuelle via des boutons représentant les catégories et sous-catégories.
    - Passer à l’opération suivante sans catégorisation si nécessaire.
    - Enregistrer les opérations catégorisées dans la base et les marquer comme traitées.

    Cette classe combine automatisation et intervention manuelle pour faciliter la classification des transactions financières.
    """

    def __init__(self, db_path: str, buttons_per_row=5):
        """
        Initialise l'interface de catégorisation et charge les données nécessaires.

        Prépare l'état initial de l'application en récupérant la hiérarchie des 
        catégories, les identifiants techniques et la liste des opérations à traiter.

        Args :
        - db_path (str) : Chemin vers la base de données SQLite.
        - buttons_per_row (int) : Nombre de boutons de catégories affichés par ligne.
        """
        super().__init__(db_path)
        
        self.__buttons_per_row = buttons_per_row
        self.__operations = self._get_unprocessed_raw_operations()
        self.__history = []  # Pile pour stocker les opérations précédemment traitées
        
        self.__root = tk.Tk()
        self.__window_width = 800
        self.__window_height = 600
        self.__display_label = tk.Label(self.__root, text="", wraplength=self.__window_width - 50)
        self.__display_label.grid(row=(len(self._categories_labels) // self.__buttons_per_row) + 1, column=0, columnspan=self.__buttons_per_row, pady=20)
    
    
    # --- [ Gestion de l'Interface ] ---
    def categorize(self):
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

        # Filtrage et tri des catégories principales
        if row[5] >= 0:
            filtered_buttons = {"Revenus": self._categories_labels["Revenus"]}
        else:
            # Tri des catégories sans tenir compte des accents
            sorted_keys = sorted(
                [k for k in self._categories_labels.keys() if k != "Revenus"],
                key=self.__normalize_text
            )
            filtered_buttons = {key: self._categories_labels[key] for key in sorted_keys}

        self.__create_buttons(filtered_buttons)

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

        # Calcul de la ligne pour les boutons de navigation (après les catégories)
        navigation_row = (len(filtered_buttons) // self.__buttons_per_row) + 10

        # Bouton "Annuler" (Affiché uniquement si un historique existe)
        if self.__history:
            undo_button = tk.Button(
                self.__root,
                text="Annuler",
                command=self.__undo_last_action,
                bg="#FFCDD2"
            )
            undo_button.grid(row=navigation_row, column=0, pady=10, sticky="ew")

        # Bouton "Suivant"
        skip_button = tk.Button(
            self.__root, 
            text="Suivant", 
            command=self.__skip_entry,
            bg="#CECDFF"
        )
        skip_button.grid(row=navigation_row, column=self.__buttons_per_row - 1, pady=10, sticky="ew")

        # Ajustement automatique des colonnes
        for i in range(self.__buttons_per_row):
            self.__root.grid_columnconfigure(i, weight=1)

    def __button_clicked(self, category_name: str):
        """
        Gère le clic sur une catégorie principale et affiche ses sous-catégories.

        Si la catégorie possède des éléments enfants, l'interface est nettoyée 
        pour afficher les boutons des sous-catégories triés par ordre alphabétique.
        Sinon, l'opération est directement traitée.

        Args:
            - category_name (str) : Le nom de la catégorie sélectionnée par l'utilisateur.
        """
        # Vérification de la validité de la catégorie
        assert category_name in self._categories_labels, f"{category_name} n'est pas une catégorie valide."

        sub_categories = self._categories_labels[category_name]

        # Cas où la catégorie contient des sous-catégories
        if isinstance(sub_categories, list) and sub_categories:
            # Nettoyage des anciens boutons (on conserve uniquement le label d'affichage)
            for widget in self.__root.winfo_children():
                if widget != self.__display_label:
                    widget.destroy()

            # Tri alphabétique insensible aux accents grâce à la méthode de normalisation
            sorted_sub_categories = sorted(sub_categories, key=self.__normalize_text)

            # Création dynamique de la grille de boutons pour les sous-catégories
            for i, sub_label in enumerate(sorted_sub_categories):
                row = i // self.__buttons_per_row
                column = i % self.__buttons_per_row
                
                btn = tk.Button(
                    self.__root,
                    text=sub_label,
                    command=lambda s=sub_label, c=category_name: self.__sub_button_clicked(s, c)
                )
                btn.grid(row=row, column=column, padx=10, pady=10, sticky="ew")

            # Calcul de la position de la ligne de navigation (placée après les boutons)
            row_index = (len(sorted_sub_categories) // self.__buttons_per_row) + 10
            
            # Ajout des boutons de navigation : Retour et Suivant
            back_button = tk.Button(
                self.__root, 
                text="Retour", 
                command=self.__update_display
            )
            back_button.grid(
                row=row_index, 
                column=0, 
                columnspan=self.__buttons_per_row - 2, 
                pady=10, 
                sticky="ew"
            )

            next_button = tk.Button(
                self.__root, 
                text="Suivant", 
                command=self.__skip_entry,
                bg="#CECDFF"
            )
            next_button.grid(
                row=row_index, 
                column=self.__buttons_per_row - 1, 
                pady=10, 
                sticky="ew"
            )
            
        else:
            # Si aucune sous-catégorie n'existe, on traite directement l'opération
            raise ValueError(f"Erreur : Il n'y a pas de sous-catégories pour la catégorie '{category_name}'.")

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

    def __undo_last_action(self):
        """
        Annule la dernière catégorisation effectuée et recharge l'opération.

        Actions :
        - Récupère l'opération de la pile d'historique.
        - Supprime l'entrée correspondante dans la base de données.
        - Réinsère l'opération en début de file d'attente.
        - Rafraîchit l'affichage.
        """
        if not self.__history:
            # Aucun historique disponible, on ne fait rien
            return

        # Récupère la dernière opération traitée (LIFO)
        last_operation = self.__history.pop()
        
        # Suppression en base de données via l'ID de la transaction (row[0])
        # Note : nécessite la méthode _delete_categorized_transaction dans la classe parente
        self._delete_categorized_transaction(last_operation[0])

        # Réinsertion en première position de la liste de travail
        self.__operations.insert(0, last_operation)

        # Mise à jour de l'interface graphique
        self.__update_display()


    # --- [ Logique de Catégorisation ] ---
    def __process_special_cases(self, row: list) -> bool:
        """
		Traite automatiquement certains cas particuliers d'opérations bancaires
		et les catégorise selon des règles prédéfinies.

		Returns:
		- bool : True si l'opération nécessite une catégorisation manuelle (afficher les boutons),
		         False si l'opération a été catégorisée automatiquement (ne pas afficher les boutons).
        """
        amount = row[5]
        short_label = row[2]
        full_label = row[4]

        # --- Revenus ---
        if short_label == "REMISE CHEQUES":
            self._save_categorized_transaction(row, "Revenus", "Chèques reçus")
            return False

        elif bool(re.match(r'^DE AUBRUN PAUL EMIL', full_label)) or bool(re.match(r'^DE MR PAUL AUBRUN', full_label)):
            self._save_categorized_transaction(row, "Revenus", "Virements internes")
            return False

        elif (
            short_label in ["VIREMENT PERMANENT", "VIREMENT INSTANTANE RECU"] or
            full_label == "VIR CPTE A CPTE RECU AUBRUN VIREMENT PAUL" or 
            full_label in ["DE AUBRUN /MOTIF VIREMENT PAUL", "VIREMENT INSTANTANE RECU"]
        ):
            self._save_categorized_transaction(row, "Revenus", "Virements reçus")
            return False

        elif full_label == "REMUNERATION NETTE":
            self._save_categorized_transaction(row, "Revenus", "Intérêts")
            return False

        # --- Abonnement ---
        elif full_label == "COMMISSIONS COTISATION A UNE OFFRE GROUPEE DE SERVICES ESPRIT LIBRE":
            self._save_categorized_transaction(row, "Abonnement", "Assurance Bancaire")
            return False

        # --- Banque ---
        elif bool(re.match(r'^COMMISSIONS COTISATION ANNUELLE VISUEL PERSONNALISE CARTE CARTE N', full_label)):
            self._save_categorized_transaction(row, "Banque", "Frais de carte")
            return False

        # --- Investissement ---
        elif bool(re.match(r'^TRADE REPUBLIC', full_label)) and amount < 0:
            self._save_categorized_transaction(row, "Investissement", "CTO")
            return False

        elif short_label == "VIREMENT INTERNE" and amount < 0:
            self._save_categorized_transaction(row, "Épargne", "Livret A")
            return False

        # --- Transports ---
        elif any(station in full_label for station in ["STATION U"]):
            self._save_categorized_transaction(row, "Transports et véhicules", "Carburant")
            return False

        return True

    def __sub_button_clicked(self, sub_button_name: str, parent_button_name: str):
        """
		Gère le clic sur une sous-catégorie et archive l'opération.

		Args:
		- sub_button_name (str) : nom de la sous-catégorie cliquée
		- parent_button_name (str) : nom de la catégorie parente

		Actions :
		- Enregistre l'opération courante avec la catégorie et sous-catégorie sélectionnées
		- Passe à l'opération suivante dans la liste
        """
        # Archivage de l'opération courante avant traitement
        self.__history.append(self.current_row)

        # Conversion des noms des boutons en IDs techniques
        self._save_categorized_transaction(self.current_row, parent_button_name, sub_button_name)

        # Passage à l'élément suivant
        self.__operations.pop(0)
        self.__update_display()


    # --- [ Utilitaires de Formatage ] ---
    def __normalize_text(self, text: str) -> str:
        """
        Normalise une chaîne de caractères en supprimant les accents et en passant en minuscules.
        
        Utile pour le tri alphabétique correct (ex: 'Épargne' traité comme 'epargne').

        Args:
            - text (str) : La chaîne à normaliser.
        Returns:
            - str : La chaîne normalisée.
        """
        normalized = unicodedata.normalize('NFD', text)
        return "".join(c for c in normalized if unicodedata.category(c) != 'Mn').lower()
