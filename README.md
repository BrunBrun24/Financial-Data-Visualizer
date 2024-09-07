# Projet de Gestion et d'Analyse Financière

Ce projet contient plusieurs classes Python conçues pour faciliter la gestion, l'analyse, et la visualisation des données financières. Les fonctionnalités incluent la génération de rapports Excel, la création de graphiques financiers interactifs, l'extraction et la manipulation de données, ainsi que la catégorisation des opérations financières. Voici une description de chaque classe incluse dans le projet.

## Classes

### 1. `ExcelReportGenerator`

La classe `ExcelReportGenerator` facilite la génération de rapports Excel à partir de données structurées sous forme de dictionnaires. Elle permet de sauvegarder les données dans un fichier Excel, d'ajouter des feuilles avec un formatage personnalisé, et de créer des bilans de revenus et de dépenses en regroupant les transactions par catégories.

**Attributs:**
- `dataDict` (dict): Dictionnaire contenant les données à enregistrer et à analyser.
- `wb` (Workbook): Objet Workbook représentant le fichier Excel généré.
- `outputFile` (str): Chemin du fichier Excel généré.

**Méthodes:**
- `__init__(self, dataDict)`: Initialise l'instance avec les données fournies et démarre le processus de création du fichier Excel.
- `CreateFileExcel(self)`: Crée un fichier Excel.
- `AddInFileExcel(self)`: Formate les feuilles Excel, applique des styles et ouvre le fichier généré.
- `SheetBilan(self)`: Crée des bilans de revenus et de dépenses en les regroupant par sous-catégories.
- `ConvertDates(self)`: Convertit les chaînes de dates au format 'YYYY-MM-DD' en objets `datetime`.
- `InitializeDataFrame(self, columnNames, months)`: Initialise un DataFrame avec des colonnes représentant les mois et des lignes pour les catégories de revenus ou de dépenses.
- `RevenueSubCategories(self, revenues)`: Crée un tableau des revenus par catégories et par mois.
- `ExpenseSubCategories(self, expenses)`: Crée un tableau des dépenses par catégories et par mois.
- `AddDataFrameToSheet(self, df, sheetName, startRow, spacing=5)`: Ajoute un DataFrame dans une feuille Excel avec un formatage personnalisé.

### 2. `GraphiqueFinancier`

La classe `GraphiqueFinancier` est conçue pour générer divers types de graphiques financiers à partir de données de transactions. Elle permet la création de graphiques Sankey, en barres, circulaires, et leur combinaison, en utilisant la bibliothèque Plotly. La classe gère également la sauvegarde des graphiques dans un fichier HTML.

**Attributs:**
- `data` (dict): Dictionnaire contenant les données de transactions.
- `outputFile` (str): Nom du fichier HTML où les graphiques générés seront sauvegardés.
- `filePlotly` (list): Liste des graphiques Plotly générés pour être sauvegardés.
- `dfs` (dict): Dictionnaire de DataFrames pandas créés à partir des données de transactions.
- `dfRevenus` (pd.DataFrame): DataFrame des revenus.
- `dfDepenses` (pd.DataFrame): DataFrame des dépenses.

**Méthodes:**
- `__init__(self, data: dict, outputFile: str)`: Initialise le générateur de graphiques avec les données de transactions et le nom du fichier HTML pour sauvegarder les graphiques.
- `SetData(self, newData: dict)`: Modifie les données de transactions et met à jour les DataFrames en conséquence.
- `SetOutputFile(self, newOutputFile: str)`: Modifie le nom du fichier de sortie pour les graphiques.
- `GraphiqueSankey(self, title: str ="", save=True) -> go.Figure`: Crée un graphique Sankey à partir des données de transactions.
- `GraphiqueBar(self, df: pd.DataFrame, title: str, save=True) -> go.Figure`: Crée un graphique en barres empilées à partir d'un DataFrame.
- `GraphiqueCirculaire(self, df: pd.DataFrame, name: str, save=True) -> go.Figure`: Crée un graphique circulaire à partir d'un DataFrame.
- `CombinerGraphiques(self, fig1: go.Figure, fig2: go.Figure, save=True) -> go.Figure`: Combine deux graphiques de type sunburst dans une seule figure.
- `GraphiqueAutomatique(self, compteCourant: bool)`: Gère la génération automatique des graphiques en fonction du type de compte.
- `LivretA(self)`: Gère la génération des graphiques pour un Livret A.
- `CompteCourantRevenusDepenses(self)`: Gère la génération des graphiques pour un compte courant avec revenus et dépenses.
- `CompteCourantUniquementDepenses(self)`: Gère la génération des graphiques pour un compte courant avec uniquement des dépenses.
- `TitreSankey(self)`: Génère un titre pour le graphique Sankey basé sur les données de revenus et de dépenses.
- `SaveInFile(self)`: Enregistre les graphiques générés dans le fichier HTML spécifié.
- `CreateDirectories(self)`: Vérifie l'existence des dossiers dans le chemin spécifié et les crée si nécessaire.

### 3. `DataExtractor`

La classe `DataExtractor` fournit des outils pour extraire et manipuler des données à partir de fichiers Excel et JSON. Elle permet de sélectionner un fichier via une interface utilisateur, de lire et de convertir les données contenues dans le fichier, ainsi que de nettoyer et transformer ces données pour une utilisation ultérieure.

