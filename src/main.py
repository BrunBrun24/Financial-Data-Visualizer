from code.mainBourse import CreateData, UpdateData
from code.mainPatrimoine import GetPatrimoine
from customtkinter import *
import threading
import time


class InterfaceGraphique:
    def __init__(self) -> None:
        """
        Initialise l'interface graphique avec les différentes options de gestion.
        """
        self.app = CTk()
        self.app.geometry("900x600")
        self.app.title("Gestion des Finances")

        # Conteneur principal qui contient les différentes sections
        self.frame_principal = None

        # Créer les sections personnalisées
        self.CreerMenu()

        # Démarrer la boucle principale de l'application
        self.app.mainloop()

    def CreerMenu(self) -> None:
        """
        Crée le menu principal avec les options pour mettre à jour les données,
        catégoriser les dépenses et afficher les graphiques.
        """
        # Si un autre frame est déjà affiché, on le détruit
        if self.frame_principal:
            self.frame_principal.destroy()

        # Crée le frame principal du menu
        self.frame_principal = CTkFrame(master=self.app, width=600, height=400)
        self.frame_principal.pack(expand=True, fill="both", padx=20, pady=20)

        CTkLabel(master=self.frame_principal, text="Menu Principal", font=("Arial Bold", 24)).pack(pady=20)

        # Ajouter les boutons pour chaque action
        CTkButton(master=self.frame_principal, text="Mettre à jour les données boursières", command=self.MettreAJourDonnees).pack(pady=10)
        CTkButton(master=self.frame_principal, text="Catégoriser les nouvelles dépenses", command=self.CategoriserDepenses).pack(pady=10)
        CTkButton(master=self.frame_principal, text="Visualiser les graphiques", command=self.AfficherGraphiques).pack(pady=10)

    def AfficherGraphiques(self) -> None:
        """
        Affiche le sous-menu des graphiques à visualiser.
        """
        # On détruit le menu principal avant d'afficher les graphiques
        if self.frame_principal:
            self.frame_principal.destroy()

        self.frame_principal = CTkFrame(master=self.app, width=600, height=400)
        self.frame_principal.pack(expand=True, fill="both", padx=20, pady=20)

        CTkLabel(master=self.frame_principal, text="Sélectionnez un graphique", font=("Arial Bold", 20)).pack(pady=20)

        # Sous-menu pour les graphiques Bourse
        CTkLabel(master=self.frame_principal, text="Bourse", font=("Arial", 16)).pack(pady=10)
        CTkButton(master=self.frame_principal, text="Progression du portefeuille en %", command=self.GraphiquePourcentage).pack(pady=5)
        CTkButton(master=self.frame_principal, text="Progression du portefeuille en €", command=self.GraphiqueEuro).pack(pady=5)
        CTkButton(master=self.frame_principal, text="Répartition du portefeuille", command=self.GraphiqueRepartition).pack(pady=5)

        # Sous-menu pour les graphiques Banque
        CTkLabel(master=self.frame_principal, text="Banque", font=("Arial", 16)).pack(pady=10)
        CTkButton(master=self.frame_principal, text="Livret A", command=self.GraphiqueLivretA).pack(pady=5)
        CTkButton(master=self.frame_principal, text="Compte Courant", command=self.GraphiqueCompteCourant).pack(pady=5)

        # Sous-menu pour les graphiques Banque
        CTkLabel(master=self.frame_principal, text="Patrimoine", font=("Arial", 16)).pack(pady=10)
        CTkButton(master=self.frame_principal, text="Patrimoine", command=self.GraphiquePatrimoine).pack(pady=5)

        # Ajouter un bouton pour retourner au menu principal
        CTkButton(master=self.frame_principal, text="Retour", command=self.CreerMenu).pack(pady=20)

    def AfficherAnimation(self, action: str, fonction: callable, duree_estimee: int) -> None:
        """
        Affiche une petite animation pendant l'exécution d'une fonction.

        Args:
            action (str): Le texte à afficher pendant l'action.
            fonction (callable): La fonction à exécuter en arrière-plan.
            duree_estimee (int): Durée estimée de l'exécution en secondes.
        """
        # Détruire le menu principal
        if self.frame_principal:
            self.frame_principal.destroy()

        # Créer un nouveau frame avec une animation
        self.frame_principal = CTkFrame(master=self.app, width=600, height=400)
        self.frame_principal.pack(expand=True, fill="both", padx=20, pady=20)

        self.animation_label = CTkLabel(master=self.frame_principal, text=action, font=("Arial", 20))
        self.animation_label.pack(pady=20)

        # Exécuter la fonction en arrière-plan
        thread = threading.Thread(target=self.ExecuterFonctionAvecAnimation, args=(fonction, duree_estimee))
        thread.start()

    def ExecuterFonctionAvecAnimation(self, fonction: callable, duree_estimee: int) -> None:
        """
        Exécute une fonction et anime l'étiquette pendant l'exécution.

        Args:
            fonction (callable): La fonction à exécuter.
            duree_estimee (int): Durée estimée en secondes pour l'exécution de la fonction.
        """
        frames = ['', '.', '..', '...']
        total_frames = len(frames)
        etapes = 10  # Diviser la tâche en 10 étapes

        for i in range(etapes):
            # Mettre à jour l'animation
            frame_index = i % total_frames
            self.animation_label.configure(text=f"En cours {frames[frame_index]}")
            self.app.update()

            # Simuler l'exécution de la fonction par étape
            time.sleep(duree_estimee / etapes)

        # Exécuter la fonction réelle après la progression
        fonction()

        # Remettre au menu principal après un délai
        self.animation_label.configure(text="Terminé !")
        self.app.after(2000, self.CreerMenu)

    ########## Actions à faire ##########
    def MettreAJourDonnees(self) -> None:
        """
        Action pour mettre à jour les données boursières.
        """
        self.AfficherAnimation("Mise à jour des données boursières en cours...", UpdateData, duree_estimee=5)

    def CategoriserDepenses(self) -> None:
        """
        Action pour catégoriser les nouvelles dépenses.
        """
        self.AfficherAnimation("Catégorisation des nouvelles dépenses en cours...", CreateData, duree_estimee=5)

    # Fonctions pour les différents graphiques
    def GraphiquePatrimoine(self) -> None:
        """
        Action pour afficher le patrimoine.
        """
        self.AfficherAnimation("Affiche du patrimoine en cours...", GetPatrimoine, duree_estimee=5)

    def GraphiquePourcentage(self) -> None:
        print("Affichage de la progression du portefeuille en pourcentage")

    def GraphiqueEuro(self) -> None:
        print("Affichage de la progression du portefeuille en euro")

    def GraphiqueRepartition(self) -> None:
        print("Affichage de la répartition du portefeuille")

    def GraphiqueLivretA(self) -> None:
        print("Affichage des données du Livret A")

    def GraphiqueCompteCourant(self) -> None:
        print("Affichage des données du Compte Courant")

# Point d'entrée pour lancer l'interface
if __name__ == "__main__":
    interface = InterfaceGraphique()
