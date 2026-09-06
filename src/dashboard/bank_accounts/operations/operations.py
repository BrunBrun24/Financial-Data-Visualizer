import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd

from accounts.bank.importers.data_extractor import DataExtractor
from accounts.bank.processing.categorizer import Categorizer
from accounts.bank.reporting.excel_generator import excel_generate_all_reports
from accounts.bank.visualization.financial_chart import chart_generate_all_reports
from accounts.heritage.processing.processing import calculate_heritage
from dashboard.bank_accounts.operations.components.operation_edit_window import OperationEditWindow
from utils.data_utils import remove_accents
from utils.loading_popup import LoadingPopup
from utils.window_utils import center_window_on_screen


class Operations:
    def __init__(self, master: ctk.CTkFrame, controller) -> None:
        self.__master = master
        self.__controller = controller
        self.__config = controller.get_config()
        self.__theme = controller.get_theme()
        self.__bank_db = self.__controller.get_bank_db()
        self.__stock_db = self.__controller.get_stock_db()
        self._sort_column = "operation_date"
        self._sort_ascending = False
        self.__selected_operation_ids = set()
        self.__column_filters = {}

    def display(self, bank_account_row: pd.Series, page: int = 1) -> None:
        """Initialise la structure fixe (Header, Actions) et lance le chargement du tableau."""

        self.__controller.destroy_widgets()
        self.__selected_operation_ids.clear()

        # Header de navigation
        nav_header = ctk.CTkFrame(self.__master, fg_color="transparent")
        nav_header.pack(fill="x", padx=20, pady=10)

        back_btn = ctk.CTkButton(
            nav_header,
            text="←",
            fg_color=self.__theme["blue_01"]["fg_color"],
            hover_color=self.__theme["blue_01"]["hover_color"],
            width=40,
            command=lambda: self.__controller.show_bank_account_menu(bank_account_row),
        )
        back_btn.place(x=0, y=15)

        ctk.CTkLabel(
            nav_header,
            text="Gestion du compte",
            font=("Arial", 40, "bold"),
        ).pack(pady=(5, 30))

        # Barre d'actions
        self.__account_actions_bar = ctk.CTkFrame(self.__master, fg_color="transparent")
        self.__account_actions_bar.pack(fill="x", padx=20, pady=10)

        self.__build_actions_bar(bank_account_row)

        # Zone d'affichage
        self.__table_container_wrapper = ctk.CTkFrame(self.__master, fg_color="transparent")
        self.__table_container_wrapper.pack(fill="both", expand=True, padx=20, pady=10)

        # Premier chargement du tableau
        self.__update_table_content(bank_account_row, page)

    def __build_actions_bar(self, bank_account_row: pd.Series) -> None:
        """Construit ou met à jour la barre d'actions en fonction des sélections."""
        for widget in self.__account_actions_bar.winfo_children():
            widget.destroy()

        ctk.CTkButton(
            self.__account_actions_bar,
            text="Importer des opérations",
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=lambda: self.__handle_import_process(bank_account_row),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.__account_actions_bar,
            text="Ajouter une opération",
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=lambda: self.__handle_add_operation(bank_account_row),
        ).pack(side="left", padx=5)

        operations = self.__bank_db.get_unprocessed_raw_operations(bank_account_row["id"])
        ctk.CTkButton(
            self.__account_actions_bar,
            text="Catégoriser les opérations",
            fg_color=self.__theme["blue_01"]["fg_color"],
            hover_color=self.__theme["blue_01"]["hover_color"],
            state="normal" if operations else "disabled",
            command=lambda: self.__handle_categorization_process(bank_account_row),
        ).pack(side="left", padx=5)

        # Bouton de réinitialisation des filtres aligné à droite de la barre d'actions si actif
        # Un filtre est actif si un filtre de colonne existe ou si le tri a été modifié
        is_custom_sorted = hasattr(self, "_sort_column") and self._sort_column != "operation_date"
        has_active_filters = len(self.__column_filters) > 0 or is_custom_sorted

        if has_active_filters:
            ctk.CTkButton(
                self.__account_actions_bar,
                text="Réinitialiser les filtres",
                width=150,
                height=28,
                fg_color="gray60",
                hover_color="gray50",
                font=("Arial", 12),
                command=lambda: (
                    self.__column_filters.clear(),
                    setattr(self, "_sort_column", "operation_date"),
                    setattr(self, "_sort_ascending", False),
                    self.__update_table_content(bank_account_row, 1),
                ),
            ).pack(side="right", padx=5)

        # Bouton de suppression groupée si des éléments sont sélectionnés
        if self.__selected_operation_ids:
            ctk.CTkButton(
                self.__account_actions_bar,
                text=f"Supprimer la sélection ({len(self.__selected_operation_ids)})",
                fg_color=self.__theme["red"]["fg_color"],
                hover_color=self.__theme["red"]["hover_color"],
                command=lambda: self.__handle_delete_selected_operations(bank_account_row),
            ).pack(side="right", padx=5)

    def __update_table_content(self, bank_account_row: pd.Series, page: int) -> None:
        """Rafraîchit le tableau"""

        # Reconstruit la barre d'actions pour mettre à jour l'état du bouton de réinitialisation
        self.__build_actions_bar(bank_account_row)

        for widget in self.__table_container_wrapper.winfo_children():
            widget.destroy()

        bank_account_id = bank_account_row["id"]
        items_per_page = 21
        currency_symbol = self.__bank_db.get_bank_account_currency_symbol(bank_account_id)

        try:
            df = self.__bank_db.get_operations_by_bank_account(bank_account_id)

            if not df.empty:
                # Application des filtres par colonnes
                df["operation_date_dt"] = pd.to_datetime(df["operation_date"], errors="coerce")
                df["year_str"] = df["operation_date_dt"].dt.year.astype(str)

                for col_name, selected_vals in self.__column_filters.items():
                    if col_name == "Date":
                        if selected_vals:
                            df = df[df["year_str"].isin(selected_vals)]
                        else:
                            df = df.iloc[0:0]
                    elif col_name == "Libellé":
                        if selected_vals:
                            df = df[df["label"].astype(str).isin(selected_vals)]
                        else:
                            df = df.iloc[0:0]
                    elif col_name == "Catégorie":
                        if selected_vals:
                            df = df[df["category"].astype(str).isin(selected_vals)]
                        else:
                            df = df.iloc[0:0]
                    elif col_name == "Sous-Catégorie":
                        if selected_vals:
                            df = df[df["sub_category"].astype(str).isin(selected_vals)]
                        else:
                            df = df.iloc[0:0]
                    elif col_name == "Montant":
                        if selected_vals:
                            if isinstance(selected_vals, dict):
                                op = selected_vals.get("operator")
                                target = selected_vals.get("value")
                                if op == "Supérieur ou égal (>=)":
                                    df = df[df["amount"] >= target]
                                elif op == "Inférieur ou égal (<=)":
                                    df = df[df["amount"] <= target]
                                elif op == "Égal (=)":
                                    df = df[df["amount"] == target]
                            elif isinstance(selected_vals, list):
                                df = df[df["amount"].isin(selected_vals)]
                        else:
                            df = df.iloc[0:0]

                df = df.sort_values(by="operation_date", ascending=True)
                df["id_view"] = range(1, len(df) + 1)

                if hasattr(self, "_sort_column") and self._sort_column:
                    df = df.sort_values(
                        by=[self._sort_column, "id_view"],
                        ascending=[self._sort_ascending, False],
                        key=lambda col: col.map(lambda x: remove_accents(str(x).lower()) if isinstance(x, str) else x),
                    )

                total_ops = len(df)
                total_pages = max(1, (total_ops // items_per_page) + (1 if total_ops % items_per_page > 0 else 0))
                page = max(1, min(page, total_pages))

                start_idx = (page - 1) * items_per_page
                page_data = df.iloc[start_idx : start_idx + items_per_page]

                header_table = ctk.CTkFrame(self.__table_container_wrapper, fg_color="gray80", height=40)
                header_table.pack(fill="x", pady=(0, 5))
                header_table.pack_propagate(False)

                header_table.grid_columnconfigure(0, weight=0, minsize=40)
                header_table.grid_columnconfigure(1, weight=0, minsize=50)
                header_table.grid_columnconfigure((2, 4, 5, 6), weight=1, uniform="group_trans")
                header_table.grid_columnconfigure(3, weight=3, uniform="group_trans")
                header_table.grid_columnconfigure(7, weight=0, minsize=90)

                page_ids = page_data["id"].tolist()
                all_page_selected = (
                    all(op_id in self.__selected_operation_ids for op_id in page_ids) and len(page_ids) > 0
                )

                master_cb = ctk.CTkCheckBox(
                    header_table,
                    text="",
                    width=20,
                    checkbox_width=18,
                    checkbox_height=18,
                    command=lambda: self.__toggle_select_all_page(bank_account_row, page, page_ids, master_cb),
                )
                master_cb.grid(row=0, column=0, padx=(10, 0), pady=5, sticky="w")
                if all_page_selected:
                    master_cb.select()

                columns = ["#", "Date", "Libellé", "Catégorie", "Sous-Catégorie", "Montant", "Justificatifs"]

                for i, col_name in enumerate(columns, start=1):
                    padx_val = (10, 20) if i == 1 else 5

                    if col_name in ["Montant", "Justificatifs"]:
                        anchor_val = "center"
                        cell_sticky = "nsew"
                    elif i in [2, 3, 4, 5]:
                        anchor_val = "w"
                        cell_sticky = "w"
                    else:
                        anchor_val = "center"
                        cell_sticky = "w"

                    cell_header_f = ctk.CTkFrame(header_table, fg_color="transparent")
                    cell_header_f.grid(row=0, column=i, padx=padx_val, pady=5, sticky=cell_sticky)

                    if col_name in ["Montant", "Justificatifs"]:
                        inner_center_f = ctk.CTkFrame(cell_header_f, fg_color="transparent")
                        inner_center_f.pack(expand=True)

                        lbl = ctk.CTkLabel(
                            inner_center_f,
                            text=col_name,
                            font=("Arial", 14, "bold"),
                            text_color="black",
                            anchor="center",
                        )
                        lbl.pack(side="left")

                        if col_name == "Montant":
                            filter_btn = ctk.CTkButton(
                                inner_center_f,
                                text="▼",
                                width=18,
                                height=18,
                                font=("Arial", 9),
                                fg_color="transparent",
                                hover_color="gray70",
                                text_color="black",
                            )
                            filter_btn.configure(
                                command=lambda btn=filter_btn, c=col_name: self.__show_excel_filter_popup(
                                    btn, c, bank_account_row, page, is_amount=True
                                )
                            )
                            filter_btn.pack(side="left", padx=(4, 0))
                    else:
                        lbl = ctk.CTkLabel(
                            cell_header_f,
                            text=col_name,
                            font=("Arial", 14, "bold"),
                            text_color="black",
                            anchor=anchor_val,
                        )
                        lbl.pack(side="left")

                        if col_name not in ["#", "Justificatifs"]:
                            filter_btn = ctk.CTkButton(
                                cell_header_f,
                                text="▼",
                                width=18,
                                height=18,
                                font=("Arial", 9),
                                fg_color="transparent",
                                hover_color="gray70",
                                text_color="black",
                            )
                            filter_btn.configure(
                                command=lambda btn=filter_btn, c=col_name: self.__show_excel_filter_popup(
                                    btn, c, bank_account_row, page
                                )
                            )
                            filter_btn.pack(side="left", padx=(4, 0))

                    if col_name == "#":
                        lbl.configure(width=50, anchor="center")

                rows_container = ctk.CTkFrame(self.__table_container_wrapper, fg_color="transparent", height=680)
                rows_container.pack(fill="x")
                rows_container.pack_propagate(False)

                for i, (index, operation) in enumerate(page_data.iterrows(), 1):
                    op_id = operation["id"]
                    is_selected = op_id in self.__selected_operation_ids

                    default_bg = "gray95" if i % 2 == 0 else "gray90"
                    hover_bg = "gray82"

                    row_f = ctk.CTkFrame(rows_container, fg_color=default_bg, height=30, cursor="hand2")
                    row_f.pack(fill="x", pady=1)

                    row_f.grid_columnconfigure(0, weight=0, minsize=40)
                    row_f.grid_columnconfigure(1, weight=0, minsize=50)
                    row_f.grid_columnconfigure((2, 4, 5, 6), weight=1, uniform="group_trans")
                    row_f.grid_columnconfigure(3, weight=3, uniform="group_trans")
                    row_f.grid_columnconfigure(7, weight=0, minsize=90)

                    cb_var = ctk.BooleanVar(value=is_selected)

                    row_cb = ctk.CTkCheckBox(
                        row_f,
                        text="",
                        width=20,
                        checkbox_width=18,
                        checkbox_height=18,
                        variable=cb_var,
                        fg_color=default_bg,
                        border_color="black",
                        checkmark_color="black",
                        command=lambda oid=op_id: self.__toggle_select_operation(oid, bank_account_row, page),
                    )
                    row_cb.grid(row=0, column=0, padx=(10, 0), sticky="w")
                    if op_id in self.__selected_operation_ids:
                        row_cb.select()

                    lbl_id = ctk.CTkLabel(
                        row_f,
                        text=str(operation["id_view"]),
                        font=("Arial", 11, "italic"),
                        width=50,
                        anchor="center",
                        fg_color=default_bg,
                    )
                    lbl_id.grid(row=0, column=1, padx=(10, 20), sticky="nsew")

                    lbl_date = ctk.CTkLabel(row_f, text=operation["operation_date"], anchor="w", fg_color=default_bg)
                    lbl_date.grid(row=0, column=2, padx=5, sticky="nsew")

                    lbl_label = ctk.CTkLabel(row_f, text=operation["label"], anchor="w", fg_color=default_bg)
                    lbl_label.grid(row=0, column=3, padx=5, sticky="nsew")

                    lbl_cat = ctk.CTkLabel(row_f, text=operation["category"], anchor="w", fg_color=default_bg)
                    lbl_cat.grid(row=0, column=4, padx=5, sticky="nsew")

                    lbl_subcat = ctk.CTkLabel(row_f, text=operation["sub_category"], anchor="w", fg_color=default_bg)
                    lbl_subcat.grid(row=0, column=5, padx=5, sticky="nsew")

                    amt = operation["amount"]
                    formatted_amt = f"{amt:,.2f}".replace(",", " ") + f" {currency_symbol}"
                    color = self.__theme["red"]["fg_color"] if amt < 0 else self.__theme["green"]["fg_color"]
                    lbl_amt = ctk.CTkLabel(
                        row_f,
                        text=formatted_amt,
                        text_color=color,
                        font=("Arial", 12, "bold"),
                        fg_color=default_bg,
                        anchor="center",
                    )
                    lbl_amt.grid(row=0, column=6, padx=5, sticky="nsew")

                    attachments = self.__bank_db.get_operation_attachments(op_id)
                    has_attachments = len(attachments) > 0

                    att_text = f"Fichier ({len(attachments)})" if has_attachments else "Fichier"
                    att_color = self.__theme["blue_01"]["fg_color"] if has_attachments else "gray60"
                    att_hover = self.__theme["blue_01"]["hover_color"] if has_attachments else "gray50"

                    att_btn = ctk.CTkButton(
                        row_f,
                        text=att_text,
                        width=95,
                        height=24,
                        corner_radius=6,
                        font=("Arial", 11, "bold"),
                        fg_color=att_color,
                        hover_color=att_hover,
                        command=lambda o=operation: self.__handle_attachments_modal(o, bank_account_row, page),
                    )
                    att_btn.grid(row=0, column=7, padx=5, pady=4)

                    widgets_in_row = [row_f, lbl_id, lbl_date, lbl_label, lbl_cat, lbl_subcat, lbl_amt]

                    def on_enter(event, wf=widgets_in_row, cb=row_cb):
                        for w in wf:
                            w.configure(fg_color=hover_bg)
                        cb.configure(fg_color=hover_bg)

                    def on_leave(event, wf=widgets_in_row, cb=row_cb, bg=default_bg):
                        for w in wf:
                            w.configure(fg_color=bg)
                        cb.configure(fg_color=bg)

                    for w in widgets_in_row:
                        w.bind("<Enter>", on_enter)
                        w.bind("<Leave>", on_leave)
                        if w != att_btn:
                            w.bind(
                                "<Button-1>",
                                lambda event, o=operation: self.__handle_edit_operation(o, bank_account_row),
                            )

                pagination_container = ctk.CTkFrame(self.__table_container_wrapper, fg_color="transparent")
                pagination_container.pack(fill="x", pady=20)

                center_frame = ctk.CTkFrame(pagination_container, fg_color="transparent")
                center_frame.pack(expand=True)

                # Saut de -10 pages
                ctk.CTkButton(
                    center_frame,
                    text=" << ",
                    width=40,
                    state="normal" if page > 1 else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(bank_account_row, max(1, page - 10)),
                ).pack(side="left", padx=5)

                # Précédent
                ctk.CTkButton(
                    center_frame,
                    text=" < ",
                    width=40,
                    state="normal" if page > 1 else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(bank_account_row, page - 1),
                ).pack(side="left", padx=5)

                ctk.CTkLabel(
                    center_frame, text=f"Page {page} / {total_pages}", font=("Arial", 13, "bold"), width=120
                ).pack(side="left", padx=15)

                # Suivant
                ctk.CTkButton(
                    center_frame,
                    text=" > ",
                    width=40,
                    state="normal" if page < total_pages else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(bank_account_row, page + 1),
                ).pack(side="left", padx=5)

                # Saut de +10 pages
                ctk.CTkButton(
                    center_frame,
                    text=" >> ",
                    width=40,
                    state="normal" if page < total_pages else "disabled",
                    fg_color=self.__theme["blue_01"]["fg_color"],
                    hover_color=self.__theme["blue_01"]["hover_color"],
                    command=lambda: self.__update_table_content(bank_account_row, min(total_pages, page + 10)),
                ).pack(side="left", padx=5)

            else:
                ctk.CTkLabel(self.__table_container_wrapper, text="Aucune opération enregistrée").pack(pady=40)

        except Exception as e:
            ctk.CTkLabel(self.__table_container_wrapper, text=f"Erreur de chargement : {e}", text_color="red").pack(
                pady=20
            )

    def __show_excel_filter_popup(self, button, col_name, bank_account_row, page, is_amount=False):
        """Affiche une fenêtre pop-up de filtre dynamique (intelligente)."""

        df_all = self.__bank_db.get_operations_by_bank_account(bank_account_row["id"])
        if df_all.empty:
            return

        # Filtre en cascade (Filtres intelligents)
        df_filtered = df_all.copy()
        df_filtered["operation_date_dt"] = pd.to_datetime(df_filtered["operation_date"], errors="coerce")
        df_filtered["year_str"] = df_filtered["operation_date_dt"].dt.year.astype(str)

        # On applique tous les filtres actifs SAUF celui de la colonne qu'on est en train d'ouvrir
        for col_k, selected_vals in self.__column_filters.items():
            if col_k == col_name:
                continue

            if col_k == "Date" and selected_vals:
                df_filtered = df_filtered[df_filtered["year_str"].isin(selected_vals)]
            elif col_k == "Libellé" and selected_vals:
                df_filtered = df_filtered[df_filtered["label"].astype(str).isin(selected_vals)]
            elif col_k == "Catégorie" and selected_vals:
                df_filtered = df_filtered[df_filtered["category"].astype(str).isin(selected_vals)]
            elif col_k == "Sous-Catégorie" and selected_vals:
                df_filtered = df_filtered[df_filtered["sub_category"].astype(str).isin(selected_vals)]
            elif col_k == "Montant" and selected_vals:
                if isinstance(selected_vals, dict):
                    op = selected_vals.get("operator")
                    target = selected_vals.get("value")
                    if op == "Supérieur ou égal (>=)":
                        df_filtered = df_filtered[df_filtered["amount"] >= target]
                    elif op == "Inférieur ou égal (<=)":
                        df_filtered = df_filtered[df_filtered["amount"] <= target]
                    elif op == "Égal (=)":
                        df_filtered = df_filtered[df_filtered["amount"] == target]
                elif isinstance(selected_vals, list):
                    df_filtered = df_filtered[df_filtered["amount"].isin(selected_vals)]

        popup_width = 280
        popup_height = 250 if is_amount else 410

        # Position de base
        x = button.winfo_rootx()

        if is_amount:
            x = button.winfo_rootx() + button.winfo_width() - popup_width

        y = button.winfo_rooty() + button.winfo_height()

        popup = ctk.CTkToplevel(button.winfo_toplevel())
        popup.wm_overrideredirect(True)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        popup.grab_set()

        main_frame = ctk.CTkFrame(popup, fg_color="gray90", corner_radius=6)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Filtre spécifique
        if is_amount:
            sort_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            sort_frame.pack(fill="x", padx=10, pady=(8, 4))

            ctk.CTkButton(
                sort_frame,
                text="Trier du plus petit au plus grand",
                anchor="w",
                fg_color="transparent",
                text_color="black",
                hover_color="gray80",
                height=22,
                font=("Arial", 11),
                command=lambda: (
                    popup.destroy(),
                    setattr(self, "_sort_column", "amount"),
                    setattr(self, "_sort_ascending", True),
                    self.__update_table_content(bank_account_row, page),
                ),
            ).pack(fill="x")

            ctk.CTkButton(
                sort_frame,
                text="Trier du plus grand au plus petit",
                anchor="w",
                fg_color="transparent",
                text_color="black",
                hover_color="gray80",
                height=22,
                font=("Arial", 11),
                command=lambda: (
                    popup.destroy(),
                    setattr(self, "_sort_column", "amount"),
                    setattr(self, "_sort_ascending", False),
                    self.__update_table_content(bank_account_row, page),
                ),
            ).pack(fill="x")

            ctk.CTkFrame(main_frame, height=1, fg_color="gray70").pack(fill="x", padx=10, pady=6)

            current_amount_filter = self.__column_filters.get("Montant", {})

            op_var = ctk.StringVar(
                value=current_amount_filter.get("operator", "Supérieur ou égal (>=)")
                if isinstance(current_amount_filter, dict)
                else "Supérieur ou égal (>=)"
            )
            op_dropdown = ctk.CTkOptionMenu(
                main_frame,
                values=["Supérieur ou égal (>=)", "Inférieur ou égal (<=)", "Égal (=)"],
                variable=op_var,
                height=28,
            )
            op_dropdown.pack(fill="x", padx=10, pady=(5, 5))

            val_var = ctk.StringVar(
                value=str(current_amount_filter.get("value", "")) if isinstance(current_amount_filter, dict) else ""
            )
            val_entry = ctk.CTkEntry(
                main_frame,
                textvariable=val_var,
                placeholder_text="Valeur (ex: 50.00)",
                height=28,
            )
            val_entry.pack(fill="x", padx=10, pady=(5, 10))

            def apply_amount_filter():
                raw_val = val_var.get().replace(",", ".").strip()
                if raw_val:
                    try:
                        target_val = float(raw_val)
                        self.__column_filters["Montant"] = {
                            "operator": op_var.get(),
                            "value": target_val,
                        }
                    except ValueError:
                        messagebox.showerror("Erreur", "Veuillez saisir un nombre valide.")
                        return
                else:
                    self.__column_filters.pop("Montant", None)

                popup.destroy()
                self.__update_table_content(bank_account_row, page)

            btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=40)
            btn_frame.pack(fill="x", padx=10, pady=10)

            ctk.CTkButton(
                btn_frame,
                text="OK",
                width=115,
                height=28,
                fg_color=self.__theme["blue_01"]["fg_color"],
                command=apply_amount_filter,
            ).pack(side="left", padx=(0, 5))

            ctk.CTkButton(
                btn_frame,
                text="Annuler",
                width=115,
                height=28,
                fg_color="gray60",
                hover_color="gray50",
                command=popup.destroy,
            ).pack(side="right", padx=(5, 0))

            return

        # Autres colonnes (Date, Libellé, Catégorie, Sous-Catégorie)
        # Extraction des valeurs uniques basées sur le DataFrame filtré
        if col_name == "Date":
            unique_values = sorted([str(x) for x in df_filtered["year_str"].dropna().unique()])
        elif col_name == "Libellé":
            unique_values = sorted([str(x) for x in df_filtered["label"].dropna().unique()])
        elif col_name == "Catégorie":
            unique_values = sorted([str(x) for x in df_filtered["category"].dropna().unique()])
        elif col_name == "Sous-Catégorie":
            unique_values = sorted([str(x) for x in df_filtered["sub_category"].dropna().unique()])
        else:
            unique_values = []

        # Options de tri pour la colonne Date
        if col_name == "Date":
            sort_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            sort_frame.pack(fill="x", padx=10, pady=(8, 4))

            ctk.CTkButton(
                sort_frame,
                text="Trier de la plus ancienne à la plus récente",
                anchor="w",
                fg_color="transparent",
                text_color="black",
                hover_color="gray80",
                height=22,
                font=("Arial", 11),
                command=lambda: (
                    popup.destroy(),
                    setattr(self, "_sort_column", "operation_date"),
                    setattr(self, "_sort_ascending", True),
                    self.__update_table_content(bank_account_row, page),
                ),
            ).pack(fill="x")
            ctk.CTkButton(
                sort_frame,
                text="Trier de la plus récente à la plus ancienne",
                anchor="w",
                fg_color="transparent",
                text_color="black",
                hover_color="gray80",
                height=22,
                font=("Arial", 11),
                command=lambda: (
                    popup.destroy(),
                    setattr(self, "_sort_column", "operation_date"),
                    setattr(self, "_sort_ascending", False),
                    self.__update_table_content(bank_account_row, page),
                ),
            ).pack(fill="x")

            ctk.CTkFrame(main_frame, height=1, fg_color="gray70").pack(fill="x", padx=10, pady=4)

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(main_frame, textvariable=search_var, placeholder_text="Rechercher", height=28)
        search_entry.pack(fill="x", padx=10, pady=(5, 5))

        scroll_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent", height=180)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Pré-sélection des éléments
        saved_selected = self.__column_filters.get(col_name, None)
        if saved_selected is not None:
            # On garde ce qui était coché et qui reste présent dans les options filtrées
            current_selected = [val for val in saved_selected if val in unique_values]
            if not current_selected:
                current_selected = unique_values
        else:
            current_selected = unique_values

        vars_dict = {}

        select_all_var = ctk.BooleanVar(value=all(val in current_selected for val in unique_values))

        def toggle_select_all():
            state = select_all_var.get()
            for v in vars_dict.values():
                v.set(state)

        select_all_cb = ctk.CTkCheckBox(
            scroll_frame, text="(Sélectionner tout)", variable=select_all_var, command=toggle_select_all
        )
        select_all_cb.pack(anchor="w", padx=5, pady=2)

        checkboxes = []
        for val in unique_values:
            v = ctk.BooleanVar(value=val in current_selected)
            vars_dict[val] = v
            display_text = str(val)
            cb = ctk.CTkCheckBox(scroll_frame, text=display_text, variable=v)
            cb.pack(anchor="w", padx=5, pady=2)
            checkboxes.append((val, cb))

        def filter_checkboxes(*args):
            query = search_var.get().lower()
            for val, cb in checkboxes:
                display_str = str(val)
                if query in display_str.lower():
                    cb.pack(anchor="w", padx=5, pady=2)
                else:
                    cb.pack_forget()

        search_var.trace("w", filter_checkboxes)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=40)
        btn_frame.pack(fill="x", padx=10, pady=10)
        btn_frame.pack_propagate(False)

        def apply_filter():
            selected = [val for val, v in vars_dict.items() if v.get()]
            # Si tout est coché, cela équivaut à réinitialiser le filtre spécifique sur cette colonne
            if len(selected) == len(unique_values):
                self.__column_filters.pop(col_name, None)
            else:
                self.__column_filters[col_name] = selected
            popup.destroy()
            self.__update_table_content(bank_account_row, page)

        ok_btn = ctk.CTkButton(
            btn_frame,
            text="OK",
            width=115,
            height=28,
            fg_color=self.__theme["blue_01"]["fg_color"],
            command=apply_filter,
        )
        ok_btn.pack(side="left", padx=(0, 5))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Annuler",
            width=115,
            height=28,
            fg_color="gray60",
            hover_color="gray50",
            command=popup.destroy,
        )
        cancel_btn.pack(side="right", padx=(5, 0))

    def __toggle_select_operation(self, operation_id: int, bank_account_row: pd.Series, page: int) -> None:
        """Ajoute ou retire une opération de la sélection multiple."""
        if operation_id in self.__selected_operation_ids:
            self.__selected_operation_ids.remove(operation_id)
        else:
            self.__selected_operation_ids.add(operation_id)
        self.__build_actions_bar(bank_account_row)

    def __toggle_select_all_page(
        self, bank_account_row: pd.Series, page: int, page_ids: list, master_cb: ctk.CTkCheckBox
    ) -> None:
        """Sélectionne ou désélectionne toutes les opérations de la page courante."""
        all_selected = all(op_id in self.__selected_operation_ids for op_id in page_ids)
        if all_selected:
            for op_id in page_ids:
                self.__selected_operation_ids.discard(op_id)
        else:
            for op_id in page_ids:
                self.__selected_operation_ids.add(op_id)
        self.__build_actions_bar(bank_account_row)
        self.__update_table_content(bank_account_row, page)

    def __handle_add_operation(self, bank_account_row: pd.Series) -> None:
        """Ouvre la fenêtre pour ajouter une nouvelle opération."""

        default_op = {
            "id": None,
            "operation_date": datetime.now().strftime("%Y-%m-%d"),
            "label": "",
            "amount": "0.00",
            "category": "",
            "sub_category": "",
        }

        win = OperationEditWindow(
            parent=self.__master,
            db=self.__bank_db,
            bank_account_id=bank_account_row["id"],
            operation=default_op,
            on_save_callback=lambda data: self.__process_add(data, bank_account_row),
        )
        win.title("Ajouter une opération")

    def __handle_delete_selected_operations(self, bank_account_row: pd.Series) -> None:
        """Gère la suppression groupée des opérations sélectionnées."""
        if not self.__selected_operation_ids:
            return

        if not messagebox.askyesno(
            "Confirmation",
            f"Souhaitez-vous vraiment supprimer les {len(self.__selected_operation_ids)} opération(s) sélectionnée(s) ?",
        ):
            return

        loading_win = LoadingPopup(self.__master, "Suppression en cours...")

        def task():
            try:
                for op_id in list(self.__selected_operation_ids):
                    self.__bank_db.delete_operation(bank_account_row["id"], op_id)
                self.__selected_operation_ids.clear()
                self.update_bilan(bank_account_row["id"], bank_account_row["name"])
            except Exception:
                self.__master.after(0, lambda: messagebox.showerror("Erreur", "Erreur lors de la suppression groupée"))
            finally:
                self.__master.after(0, lambda: self.__on_process_complete(loading_win, bank_account_row))

        threading.Thread(target=task, daemon=True).start()

    def __handle_edit_operation(self, operation: pd.Series, bank_account_row: pd.Series) -> None:
        """Ouvre la fenêtre de modification pour une opération donnée."""

        OperationEditWindow(
            self.__master,
            self.__bank_db,
            bank_account_row["id"],
            operation,
            lambda data: self.__process_update(data, bank_account_row),
        )

    def __handle_attachments_modal(self, operation: pd.Series, bank_account_row: pd.Series, page: int) -> None:
        """Ouvre une fenêtre modale élégante et agrandie pour gérer les pièces justificatives avec affichage de la date, du début du libellé, du montant et des catégories."""
        currency_symbol = self.__bank_db.get_bank_account_currency_symbol(bank_account_row["id"])

        att_win = ctk.CTkToplevel(self.__master)
        att_win.title("Gestion des pièces justificatives")

        # Définition de la taille et centrage au milieu de l'écran
        width, height = 940, 530
        att_win.geometry(f"{width}x{height}")
        att_win.minsize(width, height)
        center_window_on_screen(att_win, width, height, 2)

        att_win.grab_set()

        # En-tête stylisé avec informations condensées de l'opération
        header_card = ctk.CTkFrame(att_win, fg_color="gray85", corner_radius=10)
        header_card.pack(fill="x", padx=25, pady=20)

        ctk.CTkLabel(header_card, text="Pièces justificatives de l'opération", font=("Arial", 16, "bold")).pack(
            anchor="w", padx=15, pady=(12, 5)
        )

        # Extraction du libellé sans ajouter "..." si sa longueur ne dépasse pas la limite
        full_label = str(operation.get("label", ""))
        max_chars = 70
        short_label = full_label if len(full_label) <= max_chars else (full_label[:max_chars] + "...")

        amt = operation.get("amount", 0.0)
        formatted_amt = f"{amt:,.2f}".replace(",", " ") + f" {currency_symbol}"
        amt_color = self.__theme["red"]["fg_color"] if amt < 0 else self.__theme["green"]["fg_color"]

        # Première ligne d'informations (Date, Montant, Libellé avec libellés en gras)
        info_row_1 = ctk.CTkFrame(header_card, fg_color="transparent")
        info_row_1.pack(fill="x", padx=15, pady=(0, 6))

        # Date
        ctk.CTkLabel(info_row_1, text="Date :", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkLabel(info_row_1, text=f"{operation.get('operation_date', '')}", font=("Arial", 13)).pack(
            side="left", padx=(4, 15)
        )

        # Montant
        ctk.CTkLabel(info_row_1, text="Montant :", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkLabel(info_row_1, text=f"{formatted_amt}", font=("Arial", 13, "bold"), text_color=amt_color).pack(
            side="left", padx=(4, 15)
        )

        # Libellé
        ctk.CTkLabel(info_row_1, text="Libellé :", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkLabel(info_row_1, text=f"{short_label}", font=("Arial", 13)).pack(side="left", padx=(4, 0))

        # Deuxième ligne d'informations (Catégorie et Sous-catégorie avec libellés en gras)
        category_val = operation.get("category")
        sub_category_val = operation.get("sub_category")

        cat_display = category_val if (category_val and str(category_val).strip()) else "Non catégorisé"
        subcat_display = sub_category_val if (sub_category_val and str(sub_category_val).strip()) else "Non catégorisé"

        info_row_2 = ctk.CTkFrame(header_card, fg_color="transparent")
        info_row_2.pack(fill="x", padx=15, pady=(0, 12))

        # Catégorie
        ctk.CTkLabel(info_row_2, text="Catégorie :", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkLabel(info_row_2, text=f"{cat_display}", font=("Arial", 13)).pack(side="left", padx=(4, 20))

        # Sous-catégorie
        ctk.CTkLabel(info_row_2, text="Sous-catégorie :", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkLabel(info_row_2, text=f"{subcat_display}", font=("Arial", 13)).pack(side="left", padx=(4, 0))

        # Commentaire de l'opération
        raw_comment = operation.get("comment", "")
        comment_display = "" if raw_comment is None or str(raw_comment).lower() == "nan" else str(raw_comment)

        info_row_3 = ctk.CTkFrame(header_card, fg_color="transparent")
        info_row_3.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(info_row_3, text="Commentaire :", font=("Arial", 13, "bold")).pack(side="left", anchor="n")

        comment_textbox = ctk.CTkTextbox(info_row_3, height=55, wrap="word")
        comment_textbox.insert("1.0", comment_display)
        comment_textbox.configure(state="disabled")
        comment_textbox.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Conteneur principal de la liste des fichiers
        list_frame = ctk.CTkScrollableFrame(att_win, width=580, height=220, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        self.__refresh_list(operation["id"], list_frame, bank_account_row, page)

        footer_frame = ctk.CTkFrame(att_win, fg_color="transparent")
        footer_frame.pack(fill="x", padx=25, pady=(0, 20))

        ctk.CTkButton(
            footer_frame,
            text="+ Ajouter un fichier",
            height=35,
            font=("Arial", 13, "bold"),
            fg_color=self.__theme["green"]["fg_color"],
            hover_color=self.__theme["green"]["hover_color"],
            command=lambda: self.__add_file(operation["id"], list_frame, bank_account_row, page),
        ).pack(fill="x")

    def __refresh_list(self, op_id: int, list_frame: ctk.CTkScrollableFrame, bank_account_row: pd.Series, page: int):
        for w in list_frame.winfo_children():
            w.destroy()

        attachments = self.__bank_db.get_operation_attachments(op_id)
        if not attachments:
            empty_lbl = ctk.CTkLabel(
                list_frame,
                text="Aucun document rattaché pour le moment.",
                font=("Arial", 13, "italic"),
                text_color="gray50",
            )
            empty_lbl.pack(pady=30)
            return

        for att in attachments:
            row = ctk.CTkFrame(list_frame, fg_color="gray90", height=45, corner_radius=6)
            row.pack(fill="x", pady=4)
            row.pack_propagate(False)

            full_name = att["file_name"]
            max_len = 35
            display_name = (full_name[:max_len] + "...") if len(full_name) > max_len else full_name

            ctk.CTkLabel(row, text=display_name, anchor="w", font=("Arial", 13)).pack(side="left", padx=15)

            # Correction de l'appel à __refresh_list avec ses arguments dans le bouton Supprimer
            ctk.CTkButton(
                row,
                text="Supprimer",
                width=80,
                height=26,
                fg_color=self.__theme["red"]["fg_color"],
                hover_color=self.__theme["red"]["hover_color"],
                command=lambda aid=att["id"]: (
                    self.__bank_db.delete_operation_attachment(aid),
                    self.__refresh_list(op_id, list_frame, bank_account_row, page),
                    self.__update_table_content(bank_account_row, page),
                ),
            ).pack(side="right", padx=8)

            ctk.CTkButton(
                row,
                text="Télécharger",
                width=95,
                height=26,
                fg_color=self.__theme["blue_01"]["fg_color"],
                hover_color=self["blue_01"]["hover_color"]
                if hasattr(self, "__theme")
                else "blue",  # Ajustez selon votre code
                command=lambda aid=att["id"]: self.__download_attachment(aid),
            ).pack(side="right", padx=2)

            ctk.CTkButton(
                row,
                text="Aperçu",
                width=70,
                height=26,
                fg_color="gray50",
                hover_color="gray40",
                command=lambda aid=att["id"]: self.__preview_attachment(aid),
            ).pack(side="right", padx=2)

    def __add_file(self, op_id: int, list_frame: ctk.CTkScrollableFrame, bank_account_row: pd.Series, page: int):
        file_path = filedialog.askopenfilename(title="Sélectionner un fichier justificatif")
        if file_path:
            path_obj = Path(file_path)
            with open(path_obj, "rb") as f:
                file_bytes = f.read()
            self.__bank_db.add_operation_attachment(op_id, file_bytes, path_obj.name, path_obj.suffix)
            self.__refresh_list(op_id, list_frame, bank_account_row, page)
            self.__update_table_content(bank_account_row, page)

    def __download_attachment(self, attachment_id: int) -> None:
        """Permet de télécharger et d'enregistrer le fichier binaire sur le disque."""
        data = self.__bank_db.get_operation_attachment_data(attachment_id)
        if not data:
            messagebox.showerror("Erreur", "Fichier introuvable.")
            return

        save_path = filedialog.asksaveasfilename(initialfile=data["file_name"])
        if save_path:
            with open(save_path, "wb") as f:
                f.write(data["file_data"])
            messagebox.showinfo("Succès", "Fichier téléchargé avec succès.")

    def __preview_attachment(self, attachment_id: int) -> None:
        """Ouvre un aperçu rapide du fichier binaire via un fichier temporaire."""
        data = self.__bank_db.get_operation_attachment_data(attachment_id)
        if not data:
            messagebox.showerror("Erreur", "Fichier introuvable.")
            return

        suffix = Path(data["file_name"]).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data["file_data"])
            tmp_path = tmp.name

        try:
            if os.name == "nt":
                os.startfile(tmp_path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'aperçu : {e}")

    def __handle_import_process(self, bank_account_row: pd.Series) -> None:
        """Lance l'extraction, gère les doublons avec confirmation utilisateur et injecte les données."""

        extractor = DataExtractor(bank_account_row["id"], self.__master)
        df = extractor.run_extraction()

        if df is None or df.empty:
            return

        df["bank_account_id"] = bank_account_row["id"]
        existing_ops = self.__bank_db.get_operations_by_bank_account(bank_account_row["id"])

        if not existing_ops.empty:
            # Création des clés uniques de comparaison
            existing_ops["match_key"] = (
                existing_ops["operation_date"].astype(str)
                + "_"
                + existing_ops["label"].astype(str).str.strip()
                + "_"
                + existing_ops["amount"].astype(float).round(2).astype(str)
            )

            df["match_key"] = (
                df["operation_date"].astype(str)
                + "_"
                + df["label"].astype(str).str.strip()
                + "_"
                + df["amount"].astype(float).round(2).astype(str)
            )

            # Identification des doublons
            duplicates_mask = df["match_key"].isin(existing_ops["match_key"])
            nb_duplicates = duplicates_mask.sum()

            if nb_duplicates > 0:
                # Demande de confirmation à l'utilisateur
                import_duplicates = messagebox.askyesno(
                    "Doublons détectés",
                    f"{nb_duplicates} opération(s) importée(s) semble(nt) déjà exister dans la base de données.\n\n"
                    "Souhaitez-vous quand même les importer ?",
                )

                # Si l'utilisateur choisit Non (False), on retire les doublons du DataFrame
                if not import_duplicates:
                    df = df[~duplicates_mask]

            # Nettoyage de la colonne temporaire de clé
            df = df.drop(columns=["match_key"])

        if df.empty:
            messagebox.showinfo("Importation", "Aucune nouvelle opération n'a été ajoutée.")
            return

        loading_win = LoadingPopup(self.__master, "Importation des données en cours...")

        def task():
            try:
                self.__bank_db.add_operations(df)
                self.__master.after(0, lambda: self.__process_categorization(bank_account_row, loading_win))

            except Exception as e:
                self.__master.after(0, lambda err=e: self.__on_import_error(err, loading_win))

        threading.Thread(target=task, daemon=True).start()

    def __process_categorization(self, bank_account_row: pd.Series, loading_win: LoadingPopup) -> None:
        """Ferme la barre de chargement et ouvre la catégorisation."""
        if loading_win and loading_win.winfo_exists():
            loading_win.close()

        try:
            categorizer = Categorizer(self.__master, self.__bank_db, bank_account_row["id"])
            cat_window = categorizer.categorize()

            if cat_window and cat_window.winfo_exists():
                self.__master.wait_window(cat_window)

            self.update_bilan(bank_account_row["id"], bank_account_row["name"])
            self.__controller.show_bank_operations(bank_account_row)
            self.__on_import_success(bank_account_row, None)

        except Exception as e:
            self.__on_import_error(e, None)

    def __on_import_success(self, bank_account_row: pd.Series, loading_win: LoadingPopup | None) -> None:
        """Rappel exécuté sur le thread principal en cas de succès."""
        if loading_win is not None and loading_win.winfo_exists():
            loading_win.close()

        messagebox.showinfo(
            "Succès",
            f"Données importées avec succès pour le compte : {bank_account_row['name']}",
        )

    def __on_import_error(self, error: Exception, loading_win: LoadingPopup | None) -> None:
        """Rappel exécuté sur le thread principal en cas d'erreur."""
        if loading_win is not None and loading_win.winfo_exists():
            loading_win.close()

        messagebox.showerror("Erreur", f"Erreur lors de l'insertion : {error}")

    def __handle_categorization_process(self, bank_account_row: pd.Series) -> None:
        """Lance le processus de catégorisation."""

        try:
            categorizer = Categorizer(self.__master, self.__bank_db, bank_account_row["id"])
            cat_window = categorizer.categorize()

            if cat_window and cat_window.winfo_exists():
                self.__master.wait_window(cat_window)

            if categorizer.has_changed:
                loading_win = LoadingPopup(self.__master, "Ajout en cours...")

                def task():
                    try:
                        self.update_bilan(bank_account_row["id"], bank_account_row["name"])
                    except Exception:
                        self.__master.after(
                            0, lambda: messagebox.showerror("Erreur", "Erreur lors de la catégorisation")
                        )
                    finally:
                        self.__master.after(0, lambda: self.__on_process_complete(loading_win, bank_account_row))

                threading.Thread(target=task, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la catégorisation : {e}")

    def __process_add(self, new_operation: dict, bank_account_row: pd.Series) -> None:
        """Met à jour la base de données et rafraîchit l'affichage."""
        loading_win = LoadingPopup(self.__master, "Ajout en cours...")

        def task():
            try:
                df = pd.DataFrame([new_operation])
                self.__bank_db.add_operations(df)
                self.update_bilan(bank_account_row["id"], bank_account_row["name"])
            except Exception:
                self.__master.after(0, lambda: messagebox.showerror("Erreur", "Erreur lors de l'ajout"))
            finally:
                self.__master.after(0, lambda: self.__on_process_complete(loading_win, bank_account_row))

        threading.Thread(target=task, daemon=True).start()

    def __process_update(self, updated_data: dict, bank_account_row: pd.Series) -> None:
        """Met à jour la base de données et rafraîchit l'affichage."""
        loading_win = LoadingPopup(self.__master, "Modification en cours...")

        def task():
            try:
                self.__bank_db.update_operation(bank_account_row["id"], updated_data)
                self.update_bilan(bank_account_row["id"], bank_account_row["name"])
            except Exception:
                self.__master.after(0, lambda: messagebox.showerror("Erreur", "Erreur lors de la mise à jour"))
            finally:
                self.__master.after(0, lambda: self.__on_process_complete(loading_win, bank_account_row))

        threading.Thread(target=task, daemon=True).start()

    def __on_process_complete(self, loading_win: LoadingPopup, bank_account_row: pd.Series) -> None:
        loading_win.close()
        self.__controller.show_bank_operations(bank_account_row)

    def update_bilan(self, bank_account_id: int | None = None, bank_account_name: str | None = None) -> None:
        """Coordonne la mise à jour complète des fichiers bilan pour un compte bancaire."""
        paths = []
        base_dest = Path(self.__config["destination_path"])
        heritage_path = base_dest / "heritage" / "heritage_bank"
        paths.append(heritage_path)
        paths.append(base_dest / "heritage" / "heritage_global.html")
        paths.append(base_dest / "heritage" / "heritage_global.xlsx")

        if bank_account_id is not None:
            bank_path = base_dest / "bank_account" / bank_account_name
            paths.append(bank_path)

        # Nettoyage des répertoires existants
        for path in paths:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

        # Génération des graphiques et rapports Excel
        if bank_account_id is not None:
            chart_generate_all_reports(self.__bank_db, self.__stock_db, bank_path, bank_account_id)
            excel_generate_all_reports(self.__bank_db, self.__stock_db, bank_path, bank_account_id)

        chart_generate_all_reports(self.__bank_db, self.__stock_db, heritage_path)
        excel_generate_all_reports(self.__bank_db, self.__stock_db, heritage_path)
        calculate_heritage(self.__bank_db, self.__stock_db)
