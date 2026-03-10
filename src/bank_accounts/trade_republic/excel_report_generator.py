import os
from datetime import datetime

import pandas as pd
import xlsxwriter

from database.trade_republic_database import TradeRepublicDatabase


class ExcelReportGenerator(TradeRepublicDatabase):
    """
    Générateur de rapports d'investissements Excel.
    
    Analyse les performances du portefeuille, calcule les plus-values réalisées
    et suit l'évolution annuelle des capitaux investis et de leur rentabilité.
    """

    def __init__(self, db_path: str, root_path: str):
        """
        Initialise le générateur de rapport d'investissement.
        
        Args:
            - db_path (str) : Chemin vers la base de données Trade Republic.
            - root_path (str) : Dossier de destination des rapports.
        """
        super().__init__(db_path)
        self.__root_path = os.path.abspath(root_path)


    # --- [ Configuration des Styles ] ---
    def __get_formats(self, wb):
        """
        Définit la charte graphique des rapports d'investissement.
        """
        return {
            'header': wb.add_format({'bold': True, 'bg_color': '#1f77b4', 'font_color': 'white', 'border': 1, 'align': 'center'}),
            'currency': wb.add_format({'num_format': '#,##0.00 €', 'border': 1}),
            'percent': wb.add_format({'num_format': '0.00%', 'border': 1, 'align': 'center'}),
            'date': wb.add_format({'num_format': 'dd/mm/yyyy', 'border': 1, 'align': 'center'}),
            'gain': wb.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE', 'num_format': '#,##0.00 €', 'border': 1}),
            'loss': wb.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'num_format': '#,##0.00 €', 'border': 1}),
            'title': wb.add_format({'bold': True, 'font_size': 14, 'font_color': '#1f77b4'}),
            'std': wb.add_format({'border': 1}),
            'center': wb.add_format({'align': 'center', 'border': 1})
        }


    # --- [ Analyse des Plus-values ] ---
    def __get_capital_gains_data(self) -> pd.DataFrame:
        """Calcule les plus-values réelles en suivant l'état des stocks d'actions."""
        df = self._get_transactions_in_eur()
        df = df.sort_index()  # Tri chronologique obligatoire

        # Dictionnaires pour suivre l'état par ticker
        stock_quantities = {}  # { 'AAPL': quantité_actuelle }
        invested_amounts = {}  # { 'AAPL': coût_total_du_stock_actuel }
        
        realized_gains = []

        for timestamp, row in df.iterrows():
            ticker = row['ticker']
            qty = row['quantity']
            amount = abs(row['amount'])
            fees = row['fees']
            
            if ticker not in stock_quantities:
                stock_quantities[ticker] = 0
                invested_amounts[ticker] = 0

            if row['operation'] == 'buy':
                # On ajoute les actions et le prix payé (frais inclus dans l'investissement)
                stock_quantities[ticker] += qty
                invested_amounts[ticker] += (amount + fees)
                
            elif row['operation'] == 'sell' and stock_quantities[ticker] > 0:
                # Calcul du PRU (Prix de Revient Unitaire) avant la vente
                pru_unitaire = invested_amounts[ticker] / stock_quantities[ticker]
                
                # Coût d'acquisition de la part vendue
                acquisition_cost = pru_unitaire * qty
                
                # Plus-value = Argent reçu - Coût d'acquisition - Frais de vente
                # amount ici est l'argent récupéré (V)
                gain = amount - acquisition_cost - fees
                
                realized_gains.append({
                    'date': timestamp,
                    'ticker': ticker,
                    'quantity': qty,
                    'sell_price': amount,
                    'cost_basis': acquisition_cost,
                    'fees': fees,
                    'net_gain': gain
                })
                
                # Mise à jour du stock restant
                stock_quantities[ticker] -= qty
                invested_amounts[ticker] -= acquisition_cost
                
                # Sécurité : Si tout est vendu, on nettoie pour éviter les résidus flottants
                if stock_quantities[ticker] <= 0:
                    stock_quantities[ticker] = 0
                    invested_amounts[ticker] = 0

        return pd.DataFrame(realized_gains)


    # --- [ Génération du Rapport ] ---
    def generate_investment_report(self):
        """Génère le fichier Excel multi-feuilles de suivi d'investissement"""
        file_path = os.path.join(self.__root_path, "Bilan_Investissements.xlsx")
        os.makedirs(self.__root_path, exist_ok=True)
        
        wb = xlsxwriter.Workbook(file_path)
        fmt = self.__get_formats(wb)

        self.__add_gains_sheet(wb, fmt)
        self.__add_performance_dividend_sheet(wb, fmt)
        self.__add_annual_summary_sheet(wb, fmt)

        wb.close()

    def __add_gains_sheet(self, wb, fmt: dict):
        """Ajoute la feuille de détail des plus-values avec un tableau Excel"""
        ws = wb.add_worksheet("Plus-values Réalisées")
        data = self.__get_capital_gains_data()

        if data.empty:
            ws.write(0, 0, "Aucune vente réalisée", fmt['header'])
            return

        headers = ["Date", "Action", "Quantité", "Prix Vente", "Coût Achat", "Frais", "Plus-value"]
        
        # Préparation des données pour le tableau
        table_data = []
        for _, item in data.iterrows():
            dt_obj = item['date'].to_pydatetime() if hasattr(item['date'], 'to_pydatetime') else item['date']
            table_data.append([
                dt_obj, 
                item['ticker'], 
                item['quantity'], 
                item['sell_price'], 
                item['cost_basis'], 
                item['fees'], 
                item['net_gain']
            ])

        # Définition de la zone du tableau
        last_row = len(table_data)
        last_col = len(headers) - 1

        # Ajout du tableau
        ws.add_table(0, 0, last_row, last_col, {
            'name': 'TableGainsRealises',
            'data': table_data,
            'columns': [{'header': h, 'header_format': fmt['header']} for h in headers],
            'style': None
        })

        # On repasse sur les cellules pour appliquer les formats monétaires et conditionnels
        for row_idx in range(1, last_row + 1):
            val_gain = table_data[row_idx-1][6]
            ws.write_datetime(row_idx, 0, table_data[row_idx-1][0], fmt['date'])
            ws.write(row_idx, 1, table_data[row_idx-1][1], fmt['header'])
            ws.write(row_idx, 2, table_data[row_idx-1][2], fmt['currency'])
            ws.write(row_idx, 3, table_data[row_idx-1][3], fmt['currency'])
            ws.write(row_idx, 4, table_data[row_idx-1][4], fmt['currency'])
            ws.write(row_idx, 5, table_data[row_idx-1][5], fmt['currency'])
            
            # Format conditionnel
            cell_fmt = fmt['gain'] if val_gain >= 0 else fmt['loss']
            ws.write(row_idx, 6, val_gain, cell_fmt)

        ws.set_column('A:G', 16)

    def __add_annual_summary_sheet(self, wb, fmt: dict):
        """Ajoute la feuille de résumé annuel sous forme de tableau Excel"""
        ws = wb.add_worksheet("Synthèse Annuelle")
        df = self._get_transactions_in_eur()
        
        df['year'] = df.index.year
        df['val_buy'] = df.apply(lambda r: r['amount'] if r['operation'] == 'buy' else 0, axis=1)
        df['val_sell'] = df.apply(lambda r: r['amount'] if r['operation'] == 'sell' else 0, axis=1)

        summary = df.groupby('year').agg(
            investi=('val_buy', 'sum'),
            retire=('val_sell', 'sum'),
            frais=('fees', 'sum')
        ).reset_index()

        headers = ["Année", "Total Investi", "Total Retiré", "Frais Payés", "Évolution %"]
        
        # Préparation des lignes (on laisse la 5ème colonne vide pour la formule)
        table_rows = []
        for _, row in summary.iterrows():
            table_rows.append([row['year'], row['investi'], row['retire'], row['frais'], 0])

        last_row = len(table_rows)
        
        ws.add_table(0, 0, last_row, 4, {
            'name': 'TableSummary',
            'data': table_rows,
            'columns': [{'header': h, 'header_format': fmt['header']} for h in headers],
            'style': None,
            'total_row': True # Optionnel : ajoute une ligne de total en bas
        })

        # Application des formats et formules
        for row_idx in range(1, last_row + 1):
            ws.write(row_idx, 0, table_rows[row_idx-1][0], fmt['header'])
            ws.write(row_idx, 1, table_rows[row_idx-1][1], fmt['currency'])
            ws.write(row_idx, 2, table_rows[row_idx-1][2], fmt['currency'])
            ws.write(row_idx, 3, table_rows[row_idx-1][3], fmt['currency'])
            
            # Formule d'évolution
            if row_idx > 1:
                ws.write_formula(row_idx, 4, f"=(B{row_idx+1}-B{row_idx})/B{row_idx}", fmt['percent'])
            else:
                ws.write(row_idx, 4, 0, fmt['percent'])

        ws.set_column('A:E', 18)

    def __add_performance_dividend_sheet(self, wb, fmt: dict):
        """Ajoute la feuille de performance globale par actif (PRU, Div, Détention)"""
        ws = wb.add_worksheet("Performance & Dividendes")
        df = self._get_transactions_in_eur()
        if df.empty:
            return

        performance_list = []
        tickers = df['ticker'].dropna().unique()

        # Logique PRU et Dividendes
        for ticker in tickers:
            t_df = df[df['ticker'] == ticker].sort_index()
            qty, total_cost, first_date = 0, 0, t_df.index.min()
            total_div = t_df[t_df['operation'] == 'dividend']['amount'].sum()

            for _, row in t_df.iterrows():
                if row['operation'] == 'buy':
                    qty += row['quantity']
                    total_cost += (row['amount'] + row['fees'])
                elif row['operation'] == 'sell' and qty > 0:
                    pru_at_time = total_cost / qty
                    qty -= row['quantity']
                    total_cost -= (pru_at_time * row['quantity'])

            days = (datetime.now() - first_date).days
            pru_final = (total_cost / qty) if qty > 0 else 0
            performance_list.append([ticker, float(total_div), int(days), float(pru_final)])

        headers = ["Ticker", "Total Dividendes", "Détention (Jours)", "PRU Actuel"]
        ws.add_table(0, 0, len(performance_list), 3, {
            'name': 'TableSyntheseAnnuelle',
            'data': performance_list,
            'columns': [{'header': h, 'header_format': fmt['header']} for h in headers],
            'style': 'Table Style Light 9'
        })

        for i, row_data in enumerate(performance_list, 1):
            ws.write(i, 0, row_data[0], fmt['header'])
            ws.write(i, 1, row_data[1], fmt['currency'])
            ws.write(i, 2, row_data[2], fmt['center'])
            ws.write(i, 3, row_data[3], fmt['currency'])

        ws.set_column('A:D', 20)