**Attributs:**
- `initialDir` (str): Répertoire initial pour ouvrir la boîte de dialogue de sélection de fichiers.
- `filePath` (str): Chemin du fichier sélectionné par l'utilisateur.
- `data` (pd.DataFrame ou dict): Contient les données extraites du fichier sélectionné.

**Méthodes:**
- `__init__(self, initialDir="Bilan/Archives")`: Initialise l'extracteur de données avec le répertoire de départ.
- `ExcelDateToDatetime(excelDate)`: Convertit une date au format Excel en objet `datetime`.
- `ExtractExcelData(self, filePath)`: Extrait les données d'un fichier Excel et les formate en `DataFrame`.
- `CleanLine(text, startIndex, endText)`: Nettoie une ligne de texte en supprimant les informations inutiles.
- `LoadDictFromJson(filePath)`: Lit un fichier JSON et le convertit en dictionnaire.
- `OpenFileDialog(self, root)`: Ouvre une boîte de dialogue pour sélectionner un fichier.
- `SelectAndExtractData(self)`: Permet à l'utilisateur de sélectionner un fichier et extrait les données.
- `CenterWindow(window, width, height)`: Centre une fenêtre Tkinter à l'écran selon la largeur et la hauteur spécifiées.

### 4. `SankeyGenerator`

La classe `SankeyGenerator` permet de créer et de visualiser un graphique Sankey à partir de données de transactions financières. Elle prend en charge la préparation des données, le traitement des transactions, et la génération du graphique Sankey en utilisant Plotly.

**Attributs:**
- `dictionnaire` (dict): Dictionnaire contenant les données de transactions regroupées par catégories.
- `title` (str): Titre du graphique Sankey.
- `labels` (list): Liste des labels pour les nœuds du graphique.
- `sources` (list): Liste des indices de départ pour les liens du graphique Sankey.
- `targets` (list): Liste des indices de destination pour les liens du graphique Sankey.
- `values` (list): Liste des valeurs des liens entre les nœuds.
- `labelDict` (dict): Dictionnaire pour mapper les labels aux indices des nœuds.
- `nextIndex` (int): Index suivant disponible pour l'ajout de nouveaux labels.
- `data` (dict): Données nettoyées et reformattées prêtes à être utilisées pour générer le graphique Sankey.
- `figure` (go.Figure): Graphique Sankey généré par Plotly.

**Méthodes:**
- `__init__(self, dictionnaire: dict, title="")`: Initialise le générateur de Sankey avec les données et le titre.
- `CalculateTotals(transactionsList: list)`: Calcule les totaux des montants pour chaque type de transaction.
- `SumAmounts(transactions: dict)`: Calcule les sommes des montants pour chaque catégorie ou type.
- `GetLabelIndex(label: str) -> int`: Obtient l'index du label, en l'ajoutant si nécessaire.
- `ProcessExpenses()`: Traite les transactions lorsque les dépenses sont regroupées par catégories.
- `CleanTransactionsAndGroup() -> dict`: Nettoie les transactions et les regroupe par catégorie.
- `AddTransactions(transactions, cle: str = None, depenses: bool = True)`: Ajoute les transactions au graphique Sankey en fonction de la catégorie et des types.
- `GenerateSankey()`: Génère le graphique Sankey à partir des transactions et des catégories.
- `GetFigure() -> go.Figure`: Renvoie le graphique Sankey généré.

### 5. `CategorizeOperations`

La classe `CategorizeOperations` est conçue pour organiser et catégoriser des transactions financières en utilisant des modèles de correspondance basés sur des mots-clés. Elle permet d'attribuer des catégories spécifiques aux transactions et de gérer les changements dans les catégories.

**Attributs:**
- `operations` (list): Liste des transactions à catégoriser.
- `categorie` (str): Catégorie attribuée aux transactions correspondant aux mots-clés spécifiés.
- `keywords` (list): Liste des mots-clés utilisés pour la catégorisation.
- `motsCles` (dict): Dictionnaire des mots-clés associés aux catégories.
- `categories` (dict): Dictionnaire des catégories actuelles.
- `removedKeys` (list): Liste des mots-clés supprimés des catégories.

**Méthodes:**
- `__init__(self, operations: list)`: Initialise la catégorisation des opérations avec la liste fournie.
- `CategorizeTransaction(transaction: str)`: Catégorise une transaction en fonction des mots-clés définis.
- `RemoveCategory(self, categorie: str)`: Supprime une catégorie et ses mots-clés associés.
- `UpdateCategories(self, nouvellesCategories: dict)`: Met à jour les catégories avec les nouvelles valeurs fournies.
- `AddCategory(self, categorie: str, motsCles: list)`: Ajoute une nouvelle catégorie avec les mots-clés spécifiés.
- `UpdateMotsCles(self, categorie: str, motsCles: list)`: Met à jour les mots-clés associés à une catégorie existante.
- `GetCategories(self) -> dict`: Renvoie les catégories et les mots-clés associés.

## Utilisation

Pour utiliser ces classes dans ton projet, suis les instructions ci-dessous :

1. **Installation des Dépendances:**
   Assure-toi que les bibliothèques nécessaires sont installées. Tu peux les installer avec pip :
   ```bash
   pip install pandas openpyxl plotly
