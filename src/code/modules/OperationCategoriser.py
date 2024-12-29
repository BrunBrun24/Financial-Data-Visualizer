import os
import json
import pandas as pd
import tkinter as tk
import re


class OperationCategoriser:
    """
    La classe `CategorizeOperations` est conçue pour organiser et catégoriser des transactions financières 
    en utilisant une interface graphique Tkinter. Elle permet de charger des données depuis un DataFrame, 
    de configurer des boutons pour différentes catégories et sous-catégories, et de comparer et classer 
    les opérations en fonction des informations existantes dans un fichier JSON.

    Attributs:
        - `categories` (list): Liste des catégories uniques extraites du DataFrame.
        - `buttonLabels` (dict): Dictionnaire des labels des boutons pour chaque catégorie.
        - `cheminFileJson` (str): Chemin vers le fichier JSON contenant les opérations existantes.
        - `buttonsPerRow` (int): Nombre de boutons à afficher sur une seule ligne dans la fenêtre.
    """

    def __init__(self, data, buttonLabels, cheminFileJson, buttonsPerRow=5):
        """
        Initialise les attributs de la classe.

        Args:
            data (DataFrame): DataFrame contenant les données à utiliser.
            buttonLabels (dict): Dictionnaire des labels des boutons pour chaque catégorie.
            cheminFileJson (str): Chemin vers le fichier JSON contenant les opérations existantes.
            buttonsPerRow (int): Nombre de boutons que l'on veut afficher sur une seule ligne dans la fenêtre.
        """
        assert isinstance(data, pd.DataFrame) and not data.empty, f"data doit être un DataFrame de Pandas non vide: {type(data).__name__}"
        assert isinstance(buttonLabels, dict) and all(isinstance(mainCategorie, str) and isinstance(sousCategorie, list) and all(isinstance(item, str) for item in sousCategorie) for mainCategorie, sousCategorie in buttonLabels.items()), "buttonLabels doit être un dictionnaire avec des clés de type 'str' et des valeurs de type 'list[str]'."
        assert isinstance(cheminFileJson, str) and cheminFileJson.endswith(".json"), "Le chemin du fichier JSON doit être une chaîne de caractères se terminant par '.json'."
        assert isinstance(buttonsPerRow, int) and buttonsPerRow > 0, "buttonsPerRow doit être un entier positif."

        data['LIBELLÉ COURT'] = data['LIBELLÉ COURT'].fillna('Interet')
        data['TYPE OPÉRATION'] = data['TYPE OPÉRATION'].fillna('Interet')

        
        self.categories = data["LIBELLÉ COURT"].unique()
        self.buttonLabels = buttonLabels
        self.cheminFileJson = cheminFileJson
        self.buttonsPerRow = buttonsPerRow

        self.tableaux = self.TrierDonnees(data)
        self.results = {label: [] for label in buttonLabels}
        self.history = []
        self.listesTypesOperation = {cat: self.tableaux[cat].to_dict('records') for cat in self.categories}
        self.root = tk.Tk()
        self.windowWidth = 800
        self.windowHeight = 600
        self.index = 0
        self.categoryIndex = 0
        self.displayLabel = tk.Label(self.root, text="", wraplength=self.windowWidth - 50)
        self.displayLabel.grid(row=(len(self.buttonLabels) // self.buttonsPerRow) + 1, column=0, columnspan=self.buttonsPerRow, pady=20)

    @staticmethod
    def TrierDonnees(donnees):
        """
        Trie les données en utilisant les valeurs uniques de la colonne 'LIBELLÉ COURT' comme clés pour des DataFrames distincts.
        
        Args:
            donnees (pd.DataFrame): DataFrame contenant les transactions bancaires avec une colonne 'LIBELLÉ COURT'.
            
        Returns:
            dict: Dictionnaire de DataFrames, où chaque clé est une valeur unique de 'LIBELLÉ COURT'.
        """
        # Vérifications des assertions
        assert isinstance(donnees, pd.DataFrame), f"donnees doit être un DataFrame de Pandas: {type(donnees).__name__}"
        assert 'LIBELLÉ COURT' in donnees.columns, "Le DataFrame doit contenir la colonne 'LIBELLÉ COURT'."

        # Créer un dictionnaire vide pour stocker les DataFrames triés
        tableaux = {}

        # Obtenir les valeurs uniques de 'LIBELLÉ COURT'
        valeursUnique = donnees["LIBELLÉ COURT"].unique()

        # Remplir les tableaux en fonction de la colonne "LIBELLÉ COURT"
        for valeur in valeursUnique:
            tableaux[valeur] = donnees[donnees["LIBELLÉ COURT"] == valeur]
        
        return tableaux

    def CenterWindow(self):
        """
        Centre la fenêtre Tkinter sur l'écran.
        """
        # Vérifications des assertions
        assert isinstance(self.root, tk.Tk), f"self.root doit être une instance de tk.Tk, mais c'est {type(self.root).__name__}."
        assert isinstance(self.windowWidth, int) and self.windowWidth > 0, f"self.width doit être un entier positif, mais c'est {type(self.windowWidth).__name__} avec la valeur {self.windowWidth}."
        assert isinstance(self.windowHeight, int) and self.windowHeight > 0, f"self.height doit être un entier positif, mais c'est {type(self.windowHeight).__name__} avec la valeur {self.windowHeight}."

        screenWidth = self.root.winfo_screenwidth()
        screenHeight = self.root.winfo_screenheight()
        x = (screenWidth // 2) - (self.windowWidth // 2)
        y = (screenHeight // 2) - (self.windowHeight // 2)
        self.root.geometry(f'{self.windowWidth}x{self.windowHeight}+{x}+{y}')
    
    @staticmethod
    def ReorderKeys(item, index):
        """
        Réorganise les éléments du dictionnaire pour que la clé 'Type' soit à la position spécifiée par l'index.
        
        Args:
            item (dict): Dictionnaire dont les clés doivent être réorganisées.
            index (int): Position à laquelle la clé 'Type' doit être placée.
        
        Returns:
            dict: Dictionnaire avec les éléments réorganisés.
        """
        # Vérifications des assertions
        assert isinstance(item, dict), f"item doit être un dictionnaire, mais c'est {type(item).__name__}."
        assert isinstance(index, int) and index >= 0, f"index doit être un entier non négatif, mais c'est {type(index).__name__} avec la valeur {index}."

        keys = list(item.keys())
        
        if 'Type' in keys and keys.index('Type') != index:
            keys.remove('Type')
            keys.insert(index, 'Type')
            return {k: item[k] for k in keys}
        else:
            return item

    def TrierElements(self, dictionnaire):
        """
        Réorganise les éléments du dictionnaire pour que la clé 'Type' soit en deuxième position.

        Args:
            dictionnaire (dict): Dictionnaire à réorganiser, où les valeurs sont des listes de dictionnaires.

        Returns:
            dict: Dictionnaire avec les éléments réorganisés.
        """
        # Vérification que 'dictionnaire' est un dictionnaire
        assert isinstance(dictionnaire, dict), f"dictionnaire doit être un dictionnaire, mais c'est {type(dictionnaire).__name__}."

        for category, items in dictionnaire.items():
            # Vérification que chaque valeur est une liste
            assert isinstance(items, list), f"Les valeurs du dictionnaire doivent être des listes, mais la valeur pour la clé '{category}' est de type {type(items).__name__}."

            for item in items:
                # Vérification que chaque élément dans les listes est un dictionnaire
                assert isinstance(item, dict), f"Les éléments des listes doivent être des dictionnaires, mais un des éléments pour la clé '{category}' est de type {type(item).__name__}."
            
            # Réorganiser les éléments en utilisant la méthode ReorderKeys
            dictionnaire[category] = [self.ReorderKeys(item, 1) for item in items]
        
        return dictionnaire

    def ComparerEtCategoriserOperations(self, operationsActuelles):
        """
        Compare les opérations actuelles avec celles existantes dans le fichier JSON et les catégorise.

        Args:
            operationsActuelles (dict): Dictionnaire des opérations actuelles.

        Returns:
            list or None: Liste contenant la catégorie principale et la sous-catégorie si trouvées, sinon None.
        """
        # Vérifications des types des arguments
        assert isinstance(self.cheminFileJson, str) and self.cheminFileJson.endswith(".json"), \
            f"cheminFileJson doit être une chaîne se terminant par '.json', mais c'est {type(self.cheminFileJson).__name__}."
        assert isinstance(operationsActuelles, dict), \
            f"operationsActuelles doit être un dictionnaire, mais c'est {type(operationsActuelles).__name__}."

        # Vérification de l'existence du fichier JSON
        if os.path.exists(self.cheminFileJson):
            with open(self.cheminFileJson, 'r', encoding="UTF-8") as fichier:
                operationsExistees = json.load(fichier)
        else:
            return None

        # Créer des DataFrames à partir des opérations existantes
        dataframes = []
        for categorie, operations in operationsExistees.items():
            assert isinstance(operations, list), \
                f"Les opérations pour la catégorie '{categorie}' doivent être une liste, mais c'est {type(operations).__name__}."
            if operations:
                df = pd.DataFrame(operations)
                df['Catégorie'] = categorie
                dataframes.append(df)

        if dataframes:
            dfComplet = pd.concat(dataframes, ignore_index=True)
        else:
            return None

        # Convertir les opérations actuelles en DataFrame et les fusionner avec les opérations existantes
        df = pd.DataFrame([operationsActuelles])
        mergedDf = pd.merge(dfComplet, df, how='inner')

        if not mergedDf.empty:
            resultRow = mergedDf.iloc[0]
            return [resultRow['Catégorie'], resultRow['Type']]
        else:
            return None

    def AfficherFenetreAvecBoutons(self):
        """
        Affiche une fenêtre Tkinter avec des boutons pour catégoriser les opérations.
        """
        # Vérifications des types des attributs
        assert isinstance(self.root, tk.Tk), \
            f"self.root doit être une instance de tk.Tk, mais c'est {type(self.root).__name__}."
        assert hasattr(self, 'listesTypesOperation') and isinstance(self.listesTypesOperation, dict), \
            f"self.listesTypesOperation doit être un dictionnaire, mais c'est {type(self.listesTypesOperation).__name__}."
        assert hasattr(self, 'results') and isinstance(self.results, dict), \
            f"self.results doit être un dictionnaire, mais c'est {type(self.results).__name__}."

        # Définir le titre de la fenêtre
        self.root.title("Fenêtre avec Boutons et Affichage de Chaînes")

        # Centrer la fenêtre sur l'écran
        self.CenterWindow()

        # Transformer les dates pour ne garder que l'année, le mois et le jour
        for cat, transactions in self.listesTypesOperation.items():
            for transaction in transactions:
                assert isinstance(transaction, dict), \
                    f"Chaque élément dans self.listesTypesOperation doit être un dictionnaire, mais c'est {type(transaction).__name__}."
                assert "DATE D'OPÉRATION" in transaction and isinstance(transaction["DATE D'OPÉRATION"], pd.Timestamp), \
                    f"Chaque transaction doit avoir une clé 'DATE D'OPÉRATION' avec une valeur de type pd.Timestamp"
                
                transaction["DATE D'OPÉRATION"] = transaction["DATE D'OPÉRATION"].strftime('%Y-%m-%d')

        # Mettre à jour l'affichage
        self.UpdateDisplay()

        # Démarrer la boucle principale de Tkinter
        self.root.mainloop()

        # Retourner les éléments triés
        return self.TrierElements(self.results)

    def UpdateDisplay(self):
        """
        Met à jour l'affichage en fonction des opérations à classer et des boutons à créer.
        """
        # On vérifie si toutes les catégories ont été traitées
        if self.categoryIndex < len(self.categories):
            # Il reste des éléments à classer pour la catégorie courante

            # On récupère la catégorie courante et la liste des opérations à classer
            currentCategory = self.categories[self.categoryIndex]
            currentList = self.listesTypesOperation[currentCategory]

            # On vérifie si l'on a encore des opérations à traiter dans la liste courante
            if self.index < len(currentList):
                currentItem = currentList[self.index]

                # On récupère la catégorie principale et la sous-catégorie si elles existent
                operationsCategorisees = self.ComparerEtCategoriserOperations(currentItem)

                if operationsCategorisees is not None:
                    # Les opérations ont été catégorisées, on récupère les catégories
                    mainCategory = operationsCategorisees[0]
                    sousCategory = operationsCategorisees[1]

                    # On vérifie si les catégories existent dans les labels des boutons
                    if mainCategory in self.buttonLabels and sousCategory in self.buttonLabels[mainCategory]:
                        # On ajoute l'opération classée à la liste des résultats
                        currentItem['Type'] = sousCategory
                        if mainCategory not in self.results:
                            self.results[mainCategory] = []
                        self.results[mainCategory].append(currentItem)

                        # On ajoute l'opération à l'historique
                        self.history.append((self.index, self.categoryIndex, currentItem, mainCategory))
                    else:
                        # Si la catégorie ou la sous-catégorie n'existe pas, on lève une exception
                        raise ValueError(f"La catégorie {mainCategory} ou la sous-catégorie {sousCategory} n'existe pas.")
                    
                    # On passe à l'élément suivant dans la liste
                    self.index += 1

                    # Si tous les éléments de la liste ont été traités, on passe à la catégorie suivante
                    if self.index >= len(currentList):
                        self.index = 0
                        self.categoryIndex += 1

                    # On met à jour l'affichage avec les prochains éléments
                    self.UpdateDisplay()
                    return
                else:
                    # Si les opérations ne sont pas catégorisées, on traite les cas spéciaux
                    afficherButton = self.ProcessSpecialCases(currentItem, currentList)

                    if afficherButton:
                        # On affiche les détails de l'opération courante dans l'étiquette
                        self.displayLabel.config(text=currentItem["LIBELLÉ OPÉRATION"] + "\n\n" + str(currentItem["MONTANT"]) + "€")

                        # On filtre les boutons en fonction du montant de l'opération (revenus ou dépenses)
                        if currentItem["MONTANT"] >= 0:
                            filteredButtons = {"Revenus": self.buttonLabels["Revenus"]}
                        else:
                            filteredButtons = {key: value for key, value in self.buttonLabels.items() if key != "Revenus"}
                        
                        # On crée les boutons à afficher selon les filtres appliqués
                        self.CreateButtons(filteredButtons)
            else:
                # Si tous les éléments de la liste courante ont été traités, on passe à la catégorie suivante
                self.index = 0
                self.categoryIndex += 1
                self.UpdateDisplay()
        else:
            # Si toutes les catégories ont été traitées, on affiche un message de fin et on ferme la fenêtre
            self.displayLabel.config(text="Toutes les chaînes ont été affichées")
            self.root.destroy()

    def CreateButtons(self, filteredButtons):
        """
        Crée des boutons dans la fenêtre Tkinter pour les catégories ou sous-catégories filtrées et ajoute les boutons de navigation.

        Args:
            filteredButtons (dict): Dictionnaire où les clés sont des labels de boutons et les valeurs sont les sous-catégories associées.
        """
        assert isinstance(filteredButtons, dict), "filteredButtons doit être un dictionnaire."
        assert all(isinstance(label, str) and isinstance(sub_labels, list) and all(isinstance(sub_label, str) for sub_label in sub_labels) for label, sub_labels in filteredButtons.items()), "Chaque clé de filteredButtons doit être une chaîne de caractères et chaque valeur doit être une liste de chaînes de caractères."

        # Supprimer tous les widgets autres que le label d'affichage
        for widget in self.root.winfo_children():
            if widget != self.displayLabel:
                widget.destroy()

        # Créer et positionner les boutons pour chaque catégorie ou sous-catégorie
        for i, (label, sub_labels) in enumerate(filteredButtons.items()):
            # Calculer la position de la grille pour le bouton
            row = i // self.buttonsPerRow
            column = i % self.buttonsPerRow
            
            # Créer un bouton avec une commande lambda pour appeler ButtonClicked avec le label approprié
            button = tk.Button(self.root, text=label, command=lambda l=label: self.ButtonClicked(l))
            # Placer le bouton dans la grille
            button.grid(row=row, column=column, padx=10, pady=10, sticky='ew')

        # Ajouter un bouton "Retour" pour revenir à la catégorie précédente
        back_button = tk.Button(self.root, text="Retour", command=self.GoBack)
        # Placer le bouton "Retour" dans la grille sous les autres boutons
        back_button.grid(row=(len(filteredButtons) // self.buttonsPerRow) + 10, column=0, pady=10, sticky='ew')
        
        # Ajouter un bouton "Suivant" pour passer à la prochaine entrée
        skip_button = tk.Button(self.root, text="Suivant", command=self.SkipEntry)
        # Placer le bouton "Suivant" dans la grille à la fin de la ligne des boutons
        skip_button.grid(row=(len(filteredButtons) // self.buttonsPerRow) + 10, column=self.buttonsPerRow-1, pady=10, sticky='ew')

        # Configurer les colonnes de la grille pour s'ajuster automatiquement
        for i in range(self.buttonsPerRow):
            self.root.grid_columnconfigure(i, weight=1)

    def ButtonClicked(self, buttonName):
        """
        Gère le clic sur un bouton représentant une catégorie principale.

        Si la catégorie sélectionnée possède des sous-catégories, cette fonction
        supprime les boutons actuels (à l'exception de self.displayLabel) et crée
        des boutons pour chaque sous-catégorie. Elle ajoute également des boutons
        "Retour" pour revenir à la vue des catégories principales et "Suivant" pour
        passer à l'entrée suivante.

        Si la catégorie ne possède pas de sous-catégories, elle traite l'opération
        en appelant la méthode `ProcessButton`.

        Args:
            buttonName (str): Le nom de la catégorie principale dont le bouton a été cliqué.
        """
        # Vérifie que buttonName est une clé valide dans buttonLabels
        assert buttonName in self.buttonLabels, f"'{buttonName}' n'est pas une catégorie valide."
        # Vérifie que la valeur associée à buttonName est une liste et non vide
        assert isinstance(self.buttonLabels[buttonName], list), \
            f"La valeur associée à '{buttonName}' dans buttonLabels doit être une liste, mais c'est {type(self.buttonLabels[buttonName]).__name__}."
        assert self.buttonLabels[buttonName], f"La liste des sous-catégories pour '{buttonName}' est vide."


        # Vérifiez si la catégorie principale possède des sous-catégories
        if isinstance(self.buttonLabels[buttonName], list) and self.buttonLabels[buttonName]:
            # Détruire tous les widgets (sauf self.displayLabel) pour faire place aux sous-catégories
            for widget in self.root.winfo_children():
                if widget != self.displayLabel:
                    widget.destroy()

            # Créer des boutons pour chaque sous-catégorie
            for i, sub_label in enumerate(self.buttonLabels[buttonName]):
                button = tk.Button(self.root, text=sub_label, command=lambda l=sub_label: self.SubButtonClicked(l, buttonName))
                button.grid(row=i // self.buttonsPerRow, column=i % self.buttonsPerRow, padx=10, pady=10, sticky='ew')

            # Ajouter le bouton "Retour" pour revenir à la vue des catégories principales
            return_button = tk.Button(self.root, text="Retour", command=self.UpdateDisplay)
            return_button.grid(row=(len(self.buttonLabels[buttonName]) // self.buttonsPerRow) + 10, column=0, columnspan=self.buttonsPerRow-2, pady=10, sticky='ew')
            
            # Ajouter le bouton "Suivant" pour passer à l'entrée suivante
            skip_button = tk.Button(self.root, text="Suivant", command=self.SkipEntry)
            skip_button.grid(row=(len(self.buttonLabels[buttonName]) // self.buttonsPerRow) + 10, column=self.buttonsPerRow-1, pady=10, sticky='ew')
        else:
            # Si pas de sous-catégories, traiter l'opération
            self.ProcessButton(buttonName)

    def SubButtonClicked(self, sub_button_name, parent_button_name):
        """
        Gère le clic sur un bouton de sous-catégorie.

        Lorsque l'utilisateur clique sur un bouton de sous-catégorie, cette fonction
        appelle `ProcessSubButton` pour traiter la sous-catégorie et la catégorie
        principale associée. Ensuite, elle met à jour l'affichage après un court délai
        pour permettre à l'interface utilisateur de se rafraîchir correctement.

        Args:
            sub_button_name (str): Le nom de la sous-catégorie dont le bouton a été cliqué.
            parent_button_name (str): Le nom de la catégorie principale à laquelle appartient la sous-catégorie.
        """
        # Vérifie que sub_button_name et parent_button_name sont des chaînes de caractères
        assert isinstance(sub_button_name, str), f"sub_button_name doit être une chaîne de caractères, mais c'est {type(sub_button_name).__name__}."
        assert isinstance(parent_button_name, str), f"parent_button_name doit être une chaîne de caractères, mais c'est {type(parent_button_name).__name__}."

        # Traite la sous-catégorie et la catégorie principale associée
        self.ProcessSubButton(sub_button_name, parent_button_name)

        # Met à jour l'affichage après un délai de 100 millisecondes
        self.root.after(100, self.UpdateDisplay)

    def GoBack(self):
        """
        Permet de revenir à l'état précédent en se basant sur l'historique des actions.
        
        Cette fonction restaure l'état précédent en utilisant l'historique des actions effectuées.
        Elle récupère le dernier état enregistré dans l'historique, met à jour l'affichage en conséquence,
        et retire l'entrée correspondante des résultats.
        """
        # Vérifie que l'historique est une liste
        assert isinstance(self.history, list), f"self.history doit être une liste, mais c'est {type(self.history).__name__}."

        if self.history:
            # Récupère le dernier état de l'historique
            self.index, self.categoryIndex, current_row, button_name = self.history.pop()

            # Vérifie que button_name est bien une clé dans self.results
            assert button_name in self.results, f"Le nom du bouton {button_name} n'existe pas dans self.results."
            # Vérifie que current_row est bien dans la liste associée à button_name dans self.results
            assert current_row in self.results[button_name], f"current_row n'existe pas dans self.results[{button_name}]."

            # Retire l'entrée correspondante des résultats
            self.results[button_name].remove(current_row)

            # Met à jour l'affichage
            self.UpdateDisplay()

    def SkipEntry(self):
        """
        Passe à l'entrée suivante dans la liste des opérations à catégoriser.

        Cette fonction incrémente l'index de l'entrée actuelle. Si l'index dépasse le nombre d'entrées dans la
        liste de la catégorie actuelle, il est réinitialisé à zéro et l'index de la catégorie est incrémenté.
        L'affichage est ensuite mis à jour pour refléter la nouvelle entrée.
        """
        # Vérifie que self.index et self.categoryIndex sont des entiers
        assert isinstance(self.index, int) and self.index >= 0, f"self.index doit être un entier positif ou zéro, mais c'est {type(self.index).__name__}."
        assert isinstance(self.categoryIndex, int) and self.categoryIndex >= 0, f"self.categoryIndex doit être un entier positif ou zéro, mais c'est {type(self.categoryIndex).__name__}."

        # Vérifie que self.listesTypesOperation et self.categories sont des listes et que la catégorie actuelle existe
        assert isinstance(self.listesTypesOperation, dict), f"self.listesTypesOperation doit être un dictionnaire, mais c'est {type(self.listesTypesOperation).__name__}."
        assert self.categoryIndex < len(self.categories), f"self.categoryIndex {self.categoryIndex} est hors des limites de self.categories."

        # Passe à l'entrée suivante
        self.index += 1
        
        # Vérifie si l'index dépasse la longueur de la liste actuelle
        if self.index >= len(self.listesTypesOperation[self.categories[self.categoryIndex]]):
            # Réinitialise l'index à zéro et passe à la catégorie suivante
            self.index = 0
            self.categoryIndex += 1
            
            # Vérifie que la nouvelle catégorie existe
            if self.categoryIndex >= len(self.categories):
                self.categoryIndex = len(self.categories) - 1
                self.index = len(self.listesTypesOperation[self.categories[self.categoryIndex]]) - 1

        # Met à jour l'affichage pour la nouvelle entrée
        self.UpdateDisplay()

    def ProcessButton(self, buttonName):
        """
        Traite le clic sur un bouton représentant une catégorie ou une sous-catégorie en attribuant l'entrée courante 
        à cette catégorie et en mettant à jour l'historique et l'affichage.

        Args:
            buttonName (str): Nom de la catégorie ou sous-catégorie sélectionnée par l'utilisateur.

        Raises:
            AssertionError: Si les indices ou les structures de données ne sont pas dans des plages valides.
        """
        # Vérifie que buttonName est une chaîne de caractères
        assert isinstance(buttonName, str), f"buttonName doit être une chaîne de caractères, mais c'est {type(buttonName).__name__}."

        # Vérifie que self.categoryIndex est dans les limites de la liste des catégories
        assert isinstance(self.categoryIndex, int) and 0 <= self.categoryIndex < len(self.categories), \
            f"self.categoryIndex doit être un entier dans les limites de la liste des catégories, mais c'est {self.categoryIndex}."

        # Vérifie que self.index est un entier valide pour la liste actuelle
        current_category = self.categories[self.categoryIndex]
        assert isinstance(self.index, int) and 0 <= self.index < len(self.listesTypesOperation.get(current_category, [])), \
            f"self.index doit être un entier dans les limites de la liste pour la catégorie {current_category}, mais c'est {self.index}."

        current_list = self.listesTypesOperation[current_category]
        
        if self.index < len(current_list):
            current_row = current_list[self.index]
            
            # Vérifie que self.results est un dictionnaire
            assert isinstance(self.results, dict), f"self.results doit être un dictionnaire, mais c'est {type(self.results).__name__}."
            
            # Ajoute la ligne courante à la catégorie sélectionnée dans les résultats
            if buttonName not in self.results:
                self.results[buttonName] = []
            self.results[buttonName].append(current_row)
            
            # Ajoute l'entrée à l'historique
            self.history.append((self.index, self.categoryIndex, current_row, buttonName))
            
            # Passe à l'entrée suivante
            self.index += 1
            if self.index >= len(current_list):
                self.index = 0
                self.categoryIndex += 1
                
                # Assure que categoryIndex reste dans les limites
                if self.categoryIndex >= len(self.categories):
                    self.categoryIndex = len(self.categories) - 1

        # Met à jour l'affichage avec la nouvelle entrée
        self.UpdateDisplay()

    def ProcessSubButton(self, sub_button_name, parent_button_name):
        """
        Traite le clic sur un bouton de sous-catégorie en attribuant l'entrée courante à cette sous-catégorie 
        et en mettant à jour l'historique et l'affichage.

        Args:
            sub_button_name (str): Nom de la sous-catégorie sélectionnée par l'utilisateur.
            parent_button_name (str): Nom de la catégorie principale associée à la sous-catégorie sélectionnée.

        Raises:
            AssertionError: Si les indices ou les structures de données ne sont pas dans des plages valides.
        """
        # Vérifie que sub_button_name et parent_button_name sont des chaînes de caractères
        assert isinstance(sub_button_name, str), f"sub_button_name doit être une chaîne de caractères, mais c'est {type(sub_button_name).__name__}."
        assert isinstance(parent_button_name, str), f"parent_button_name doit être une chaîne de caractères, mais c'est {type(parent_button_name).__name__}."

        # Vérifie que self.categoryIndex est dans les limites de la liste des catégories
        assert isinstance(self.categoryIndex, int) and 0 <= self.categoryIndex < len(self.categories), \
            f"self.categoryIndex doit être un entier dans les limites de la liste des catégories, mais c'est {self.categoryIndex}."

        # Vérifie que self.index est un entier valide pour la liste actuelle
        current_category = self.categories[self.categoryIndex]
        assert isinstance(self.index, int) and 0 <= self.index < len(self.listesTypesOperation.get(current_category, [])), \
            f"self.index doit être un entier dans les limites de la liste pour la catégorie {current_category}, mais c'est {self.index}."

        current_list = self.listesTypesOperation[current_category]
        
        if self.index < len(current_list):
            current_row = current_list[self.index]
            
            # Vérifie que self.results est un dictionnaire
            assert isinstance(self.results, dict), f"self.results doit être un dictionnaire, mais c'est {type(self.results).__name__}."
            
            # Assure que parent_button_name est bien une clé dans self.results
            if parent_button_name not in self.results:
                self.results[parent_button_name] = []
            
            # Attribue la sous-catégorie à l'entrée courante
            current_row['Type'] = sub_button_name
            
            # Ajoute la ligne courante aux résultats
            self.results[parent_button_name].append(current_row)
            
            # Ajoute l'entrée à l'historique
            self.history.append((self.index, self.categoryIndex, current_row, parent_button_name))
            
            # Passe à l'entrée suivante
            self.index += 1
            if self.index >= len(current_list):
                self.index = 0
                self.categoryIndex += 1

        # Met à jour l'affichage avec la nouvelle entrée
        self.UpdateDisplay()


    def ProcessSpecialCases(self, currentItem, currentList):
        """
        Traite les cas spéciaux pour les opérations et les catégorise en conséquence.

        Args:
            currentItem (dict): Dictionnaire contenant les informations sur l'opération à traiter. Doit contenir les clés suivantes :
                - 'MONTANT' : montant de l'opération (float ou int)
                - 'LIBELLÉ COURT' : libellé court de l'opération (str)
                - 'LIBELLÉ OPÉRATION' : libellé complet de l'opération (str)

        Returns:
            True: Si aucune catégorisation n'a été faite, on renvoie True pour afficher les boutons
            False: Si une catégorisation a été faite, on renvoie False pour ne pas afficher les boutons
        """
        # Vérifie que currentItem est un dictionnaire et contient les clés nécessaires
        assert isinstance(currentItem, dict), f"currentItem doit être un dictionnaire, mais c'est {type(currentItem).__name__}."
        assert 'MONTANT' in currentItem and isinstance(currentItem['MONTANT'], (int, float)), \
            f"currentItem doit contenir une clé 'MONTANT' avec une valeur de type int ou float, mais c'est {type(currentItem.get('MONTANT', 'clé manquante'))}."
        assert 'LIBELLÉ COURT' in currentItem and isinstance(currentItem['LIBELLÉ COURT'], str), \
            f"currentItem doit contenir une clé 'LIBELLÉ COURT' avec une valeur de type str, mais c'est {type(currentItem.get('LIBELLÉ COURT', 'clé manquante'))}."
        assert 'LIBELLÉ OPÉRATION' in currentItem and isinstance(currentItem['LIBELLÉ OPÉRATION'], str), \
            f"currentItem doit contenir une clé 'LIBELLÉ OPÉRATION' avec une valeur de type str, mais c'est {type(currentItem.get('LIBELLÉ OPÉRATION', 'clé manquante'))}."

        montant = currentItem["MONTANT"]
        libelleCourt = currentItem["LIBELLÉ COURT"]
        libelleOperation = currentItem["LIBELLÉ OPÉRATION"]

        # Liste des restaurants spécifiques pour la catégorisation
        restaurant = ["BURGER KING", "KFC", "MC DO", "O TACOS", "OTACOS"]

        # On regarde s'il n'y a pas d'indices pour classer automatiquement les transactions dans leur catégories

        # Pour la catégorie "Revenus"
        if libelleCourt == "REMISE CHEQUES":
            self.PutInCategorie(currentItem, currentList, "Revenus", "Chèque reçu")
            return False
        elif libelleOperation in ["DE AUBRUN /MOTIF VIREMENT PAUL", "VIREMENT INSTANTANE RECU"]:
            self.PutInCategorie(currentItem, currentList, "Revenus", "Virement reçu")
            return False
        elif bool(re.match(r'^DE AUBRUN PAUL EMIL', libelleOperation)) or bool(re.match(r'^DE MR PAUL AUBRUN', libelleOperation)):
            self.PutInCategorie(currentItem, currentList, "Revenus", "Virement interne")
            return False
        elif libelleCourt == "VIREMENT PERMANENT":
            self.PutInCategorie(currentItem, currentList, "Revenus", "Virement reçu")
            return False
        elif libelleOperation == "VIR CPTE A CPTE RECU AUBRUN VIREMENT PAUL":
            self.PutInCategorie(currentItem, currentList, "Revenus", "Virement reçu")
            return False

        # Pour la catégorie "Banque"
        elif libelleCourt == "COMMISSIONS":
            self.PutInCategorie(currentItem, currentList, "Banque", "Frais bancaires")
            return False

        # Pour la catégorie "Investissement"
        elif bool(re.match(r'^TRADE REPUBLIC', libelleOperation)) and montant < 0:
            self.PutInCategorie(currentItem, currentList, "Investissement", "CTO")
            return False
        elif libelleCourt == "VIREMENT INTERNE" and montant < 0:
            self.PutInCategorie(currentItem, currentList, "Investissement", "Livret A")
            return False

        # Pour la catégorie "Loisir et sorties"
        elif any(restaurantItem in libelleOperation for restaurantItem in restaurant):
            self.PutInCategorie(currentItem, currentList, "Loisir et sorties", "Restaurants - Bars")
            return False

        # Pour la catégorie "Transports et véhicules"
        elif any(stationCarburant in libelleOperation for stationCarburant in ["DAC", "STATION U"]):
            self.PutInCategorie(currentItem, currentList, "Transports et véhicules", "Carburant")
            return False

        # Pour la catégorie "Vie quotidienne"
        elif libelleOperation == "IZLY SMONEY":
            self.PutInCategorie(currentItem, currentList, "Vie quotidienne", "Alimentation - Supermarché")
            return False
        
        return True

    def PutInCategorie(self, currentItem, currentList, mainCategorie, secondCategorie):
        if mainCategorie in self.buttonLabels and secondCategorie in self.buttonLabels[mainCategorie]:
            currentItem['Type'] = secondCategorie
            if mainCategorie not in self.results:
                self.results[mainCategorie] = []
            self.results[mainCategorie].append(currentItem)
            self.history.append((self.index, self.categoryIndex, currentItem, mainCategorie))
        else:
            print(f"La catégorie {mainCategorie} ou la sous-catégorie {secondCategorie} n'existe pas.")
        
        # Passer à l'entrée suivante
        self.index += 1
        if self.index >= len(currentList):
            self.index = 0
            self.categoryIndex += 1
        self.UpdateDisplay()

