import re
import plotly.graph_objects as go


class SankeyGenerator:
    """
    La classe `SankeyGenerator` permet de créer et de visualiser un graphique Sankey à partir de données de transactions financières.
    Elle prend en charge la préparation des données, le traitement des transactions, et la génération du graphique Sankey en utilisant Plotly.

    Attributs:
        - `dictionnaire` (dict): Dictionnaire contenant les données de transactions regroupées par catégories.
        - `title` (str): Titre du graphique Sankey.
    """
    
    def __init__(self, dictionnaire: dict, title=""):
        """
        Initialise le générateur de Sankey avec les données et le titre.
        """
        assert isinstance(dictionnaire, dict), "Les données doivent être un dictionnaire"
        assert isinstance(title, str), "Le titre doit être une chaîne de caractères"

        self.dictionnaire = dictionnaire
        self.title = title
        self.labels = []
        self.sources = []
        self.targets = []
        self.values = []
        self.labelDict = {}
        self.nextIndex = 0

        # Nettoyer et reformater les données
        self.data = self.CleanTransactionsAndGroup()

        # Traiter les transactions et générer le graphique Sankey
        self.GenerateSankey()

    @staticmethod
    def CalculateTotals(transactionsList: list) -> dict:
        """
        Calcule les totaux des montants pour chaque type de transaction.
        """
        assert isinstance(transactionsList, list), "transactionsList doit être une liste"
        
        totals = {}
        for transaction in transactionsList:
            typeOp = transaction['Type']
            montant = round(abs(transaction['MONTANT']), 2)
            if typeOp in totals:
                totals[typeOp] += montant
            else:
                totals[typeOp] = montant
        return totals

    def SumAmounts(self, transactions: dict) -> dict:
        """
        Calcule les sommes des montants pour chaque catégorie ou type.
        """
        assert isinstance(transactions, dict), "transactions doit être un dictionnaire"
        
        sums = {}
        for category, transactionsList in transactions.items():
            total = sum(transaction['MONTANT'] for transaction in transactionsList)
            sums[category] = total
        return sums

    def GetLabelIndex(self, label: str) -> int:
        """
        Obtient l'index du label, en l'ajoutant si nécessaire.
        """
        assert isinstance(label, str), "label doit être une chaîne de caractères"
        
        if label not in self.labelDict:
            self.labelDict[label] = self.nextIndex
            self.labels.append(label)
            self.nextIndex += 1
        return self.labelDict[label]

    def ProcessExpenses(self):
        """
        Traite les transactions lorsque les dépenses sont regroupées par catégories.
        """
        self.nextIndex = 0
        for category, transactions in self.data.items():
            if category not in self.labelDict:
                self.labelDict[category] = self.nextIndex
                self.labels.append(category)
                self.nextIndex += 1
            for transaction in transactions:
                transactionType = transaction['Type']
                if transactionType not in self.labelDict:
                    self.labelDict[transactionType] = self.nextIndex
                    self.labels.append(transactionType)
                    self.nextIndex += 1
                self.sources.append(self.labelDict[category])
                self.targets.append(self.labelDict[transactionType])
                self.values.append(abs(transaction['MONTANT']))

    def CleanTransactionsAndGroup(self) -> dict:
        """
        Nettoie les transactions en supprimant les clés non nécessaires et regroupe les transactions par catégorie.
        """

        reformattedData = {}
        for category, transactionsList in self.dictionnaire.items():
            if transactionsList:
                transactionsWithTotals = [{'Type': transaction['Type'], 'MONTANT': transaction['MONTANT']} for transaction in transactionsList]
                totals = self.CalculateTotals(transactionsList)
                categoryTotal = round(sum(totals.values()), 2)
                reformattedData[f'{category}: {categoryTotal:.2f} €'] = transactionsWithTotals
            else:
                reformattedData[category] = []

        return reformattedData

    def AddTransactions(self, transactions, cle: str = None, depenses: bool = True):
        """
        Ajoute les transactions au graphique Sankey en fonction de la catégorie et des types.
        """
        assert isinstance(depenses, bool), "depenses doit être un booléen"

        if not depenses:
            if isinstance(transactions, list):
                for transaction in transactions:
                    targetName = transaction['Type']
                    argent = sum(trans['MONTANT'] for trans in transactions if trans['Type'] == targetName)
                    targetName += f": {abs(round(argent, 2))} €"
                    sourceIdx = self.GetLabelIndex(targetName)
                    targetIdx = self.GetLabelIndex(cle)
                    self.sources.append(sourceIdx)
                    self.targets.append(targetIdx)
                    self.values.append(round(abs(transaction['MONTANT']), 2))
            else:
                self.ProcessExpenses()
        else:
            for category, montant in self.SumAmounts(transactions).items():
                if montant < 0:
                    targetName = category
                    mainSourceIdx = 1
                    sourceIdx = self.GetLabelIndex(targetName)
                    self.sources.append(mainSourceIdx)
                    self.targets.append(sourceIdx)
                    self.values.append(abs(round(montant, 2)))

            for sousCategory, transaction in transactions.items():
                if transaction:
                    for ele in transaction:
                        targetName = ele['Type']
                        argent = sum(trans['MONTANT'] for trans in transaction if trans['Type'] == targetName)
                        targetName += f": {abs(round(argent, 2))} €"
                        sourceIdx = self.GetLabelIndex(sousCategory)
                        targetIdx = self.GetLabelIndex(targetName)
                        self.sources.append(sourceIdx)
                        self.targets.append(targetIdx)
                        self.values.append(abs(round(ele['MONTANT'], 2)))

    def GenerateSankey(self):
        """
        Génère le graphique Sankey à partir des transactions et des catégories.
        """
        pattern = r'Revenus: -?\d+(?:,\d{3})*(?:\.\d+)?'
        cle = ""
        for key in self.data.keys():
            if re.match(pattern, key):
                cle = key
                self.AddTransactions(self.data[cle], cle, False)
                self.data.pop(cle)
                break

        if cle == "":
            self.AddTransactions(self.data)
        else:
            self.AddTransactions(self.data)

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black', width=0.5),
                label=self.labels
            ),
            link=dict(
                source=self.sources,
                target=self.targets,
                value=self.values
            )
        )])

        fig.update_layout(
            title_text=self.title,
            title_x=0.5,
            font_size=10,
            width=1800,
            height=900,
            margin=dict(
                l=100,
                r=100,
                t=50,
                b=50
            )
        )

        self.figure = fig

    def GetFigure(self) -> go.Figure:
        """
        Renvoie le graphique Sankey généré.
        """
        return self.figure

