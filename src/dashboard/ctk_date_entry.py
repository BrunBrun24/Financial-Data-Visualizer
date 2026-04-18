from datetime import datetime

import customtkinter as ctk

from dashboard.custom_calendar import CustomCalendar


class CtkDateEntry(ctk.CTkFrame):
    """Widget simulant une entrée de date avec un bouton calendrier intégré."""

    def __init__(self, master, initial_date=None):
        super().__init__(master, fg_color="transparent")

        self.date_var = ctk.StringVar(value=initial_date or datetime.now().strftime("%Y-%m-%d"))

        # Champ de texte (Lecture seule pour forcer l'usage du calendrier)
        self.entry = ctk.CTkEntry(self, textvariable=self.date_var, width=150)
        self.entry.pack(side="left", padx=(0, 5))

        self.btn = ctk.CTkButton(self, text="📅", width=40, command=self.__open_calendar)
        self.btn.pack(side="left")

    def get(self):
        return self.date_var.get()

    def __open_calendar(self):
        CustomCalendar(self.winfo_toplevel(), self.date_var.get(), self.__set_date)

    def __set_date(self, date_str):
        self.date_var.set(date_str)
