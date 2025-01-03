import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime
import pandas as pd

class DateExecutionTkinter:

    def __init__(self, data: pd.DataFrame, dateCol: str, tickerCol: str):
        """
        Initialise la fenêtre Tkinter pour valider ou corriger la date d'exécution.

        Args:
            data (pd.DataFrame): DataFrame contenant les données.
            dateCol (str): Nom de la colonne contenant les dates d'exécution.
            tickerCol (str): Nom de la colonne contenant les tickers.
        """
        assert isinstance(data, pd.DataFrame), "Le paramètre data doit être un DataFrame."
        assert dateCol in data.columns, f"Le DataFrame doit contenir une colonne '{dateCol}'."
        assert tickerCol in data.columns, f"Le DataFrame doit contenir une colonne '{tickerCol}'."

        self.data = data.copy()  # Copier les données pour éviter de modifier l'original
        self.dateCol = dateCol
        self.tickerCol = tickerCol
        self.uniqueDates = sorted(self.data[dateCol].unique())  # Trier les dates de la plus ancienne à la plus récente
        self.index = 0  # Index pour parcourir les dates uniques

        # Initialisation de Tkinter
        self.root = tk.Tk()
        self.root.title("Validation de la Date d'Exécution")

        # Centrer la fenêtre
        screenWidth = self.root.winfo_screenwidth()
        screenHeight = self.root.winfo_screenheight()
        windowWidth = 1250
        windowHeight = 650
        positionTop = int(screenHeight / 2 - windowHeight / 2)
        positionRight = int(screenWidth / 2 - windowWidth / 2)
        self.root.geometry(f'{windowWidth}x{windowHeight}+{positionRight}+{positionTop}')

    def DisplayNext(self):
        """Affiche la prochaine date d'exécution et les tickers associés à valider."""
        if self.index < len(self.uniqueDates):
            currentDate = self.uniqueDates[self.index]
            tickers = self.data[self.data[self.dateCol] == currentDate][self.tickerCol].tolist()
            self.AskUser(currentDate, tickers)
        else:
            # Si toutes les dates ont été traitées, fermer l'application
            self.root.quit()
            self.root.destroy()  # Ajout de cette ligne pour fermer la fenêtre après la fin

    def AskUser(self, dateExecution, tickers):
        """Demande à l'utilisateur de valider ou modifier la date d'exécution."""
        # Effacer les anciens widgets
        self.ClearWindow()

        # Préparer le message principal
        # Format classique de la date avec la suppression du zéro pour le jour
        formattedDate = f"{dateExecution.day} {dateExecution.strftime('%B')} {dateExecution.year}"
        message = f"La date d'exécution suivante est-elle correcte ?\n\n📅 {formattedDate}"

        # Créer un label pour afficher les informations
        label = tk.Label(self.root, text=message, font=("Arial", 14), justify="left", wraplength=500)
        label.pack(pady=10)

        if len(tickers) > 40:
            self.DisplayTickersScrollable(tickers)
        else:
            # Afficher les tickers dans une grille avec 4 tickers par ligne
            self.DisplayTickersGrid(tickers)

        # Créer un cadre pour les boutons en bas de la fenêtre
        buttonFrame = tk.Frame(self.root)
        buttonFrame.pack(side="bottom", pady=20)

        # Placer les boutons "Oui" et "Non" dans ce cadre
        yesButton = tk.Button(buttonFrame, text="Oui", command=self.OnYes, bg="lightgreen", padx=20, pady=10)
        yesButton.pack(side="left", padx=10)

        noButton = tk.Button(buttonFrame, text="Non", command=self.OnNo, bg="salmon", padx=20, pady=10)
        noButton.pack(side="right", padx=10)

    def DisplayTickersScrollable(self, tickers):
        """Affiche les tickers dans une zone avec une barre de défilement."""
        tickerFrame = tk.Frame(self.root)
        tickerFrame.pack(pady=10)

        tickerScrollbar = tk.Scrollbar(tickerFrame)
        tickerScrollbar.pack(side="right", fill="y")

        tickerText = tk.Text(
            tickerFrame, wrap="none", height=15, width=50, font=("Arial", 12), yscrollcommand=tickerScrollbar.set
        )
        tickerText.pack(side="left", fill="both", expand=True)
        tickerScrollbar.config(command=tickerText.yview)

        for i, ticker in enumerate(tickers):
            tickerText.insert("end", f"• {ticker}\n")
        tickerText.config(state="disabled")  # Empêche l'édition

    def DisplayTickersGrid(self, tickers):
        """Affiche les tickers dans une grille sans barre de défilement."""
        gridFrame = tk.Frame(self.root)
        gridFrame.pack(pady=10)

        for i, ticker in enumerate(tickers):
            row = i // 5  # Ligne (1 ticker par groupe de 5)
            col = i % 5   # Colonne
            tickerLabel = tk.Label(gridFrame, text=f"• {ticker}", font=("Arial", 12), padx=10, pady=5)
            tickerLabel.grid(row=row, column=col, padx=5, pady=5)

    def OnYes(self):
        """L'utilisateur a validé la date d'exécution."""
        self.index += 1
        self.DisplayNext()

    def OnNo(self):
        """L'utilisateur souhaite corriger la date d'exécution pour tous les tickers associés."""
        currentDate = self.uniqueDates[self.index]
        while True:
            newDate = simpledialog.askstring(
                "Correction de la Date",
                "Entrez la nouvelle date d'exécution (format : YYYY-MM-DD) :",
                parent=self.root
            )
            if newDate:
                try:
                    # Vérifier que la date est valide
                    newDateObj = datetime.strptime(newDate, "%Y-%m-%d")
                    # Mettre à jour le DataFrame pour tous les tickers ayant cette date
                    self.data.loc[self.data[self.dateCol] == currentDate, self.dateCol] = newDateObj
                    self.index += 1
                    break
                except ValueError:
                    messagebox.showerror("Erreur", "Format de date invalide. Utilisez le format YYYY-MM-DD.")
            else:
                messagebox.showinfo("Info", "Aucune modification effectuée. Passage à la ligne suivante.")
                self.index += 1
                break

        self.DisplayNext()

    def ClearWindow(self):
        """Efface tous les widgets de la fenêtre."""
        for widget in self.root.winfo_children():
            widget.destroy()

    def Run(self) -> pd.DataFrame:
        """
        Lancer l'interface graphique et retourner le DataFrame corrigé.

        Returns:
            pd.DataFrame: DataFrame mis à jour avec des dates d'exécution corrigées.
        """
        if self.data is not None and not self.data.empty:
            self.DisplayNext()
            self.root.mainloop()
        return self.data

