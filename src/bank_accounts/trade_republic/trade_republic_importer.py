import io
import os
import re
from datetime import date, datetime
from difflib import SequenceMatcher

import pandas as pd

from bank_accounts.trade_republic.execution_date_validator import (
    ExecutionDateValidator,
)
from database.trade_republic_database import TradeRepublicDatabase


class TradeRepublicImporter(TradeRepublicDatabase):
    """
    Cette classe orchestre le pipeline ETL (Extract, Transform, Load) pour les documents 
    financiers de Trade Republic. Elle assure la transition entre des fichiers PDF bruts 
    et une base de données structurée.

    La classe gère le scan récursif des répertoires, l'extraction de texte par expressions 
    régulières (Regex), le renommage intelligent des fichiers physiques, la résolution 
    des tickers par similarité textuelle et la persistance des transactions.

    Attributs:
        DATA_FILE (str): Chemin racine vers le dossier contenant les fichiers PDF.
        SOURCE_DIRECTORIES (tuple): Liste des sous-dossiers thématiques à scanner 
                                     (buy, sell, dividend, etc.).
        TICKERS_MAPPING (dict): Dictionnaire de correspondance entre les noms 
                                d'entreprises textuels et leurs symboles boursiers (tickers).
    """
    # Chemin racine vers les fichiers PDF
    DATA_FILE = 'data/Bourse/pdf/'
    
    # Liste immuable des dossiers correspondant aux catégories de transactions
    SOURCE_DIRECTORIES = (
        'buy', 
        'sell', 
        'dividend', 
        'interest', 
        'deposit', 
        'withdrawal', 
        # 'purchase_costs', 
        # 'sales_costs'
    )

    TICKERS_MAPPING = {
        'Hermes': 'RMS.PA',
        'Air Liquide': 'AI.PA',
        'TotalEnergies': 'TTE.PA',
        "L'Oréal": 'OR.PA',
        "L'Oreal": 'OR.PA',
        'ACCOR': 'AC.PA',
        'Danone': 'BN.PA',
        'Pernod Ricard': 'RI.PA',
        'LVMH': 'MC.PA',
        'Sodexo': 'SW.PA',
        'Schneider Electric': 'SU.PA',
        'Capgemini': 'CAP.PA',
        'Cap gemini': 'CAP.PA',
        'iShares Physical Metals PLC': 'PHYMF',
        'iShs VII-Core S&P': 'CSPX.L',
        'AbbVie': 'ABBV',
        'Alphabet': 'GOOGL',
        'Salesforce': 'CRM',
        'Amazon': 'AMZN',
        'Amazon.com': 'AMZN',
        'Apple': 'AAPL',
        'Arista Networks': 'ANET',
        'Blackrock': 'BLK',
        'Broadcom': 'AVGO',
        'Cadence Design Systems': 'CDNS',
        'Coca-Cola': 'KO',
        'Meta Platforms': 'META',
        'Fortinet': 'FTNT',
        'Intuit': 'INTU',
        'Johnson & Johnson': 'JNJ',
        'KLA Corp': 'KLAC',
        'KLA-Tencor': 'KLAC',
        'Lam Research': 'LRCX',
        'Eli Lilly': 'LLY',
        'Mastercard': 'MA',
        "McDonald's": 'MCD',
        'Microsoft': 'MSFT',
        'Novo Nordisk': 'NVO',
        'Novo-Nordisk AS': 'NVO',
        'NVIDIA': 'NVDA',
        'Oracle': 'ORCL',
        'Palo Alto Networks': 'PANW',
        'PepsiCo': 'PEP',
        'Procter & Gamble': 'PG',
        'Roper Technologies': 'ROP',
        'S&P Global': 'SPGI',
        'Synopsys': 'SNPS',
        'UnitedHealth': 'UNH',
        'VISA': 'V',
        'Walmart': 'WMT',
        'Cintas': 'CTAS',
        'Pluxee': 'PLX.PA',
    }

    def __init__(self, db_path: str):
        """
        Initialise la base de données.

        Args:
            - db_path (str) : Chemin vers le fichier de base de données SQLite.
        """
        super().__init__(db_path)


    # --- [ Pipeline Principal ] ---
    def run_full_import_process(self):
        """
        Lance le cycle complet : importation des nouveaux fichiers, 
        renommage physique et extraction des données financières.
        """
        # 1. Scanner et importer les fichiers PDF (renommage inclus)
        self.__import_all_pdfs()

        # 2. Traiter les fichiers non marqués comme 'processed' dans la base
        self.__process_unprocessed_files()

        # 3 Mets à jour les données dans les différentes tables pour chaque ticker
        tickers = self._get_all_company_tickers() + ['EURUSD=X']
        self._fetch_and_update_companies(tickers)

    def __process_unprocessed_files(self):
        """
        Récupère les contenus binaires des PDF non traités et 
        exécute les méthodes de traitement appropriées.
        """
        # On récupère maintenant une liste contenant l'ID et le BLOB (bytes)
        unprocessed_data = self._get_unprocessed_files()

        if not unprocessed_data:
            return

        # Regroupement par catégorie : on stocke des dictionnaires {id, content}
        categorized_items = {}
        for entry in unprocessed_data:
            cat = entry['table_associee']
            if cat not in categorized_items:
                categorized_items[cat] = []
            
            # On conserve l'ID pour pouvoir marquer comme traité plus tard
            categorized_items[cat].append({
                'id': entry['id'],
                'content': entry['content']
            })

        for category, items in categorized_items.items():
            # On extrait juste la liste des contenus binaires pour le processeur
            blobs = [item['content'] for item in items]
            
            # Le dispatcher doit maintenant envoyer des blobs
            df = self.__dispatch_to_processor(category, blobs)

            # Si on obtient un data Frame non vide alors on l'enregistre dans la table operation
            if df is not None and not df.empty:
                # Regrouper les opérations pour les mêmes dates
                df = self.__aggregate_transactions(df)

                if category in ['buy', 'sell']:
                    # On utilise le validateur pour vérifier/corriger les dates avant insertion pour les achats et les ventes
                    # Les noms de colonnes doivent correspondre à votre structure de DataFrame
                    date_validator = ExecutionDateValidator(data=df)
                    df = date_validator.run()

                # On assure la présence de chaque ticker unique en base
                self._fetch_and_update_companies(list(df['ticker'].dropna().unique()))

                # Une fois les entreprises créées, on insère les transactions
                self._insert_transactions_from_df(df)

            # Marquer le fichier comme traité en utilisant l'ID unique de la base
            for item in items:
                self._mark_file_as_processed(item['id'])
        
    def __dispatch_to_processor(self, category: str, pdf_blobs: list) -> pd.DataFrame:
        """
        Aiguille les contenus binaires des PDF vers la méthode de traitement appropriée.

        Args:
            category (str): Le type de document (ex: 'buy', 'dividend').
            pdf_blobs (list): Liste des objets bytes (BLOB) extraits de la base de données.

        Returns:
            pd.DataFrame: Les données extraites structurées, ou None pour les documents informatifs.
        """
        if category == 'deposit':
            return self.__process_deposit_data(pdf_blobs)
        elif category == 'dividend':
            return self.__process_dividend_data(pdf_blobs)
        elif category == 'interest':
            return self.__process_interest_data(pdf_blobs)
        elif category == 'buy':
            return self.__process_order_buy_data(pdf_blobs)
        elif category == 'sell':
            return self.__process_order_sell_data(pdf_blobs)
            
        return None


    # --- [ Importation & Renommage Physique ] ---
    def __import_all_pdfs(self):
        """
        Parcourt les dossiers sources, importe les fichiers en base de données
        et les renomme selon leur contenu.
        """
        if not os.path.exists(self.DATA_FILE):
            raise FileNotFoundError(f"Répertoire racine inaccessible : {self.DATA_FILE}")

        for folder_name in self.SOURCE_DIRECTORIES:
            folder_path = os.path.join(self.DATA_FILE, folder_name)

            if not os.path.exists(folder_path):
                print(f"Avertissement : Le dossier {folder_path} n'existe pas. Passage au suivant.")
                continue

            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith('.pdf'):
                    full_path = os.path.join(folder_path, file_name)
                    
                    # 1. Insertion en base de données
                    # On stocke d'abord pour vérifier si c'est un doublon binaire
                    result = self._insert_pdf_to_database(
                        file_path=full_path,
                        table_name=folder_name
                    )

                    # 2. Renommage physique du fichier si l'insertion a réussi ou si le fichier est nouveau
                    # On ne renomme que si result != -1 (pas un doublon binaire déjà en base)
                    if result != -1:
                        self.__trigger_file_renaming(full_path, folder_path, folder_name)

    def __trigger_file_renaming(self, file_path: str, folder_path: str, category: str):
        """
        Oriente le fichier vers la bonne méthode de renommage selon sa catégorie.

        Args:
            file_path (str): Chemin complet du fichier.
            folder_path (str): Dossier contenant le fichier.
            category (str): Type de transaction (nom du dossier).
        """
        if category in ('deposit', 'withdrawal', 'interest'):
            self.__rename_cash_operation(file_path, folder_path)
        
        elif category == 'dividend':
            self.__rename_dividend_file(file_path, folder_path)
        
        elif category in ('buy', 'purchase_costs'):
            self.__rename_order_file(file_path, folder_path, is_buy_order=True)
        
        elif category in ('sell', 'sales_costs'):
            self.__rename_order_file(file_path, folder_path, is_buy_order=False)

    def __rename_cash_operation(self, file_path: str, folder_path: str):
        """
        Renomme un fichier de dépôt, retrait ou intérêt basé sur la date extraite.

        Args:
            file_path (str): Chemin actuel du fichier.
            folder_path (str): Dossier où se trouve le fichier.
        """
        # Extraction du texte (méthode protégée supposée existante)
        pdf_text = self.__extract_pdf_text(file_path)
        
        # Extraction et formatage de la date
        raw_date = self.__regex_extract(pdf_text, r'DATE ((\d{2}/\d{2}/\d{4})|(\d{2}.\d{2}.\d{4}))', 1).replace('.', '/')
        formatted_date = datetime.strptime(raw_date, '%d/%m/%Y').strftime('%Y-%m-%d')

        target_path = self.__get_unique_path(folder_path, formatted_date)
        
        try:
            os.rename(file_path, target_path)
        except Exception as error:
            raise RuntimeError(f"Impossible de renommer le fichier de cash {file_path} : {error}")

    def __rename_dividend_file(self, file_path: str, folder_path: str):
        """
        Renomme un fichier de dividende au format 'Ticker (YYYY-MM-DD)'.

        Args:
            file_path (str): Chemin actuel du fichier.
            folder_path (str): Dossier où se trouve le fichier.
        """
        pdf_text = self.__extract_pdf_text(file_path)
        
        raw_date = self.__regex_extract(pdf_text, r'DATE ((\d{2}/\d{2}/\d{4})|(\d{2}.\d{2}.\d{4}))', 1).replace('.', '/')
        operation_date = datetime.strptime(raw_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        
        ticker_symbol = self.__regex_extract(pdf_text, r"(POSITION|QUANTITÉ)[^\n]*\n([A-Za-zàâäéèêëîïôöùûü'\s&.-]+)", 2).strip()

        new_name = f"{ticker_symbol} ({operation_date})"
        target_path = self.__get_unique_path(folder_path, new_name)
        
        try:
            os.rename(file_path, target_path)
        except Exception as error:
            raise RuntimeError(f"Impossible de renommer le fichier de dividende {file_path} : {error}")

    def __rename_order_file(self, file_path: str, folder_path: str, is_buy_order: bool):
        """
        Renomme un fichier d'ordre (achat ou vente) avec Ticker et Date.

        Args:
            file_path (str): Chemin actuel du fichier.
            folder_path (str): Dossier où se trouve le fichier.
            is_buy_order (bool): True s'il s'agit d'un achat, False pour une vente.
        """
        pdf_text = self.__extract_pdf_text(file_path)
        
        # Extraction et normalisation de la date
        date_match = self.__regex_extract(pdf_text, r'DATE ((\d{2}/\d{2}/\d{4})|(\d{2}.\d{2}.\d{4}))', 1)
        normalized_date = re.sub(r'[-.]', '/', date_match)
        operation_date = datetime.strptime(normalized_date, '%d/%m/%Y').strftime('%Y-%m-%d')

        if is_buy_order:
            ticker_symbol = self.__regex_extract(pdf_text, r"(POSITION|QUANTITÉ)[^\n]*\n([A-Za-zàâäéèêëîïôöùûü'\s&.-]+)", 2).strip()
            file_prefix = f"{ticker_symbol} ({operation_date})"
        else:
            ticker_symbol = self.__regex_extract(pdf_text, r'(?:POSITION QUANTITÉ PRIX MONTANT|TITRE ORDRE / QUANTITÉ VALEUR)\s+([^\n]+)', 1).strip()
            
            # Distinction entre coûts ex-ante et facture de vente
            if 'INFORMATIONS SUR LES COÛTS EX-ANTE' in pdf_text.upper():
                file_prefix = f"{ticker_symbol} ({operation_date}) Costs"
            else:
                file_prefix = f"{ticker_symbol} ({operation_date}) Sale Invoice"

        target_path = self.__get_unique_path(folder_path, file_prefix)

        try:
            os.rename(file_path, target_path)
        except Exception as error:
            raise RuntimeError(f"Erreur lors du renommage de l'ordre {file_path} : {error}")
    

    # --- [ Extraction des Données (Processing) ] ---
    def __process_deposit_data(self, pdf_blobs: list) -> pd.DataFrame:
        """
        Extrait les données de dépôt de fonds avec gestion des frais de carte.

        Analyse le texte pour identifier le montant brut déposé, les frais de transaction
        et la date de valeur. Le montant net crédité est validé par la ligne de compte.

        Args:
            pdf_blobs (list): Liste des contenus binaires des PDF.

        Returns:
            pd.DataFrame: DataFrame contenant les dépôts structurés.
        """
        records = []
        for blob in pdf_blobs:
            text = self.__extract_pdf_text(blob)
            
            # --- [ Extraction des Montants ] ---
            # On cherche le premier "Montant total" qui correspond au brut (avant frais)
            raw_gross = self.__regex_extract(text, r"Montant total\s+([\d,.]+)\s+EUR", 1)
            gross_amount = float(raw_gross.replace(',', '.')) if raw_gross else 0.0

            # Extraction des frais de carte (on capture la valeur numérique)
            raw_fees = self.__regex_extract(text, r"Frais de paiements.*?([-]?[\d,.]+)\s+EUR", 1)
            fees = abs(float(raw_fees.replace(',', '.'))) if raw_fees else 0.0

            # --- [ Extraction de la Date ] ---
            # On cherche la ligne après COMPTE-ESPÈCES DATE DE VALEUR MONTANT
            cash_pattern = r"DE\d{20}\s+(\d{2}/\d{2}/\d{4})"
            val_date_str = self.__regex_extract(text, cash_pattern, 1)
            val_date = self.__parse_date(val_date_str) if val_date_str else None

            records.append({
                'ticker': None,
                'currency': 'EUR',
                'operation': 'deposit',
                'date': val_date,
                'amount': gross_amount,
                'fees': fees,
                'stock_price': None,
                'quantity': None
            })
            
        return pd.DataFrame(records)

    def __process_dividend_data(self, pdf_blobs: list) -> pd.DataFrame:
        """
        Extrait les données de dividendes en gérant l'inversion des taux de change.

        Calcule le montant brut en EUR en adaptant l'opération (multiplication ou 
        division) selon le sens du taux de change extrait (EUR/USD ou USD/EUR).
        La taxe est déduite par différence entre le brut converti et le net final.

        Args:
            pdf_blobs (list): Liste des contenus binaires des PDF.

        Returns:
            pd.DataFrame: DataFrame des dividendes avec montants et taxes en EUR.
        """
        records = []
        for blob in pdf_blobs:
            text = self.__extract_pdf_text(blob)
            base = self.__extract_transaction_base_data(text)
            
            # --- [ Extraction des Dates ] ---
            pay_date = self.__parse_date(self.__regex_extract(text, r'DE\d{20}\s(\d{2}[./]\d{2}[./]\d{4})', 1))

            # --- [ Extraction de la Quantité ] ---
            # Regex gérant le point ou la virgule, suivi de "unit." ou "titre(s)"
            qty_match = re.search(r'([\d,.]+)\s+(?:unit\.|titre\(s\))', text)
            quantity = 0.0
            if qty_match:
                # On remplace la virgule par un point pour le cast en float
                quantity = float(qty_match.group(1).replace(',', '.'))

            # --- [ Analyse du Taux de Change ] ---
            # On capture la valeur et l'unité (ex: 1.1715 et USD/EUR)
            fx_match = re.search(r'([\d,.]+)\s+(EUR/USD|USD/EUR)', text)
            fx_rate = 1.0
            fx_direction = "EUR/USD"
            
            if fx_match:
                fx_rate = float(fx_match.group(1).replace(',', '.'))
                fx_direction = fx_match.group(2)

            # --- [ Extraction des Totaux ] ---
            # On récupère tous les couples (Montant, Devise) associés au mot TOTAL
            all_totals = re.findall(r'TOTAL\s+([\d,.]+)\s+(USD|EUR)', text)
            if not all_totals:
                continue

            # Premier TOTAL = Brut / Dernier TOTAL = Net (toujours en EUR)
            gross_val = float(all_totals[0][0].replace(',', '.'))
            gross_currency = all_totals[0][1]
            net_in_eur = float(all_totals[-1][0].replace(',', '.'))

            # --- [ Conversion et Calcul des Taxes ] ---
            if gross_currency == "USD":
                # Logique de conversion selon la direction du taux
                if fx_direction == "EUR/USD":
                    # 1 EUR = X USD -> On divise
                    gross_in_eur = round(gross_val / fx_rate, 2)
                else:
                    # 1 USD = X EUR -> On multiplie
                    gross_in_eur = round(gross_val * fx_rate, 2)
            else:
                gross_in_eur = gross_val

            # Calcul de la taxe par différentiel
            tax_value = round(gross_in_eur - net_in_eur, 2)

            records.append({
                'ticker': base['ticker'],
                'currency': 'EUR',
                'operation': 'dividend',
                'date': pay_date,
                'amount': gross_in_eur,
                'fees': max(0.0, tax_value),
                'stock_price': None,
                'quantity': quantity
            })

        return pd.DataFrame(records)
    
    def __process_order_buy_data(self, pdf_blobs: list) -> pd.DataFrame:
        """
        Extrait les données d'achat d'actions en gérant les frais externes.

        Analyse le texte des PDF pour identifier la date, la quantité, le prix 
        unitaire et les frais. La gestion des frais cible spécifiquement la 
        mention 'Frais externes' sous la section 'POSITION MONTANT'.

        Args:
            pdf_blobs (list): Liste des contenus binaires des PDF.

        Returns:
            pd.DataFrame: DataFrame contenant les transactions d'achat.
        """
        records = []
        for blob in pdf_blobs:
            text = self.__extract_pdf_text(blob)
            base = self.__extract_transaction_base_data(text)
            
            # Extraction de la date d'exécution
            exec_date = self.__parse_date(self.__regex_extract(text, r'(?<=DATE\s)(\d{2}[/\.]\d{2}[/\.]\d{4})', 0))
            
            # Extraction de la quantité
            qty_pattern = r'([-+]?\d+[\.,]?\d*)\s+(?:[-+]?\d+[\.,]?\d*\s+EUR|titre\(s\)|unit\.)'
            qty = float(self.__regex_extract(text, qty_pattern, 1).replace(',', '.'))
            
            # Montant total investi
            total_invested = float(self.__regex_extract(text, r'MONTANT\s+.*\s+([-\d,]+)\s+EUR', 1).replace(',', '.'))

            # --- [ GESTION DES FRAIS ] ---
            # Nouvelle regex ciblant "Frais externes" après "POSITION MONTANT"
            # Elle cherche "Frais externes", puis le nombre juste avant "EUR"
            raw_fees = self.__regex_extract(text, r'Frais externes\s+([-\d,]+)\s+EUR', 1)
            
            if raw_fees:
                fees = abs(float(raw_fees.replace(',', '.')))
            else:
                # Fallback : recherche générique de la valeur après POSITION MONTANT
                generic_fees = self.__regex_extract(text, r'Frais fixes par ordre\s+([-\d,]+)\s+EUR', 1)
                fees = abs(float(generic_fees.replace(',', '.'))) if generic_fees else 0.0

            # Prix unitaire de l'action
            price_pattern = r'POSITION QUANTITÉ (?:COURS MOYEN|PRIX) MONTANT\s+.*?\s([\d,]+)\sEUR'
            stock_price = float(self.__regex_extract(text, price_pattern, 1).replace(',', '.'))
            
            records.append({
                'ticker': base['ticker'],
                'currency': 'EUR',
                'operation': 'buy',
                'date': exec_date,
                'amount': total_invested,
                'fees': fees,
                'stock_price': stock_price,
                'quantity': qty
            })

        return pd.DataFrame(records)
    
    def __process_interest_data(self, pdf_blobs: list) -> pd.DataFrame:
        """
        Extrait les données relatives aux intérêts versés sur le compte espèces.

        Args:
            pdf_blobs (list): Liste des contenus binaires des fichiers PDF.

        Returns:
            pd.DataFrame: DataFrame contenant les intérêts structurés.
        """
        records = []
        for blob in pdf_blobs:
            text = self.__extract_pdf_text(blob)
            
            # 1. Extraction du compte espèces (plusieurs formats possibles)
            cash_account = self.__regex_extract(text, r'compte_titresS\s+(\d+)', 1)
            if cash_account is None:
                cash_account = self.__regex_extract(text, r'(\d+)\s+RAPPORT D\'INTÉRÊTS', 1)
            
            # 2. Extraction de l'IBAN
            iban = self.__regex_extract(text, r'DE\d{20}', 0)
            
            # 3. Extraction de la ligne de détail des intérêts (Gestion multi-patterns)
            interest_patterns = [
                r'(?<=ACTIFS NATURE DES REVENUS TAUX D\'INTÉRÊTS TOTAL\n).+',
                r'(?<=ACTIFS NATURE DES REVENUS TAUX D\'INTÉRÊTS DATE TOTAL\n).+',
                r'(?<=ACTIFS NATURE DES REVENUS TAUX D\'INTÉRÊT DATE TOTAL\n).+'
            ]
            
            # On combine les motifs pour une recherche globale
            combined_pattern = '|'.join(interest_patterns)
            raw_line = self.__regex_extract(text, combined_pattern, 0)
            
            if raw_line:
                line_data = raw_line.split()
                # Taux d'intérêt (ex: 4,00% -> 0.04)
                rate = float(line_data[2][:-1].replace(',', '.')) / 100
                # Montant (avant-dernier élément de la ligne)
                amount = float(line_data[-2].replace(',', '.'))
            else:
                rate, amount = 0.0, 0.0

            # 4. Extraction de la date d'effet (Logique spécifique après IBAN)
            date_raw_line = self.__regex_extract(text, r'(?<=IBAN DATE D\'EFFET TOTAL\n).*\b\d{2}/\d{2}/\d{4}\b', 0)
            
            if date_raw_line:
                # On récupère le deuxième élément de la ligne (la date)
                date_str = date_raw_line.split()[1]
                effective_date = self.__parse_date(date_str)
            else:
                # Fallback sur la date d'effet standard si la ligne complexe échoue
                effective_date = self.__parse_date(self.__regex_extract(text, r'DATE D\'EFFET\s+(\d{2}/\d{2}/\d{4})', 1))

            records.append({
                'ticker': None,
                'currency': 'EUR',
                'operation': 'interest',
                'date': effective_date,
                'amount': amount,
                'fees': 0.0,
                'stock_price': None,
                'quantity': None
            })

        return pd.DataFrame(records)

    def __process_order_sell_data(self, pdf_blobs: list) -> pd.DataFrame:
        """
        Extrait les données de vente d'actifs financiers à partir des BLOBs.

        Args:
            pdf_blobs (list): Liste des contenus binaires des PDF.

        Returns:
            pd.DataFrame: Données de vente structurées.
        """
        records = []
        for blob in pdf_blobs:
            text = self.__extract_pdf_text(blob)
            base = self.__extract_transaction_base_data(text)
            
            # Extraction de la date d'exécution
            exec_date = self.__parse_date(self.__regex_extract(text, r'(?<=DATE\s)(\d{2}[-/.]\d{2}[-/.]\d{4})', 0))
            
            # --- GESTION DE LA QUANTITÉ (DOUBLE REGEX) ---
            # Tentative 1 : Regex complexe (Position ou format titre/unit)
            qty_pattern_complex = r'(?:POSITION\s+QUANTITÉ\s+PRIX\s+MONTANT\s+.*?\s+([-+]?\d+[\.,]?\d*)\s+[-+]?\d+[\.,]?\d*\s+EUR\s+[-+]?\d+[\.,]?\d*\s+EUR)|(?:([-+]?\d+[\.,]?\d*)\s+(?:titre\(s\)|unit\.))'
            qty_str = self.__regex_extract(text, qty_pattern_complex, 1)
            
            # Si le premier groupe est vide, on vérifie le second groupe de la même regex
            if qty_str is None:
                qty_str = self.__regex_extract(text, qty_pattern_complex, 2)
            
            # Tentative 2 : Regex simple si la complexe a échoué
            if qty_str is None:
                qty_str = self.__regex_extract(text, r'([\d]+(?:[.,]\d+)?)\s+titre\(s\)', 1)
            
            # Si après les deux tentatives on n'a rien, on lève une erreur pour ce fichier
            if qty_str is None:
                print("Avertissement : Impossible d'extraire la quantité pour un fichier, passage au suivant.")
                continue
                
            quantity = abs(float(qty_str.replace(',', '.')))

            # --- MONTANTS FINANCIERS ---
            # Prix unitaire
            unit_price_str = self.__regex_extract(text, r'PRIX MONTANT\s+.*?\s([\d,]+)\sEUR', 1)
            unit_price = float(unit_price_str.replace(',', '.')) if unit_price_str else 0.0
            
            # Montant brut de la vente
            gross_str = self.__regex_extract(text, r'PRIX MONTANT\s+.*\s+([-\d,]+)\s+EUR', 1)
            gross_sale_amount = float(gross_str.replace(',', '.')) if gross_str else 0.0
            
            # Montant net reçu (après frais)
            net_str = self.__regex_extract(text, r'DATE DE VALEUR MONTANT\s+.*\s+([-\d,]+)\s+EUR', 1)
            net_proceeds = float(net_str.replace(',', '.')) if net_str else gross_sale_amount
            
            # Calcul des frais par différence (en valeur absolue)
            fees = round(abs(gross_sale_amount - net_proceeds), 2)

            records.append({
                'ticker': base['ticker'],
                'currency': 'EUR',
                'operation': 'sell',
                'date': exec_date,
                'amount': abs(gross_sale_amount),
                'fees': fees,
                'stock_price': unit_price,
                'quantity': quantity
            })

        return pd.DataFrame(records)
    

    # --- [ Gestion des Tickers & Référentiels ] ---
    def __map_company_name_to_ticker(self, company_name: str) -> str:
        """
        Associe un nom d'entreprise à son ticker via recherche floue et 
        vérification du taux de présence des mots.

        Args:
            company_name (str): Le nom de l'entreprise extrait du document.

        Returns:
            str: Le symbole boursier (ticker) correspondant.

        Raises:
            ValueError: Si moins de 50% des mots correspondent ET que le score 
                        flou est inférieur à 70%.
        """
        # Paramètres de confiance
        similarity_threshold = 0.70 
        word_match_threshold = 0.50  # 50% des mots doivent correspondre
        
        cleaned_name = company_name.strip()
        cleaned_name_lower = cleaned_name.lower()
        # On découpe le nom du PDF en liste de mots pour la comparaison
        pdf_words = cleaned_name_lower.split()

        # 1. Correspondance exacte
        for name_key, ticker_value in self.TICKERS_MAPPING.items():
            if cleaned_name_lower == name_key.lower():
                print(f"{company_name} => {ticker_value}")
                return ticker_value

        # 2. Recherche par taux d'inclusion des mots (Seuil 50%)
        for name_key, ticker_value in self.TICKERS_MAPPING.items():
            key_words = name_key.lower().split()
            # On compte combien de mots de notre mapping sont dans le nom PDF
            words_found = [word for word in key_words if word in pdf_words]
            match_rate = len(words_found) / len(key_words) if key_words else 0

            if match_rate >= word_match_threshold:
                print(f"{company_name} => {ticker_value}")
                return ticker_value

        # 3. Recherche par similarité floue (Fuzzy Matching) pour les fautes de frappe
        best_suggested_ticker = None
        best_suggested_key_name = None
        highest_score = 0.0

        for name_key, ticker_value in self.TICKERS_MAPPING.items():
            score = SequenceMatcher(None, cleaned_name_lower, name_key.lower()).ratio()
            
            if score > highest_score:
                highest_score = score
                best_suggested_ticker = ticker_value
                best_suggested_key_name = name_key

        # Validation finale par similarité
        if highest_score >= similarity_threshold:
            print(f"{company_name} => {ticker_value}")
            return best_suggested_ticker

        # 4. Message d'erreur détaillé en cas d'échec total
        suggestion_info = ""
        if best_suggested_ticker:
            current_score_pct = highest_score * 100
            threshold_pct = similarity_threshold * 100
            suggestion_info = (f"{current_score_pct:.1f}% < {threshold_pct}% "
                               f"le ticker suggéré était '{best_suggested_ticker}' "
                               f"(clé: '{best_suggested_key_name}')")

        raise ValueError(
            f"Erreur de correspondance : Le nom '{company_name}' n'a pas pu être validé. "
            f"Détails : {suggestion_info}"
        )


    # --- [ Utilitaires Parsing & Transformation ] ---
    def __extract_pdf_text(self, source) -> str:
        """
        Extrait le texte d'un PDF à partir d'un chemin de fichier (str) 
        ou d'un contenu binaire (bytes).

        Args:
            source (str | bytes): Le chemin du fichier ou le contenu binaire du PDF.

        Returns:
            str: Le texte intégral extrait du document.

        Raises:
            RuntimeError: Si le document ne peut pas être ouvert ou analysé.
        """
        import pdfplumber

        try:
            full_text = ''
            
            # Si source est de type bytes (BLOB de la BDD), on l'enveloppe dans BytesIO
            # Sinon (str), on passe directement le chemin à pdfplumber
            pdf_input = io.BytesIO(source) if isinstance(source, bytes) else source
            
            with pdfplumber.open(pdf_input) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + '\n'
            
            return full_text

        except Exception as error:
            # On évite d'afficher le contenu binaire brut dans l'erreur pour plus de clarté
            error_msg = 'Données binaires' if isinstance(source, bytes) else source
            raise RuntimeError(f'Erreur lors de l\'extraction PDF ({error_msg}) : {error}')
        
    def __regex_extract(self, text: str, pattern: str, group_index: int) -> str:
        """
        Extrait une information via Regex sans bloquer l'exécution en cas d'absence.

        Args:
            text (str): Le texte source à analyser.
            pattern (str): Le motif Regex à rechercher.
            group_index (int): L'index du groupe de capture à retourner.

        Returns:
            str: La donnée extraite ou None si le motif n'est pas trouvé.
        """
        import re
        
        match = re.search(pattern, text)
        if match:
            try:
                return match.group(group_index)
            except IndexError:
                # Cas où l'index du groupe demandé n'existe pas dans le match
                return None
        
        return None
    
    def __aggregate_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Regroupe les transactions similaires en incluant les valeurs nulles.

        Fusionne les lignes partageant le même type d'opération, date et prix. 
        L'argument dropna=False est crucial pour ne pas supprimer les opérations 
        de type dépôt ou retrait qui possèdent des champs 'None' (ticker, prix).

        Args:
            df (pd.DataFrame): DataFrame des transactions au format 'user_transaction'.

        Returns:
            pd.DataFrame: DataFrame agrégé conservant l'intégralité des types d'opérations.
        """
        if df.empty:
            return df

        # Définition des colonnes de regroupement (clés d'unicité)
        group_columns = ['ticker', 'currency', 'operation', 'date', 'stock_price']

        # Agrégation avec dropna=False pour inclure les lignes ayant des None/NaN
        aggregated_df = df.groupby(group_columns, as_index=False, dropna=False).agg({
            'amount': 'sum',
            'fees': 'sum',
            'quantity': 'sum'
        })

        # Réorganisation des colonnes selon le schéma de la table user_transaction
        column_order = [
            'ticker', 'currency', 'operation', 'date', 
            'amount', 'fees', 'stock_price', 'quantity'
        ]
        
        return aggregated_df[column_order]
    
    def __parse_date(self, date_string: str) -> date:
        """
        Convertit une chaîne de caractères en objet date, gérant divers formats.

        Args:
            date_string (str): La date sous forme de texte.

        Returns:
            date: L'objet date Python.
        """
        if not date_string:
            return None
        
        # Normalisation des séparateurs
        normalized = date_string.replace('.', '/').replace('-', '/')
        try:
            return datetime.strptime(normalized, '%d/%m/%Y').date()
        except ValueError:
            return datetime.strptime(normalized, '%Y/%m/%Y').date()

    def __get_unique_path(self, folder_path: str, base_name: str) -> str:
        """
        Génère un chemin de fichier unique en ajoutant un suffixe numérique si nécessaire.

        Args:
            folder_path (str): Le dossier de destination.
            base_name (str): Le nom de fichier souhaité (sans extension).

        Returns:
            str: Le chemin complet vers le fichier unique avec l'extension .pdf.
        """
        counter = 1
        unique_path = os.path.join(folder_path, f"{base_name}.pdf")
        
        # Boucle pour incrémenter le compteur si le fichier existe déjà
        while os.path.exists(unique_path):
            unique_path = os.path.join(folder_path, f"{base_name} - {counter}.pdf")
            counter += 1
            
        return unique_path

    def __extract_transaction_base_data(self, text: str):
        """
        Extrait les données communes à la plupart des documents Trade Republic.

        Args:
            text (str): Texte intégral du PDF.

        Returns:
            dict: Dictionnaire contenant ISIN, Ticker et Compte-titres.
        """
        isin = self.__regex_extract(text, r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b", 0)
        account = self.__regex_extract(text, r"COMPTE-TITRES\s+(\d+)", 1)
        
        raw_name = self.__regex_extract(text, r"(POSITION|QUANTITÉ)[^\n]*\n([A-Za-zàâäéèêëîïôöùûü'\s&.-]+)", 2)
        clean_name = self.__clean_company_name(raw_name)
        ticker = self.__map_company_name_to_ticker(clean_name)
        
        return {'isin': isin, 'account': account, 'ticker': ticker, 'name': clean_name}
    
    def __clean_company_name(self, raw_name: str) -> str:
        """
        Nettoie le nom de la société en supprimant les suffixes juridiques.

        Args:
            raw_name (str): Nom brut extrait du PDF.

        Returns:
            str: Nom nettoyé.
        """
        if not raw_name:
            return ''
        suffixes = ['Corp.', 'S.A.', 'Inc.', 'SE', 'AG']
        clean_name = raw_name
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, '')
        return clean_name.strip()
