import calendar
from datetime import datetime

import customtkinter as ctk


class CustomCalendar(ctk.CTkToplevel):
    """Fenêtre surgissante affichant un calendrier interactif pour choisir une date."""

    def __init__(self, parent, current_date_str, callback):
        super().__init__(parent)
        self.title("Choisir une date")
        self.geometry("300x350")
        self.transient(parent)
        self.grab_set()

        self._callback = callback
        # Parsing de la date actuelle ou défaut à aujourd'hui
        try:
            self._current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
        except:
            self._current_date = datetime.now()

        self._view_month = self._current_date.month
        self._view_year = self._current_date.year

        self.__setup_ui()

    def __setup_ui(self):
        """Ajoute l'entête pour les mois et la navigation."""

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(header, text="<", width=30, command=lambda: self.__change_month(-1)).pack(side="left")

        self.month_label = ctk.CTkLabel(header, text="", font=("Arial", 14, "bold"))
        self.month_label.pack(side="left", expand=True)

        ctk.CTkButton(header, text=">", width=30, command=lambda: self.__change_month(1)).pack(side="left")

        # Grille des jours
        self.days_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.days_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.__draw_calendar()

    def __draw_calendar(self):
        """Affiche le calendrier"""

        for widget in self.days_frame.winfo_children():
            widget.destroy()

        # Nom du mois
        month_name = calendar.month_name[self._view_month]
        self.month_label.configure(text=f"{month_name} {self._view_year}")

        # En-têtes Jours (L, M, M...)
        days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        for i, day in enumerate(days):
            ctk.CTkLabel(self.days_frame, text=day, font=("Arial", 11)).grid(row=0, column=i, sticky="nsew")

        # Calcul des jours du mois
        month_days = calendar.monthcalendar(self._view_year, self._view_month)

        for r, week in enumerate(month_days):
            for c, day in enumerate(week):
                if day != 0:
                    # Style différent pour le jour aujourd'hui
                    is_today = (
                        day == datetime.now().day
                        and self._view_month == datetime.now().month
                        and self._view_year == datetime.now().year
                    )

                    btn = ctk.CTkButton(
                        self.days_frame,
                        text=str(day),
                        width=35,
                        height=35,
                        fg_color="#3B8ED0",
                        border_width=1 if is_today else 0,
                        command=lambda d=day: self.__select_date(d),
                    )
                    btn.grid(row=r + 1, column=c, padx=1, pady=1)

    def __change_month(self, delta):
        """Décale le mois affiché et ajuste l'année en cas de dépassement."""

        self._view_month += delta
        if self._view_month > 12:
            self._view_month = 1
            self._view_year += 1
        elif self._view_month < 1:
            self._view_month = 12
            self._view_year -= 1
        self.__draw_calendar()

    def __select_date(self, day):
        """Formate la date sélectionnée, exécute le callback et ferme la vue."""

        selected = datetime(self._view_year, self._view_month, day)
        self._callback(selected.strftime("%Y-%m-%d"))
        self.destroy()
