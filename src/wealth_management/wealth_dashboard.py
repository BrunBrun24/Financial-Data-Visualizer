import json
import os

import pandas as pd

from database.bnp_paribas_database import BnpParibasDatabase
from database.trade_republic_database import TradeRepublicDatabase


class WealthDashboard:
    """
    Moteur de consolidation et de visualisation du patrimoine.
    
    Cette classe agrège les données bancaires et boursières pour générer
    des rapports d'évolution et de répartition sous forme de graphiques.
    """

    def __init__(self, bnp_checking_db_path: str, bnp_livret_a_db_path: str, trade_republic_db_path: str):
        """
        Initialise les connexions aux différentes sources de données.

        Args:
            - bnp_checking_db_path (str) : Chemin vers la base du compte chèques BNP.
            - bnp_livret_a_db_path (str) : Chemin vers la base du Livret A BNP.
            - trade_republic_db_path (str) : Chemin vers la base Trade Republic.
        """
        self.__bnp_checking_db = BnpParibasDatabase(db_path=bnp_checking_db_path)
        self.__bnp_livret_a_db = BnpParibasDatabase(db_path=bnp_livret_a_db_path)
        self.__trade_republic_db = TradeRepublicDatabase(db_path=trade_republic_db_path)


    # --- [ Export ] ---
    def generate_wealth_report(self, export_path: str):
        """
        Génère un fichier HTML complet avec des graphiques plein écran et sélecteurs de dates.

        Args:
            - export_path (str) : Dossier où enregistrer le rapport.
        """
        # Récupération des données consolidées
        data_map = self.__get_normalized_data()
        
        # Génération du contenu des alertes
        alerts_content = self.__get_alerts_html(data_map)
        
        # Récupération des configurations Highcharts
        global_cfg = self.__get_global_evolution_config(data_map)
        accounts_cfg = self.__get_accounts_evolution_config(data_map)
        pie_cfg = self.__get_distribution_pie_config(data_map)
        liquidity_cfg = self.__get_liquidity_config(data_map)
        fire_gauge = self.__get_fire_gauge_config(data_map)

        # Construction du template HTML
        html_template = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <script src="https://code.highcharts.com/stock/highstock.js"></script>
            <script src="https://code.highcharts.com/highcharts-more.js"></script>
            <script src="https://code.highcharts.com/modules/solid-gauge.js"></script>
            
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; background-color: #f0f2f5; color: #333; }}
                h1 {{ text-align: center; padding: 20px; }}
                .chart-container {{ width: 95%; margin: 20px auto; background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); box-sizing: border-box; }}
                .alerts-wrapper {{ width: 95%; margin: 20px auto; }}
                .alert {{ padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 6px solid; font-size: 1.05em; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
                .danger {{ background-color: #fdecea; color: #b71c1c; border-left-color: #d32f2f; }}
                .success {{ background-color: #edf7ed; color: #1b5e20; border-left-color: #2e7d32; }}
                .row-container {{ display: flex; flex-wrap: wrap; justify-content: center; width: 95%; margin: 0 auto; gap: 20px; }}
                .small-chart-wrapper {{ flex: 1; min-width: 450px; max-width: calc(50% - 10px); display: flex; justify-content: center; }}
            </style>
        </head>
        <body>
            <h1>Tableau de Bord Patrimonial</h1>
            <div class="alerts-wrapper">{alerts_content}</div>
            <div id="global_chart" class="chart-container" style="height: 65vh;"></div>
            <div id="accounts_chart" class="chart-container" style="height: 65vh;"></div>
            <div class="row-container">
                <div class="small-chart-wrapper"><div id="pie_chart" class="chart-container" style="width: 100%; height: 65vh;"></div></div>
                <div class="small-chart-wrapper"><div id="fire_gauge" class="chart-container" style="width: 100%; height: 65vh;"></div></div>
            </div>
            <div id="liquidity_chart" class="chart-container" style="height: 35vh;"></div>
            <script>
                Highcharts.chart('global_chart', {json.dumps(global_cfg)});
                Highcharts.chart('accounts_chart', {json.dumps(accounts_cfg)});
                Highcharts.chart('pie_chart', {json.dumps(pie_cfg)});
                Highcharts.chart('liquidity_chart', {json.dumps(liquidity_cfg)});
                Highcharts.chart('fire_gauge', {json.dumps(fire_gauge)});
            </script>
        </body>
        </html>
        """
        
        # Exportation du fichier
        if not os.path.exists(export_path):
            os.makedirs(export_path)
            
        file_path = os.path.join(export_path, 'Evolution de mon patrimoine.html')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_template)


    # --- [ Configurations Highcharts ] ---
    def __get_global_evolution_config(self, data_map: dict) -> dict:
        """
        Configure le graphique global de l'évolution du patrimoine.
        
        Args:
            - data_map (dict) : Données normalisées des comptes.

        Returns:
            - dict : Configuration Highcharts.
        """
        total_series = data_map['checking'] + data_map['livret_a'] + data_map['trade_republic']
        chart_data = [[int(date.timestamp() * 1000), round(val, 2)] for date, val in total_series.items()]

        return {
            "rangeSelector": {
                "enabled": True,
                "buttons": [
                    {"type": "year", "count": 1, "text": "1y"},
                    {"type": "year", "count": 3, "text": "3y"},
                    {"type": "year", "count": 5, "text": "5y"},
                    {"type": "ytd", "text": "YTD"},
                    {"type": "all", "text": "All"}
                ],
                "selected": 4,
                "buttonTheme": { "width": 30 },
                "inputEnabled": False
            },
            "chart": {
                "type": "area",
                "zoomType": None,
                "panning": False,
                "mouseWheelZoom": False
            },
            "title": {"text": "Évolution du Patrimoine Global"},
            "xAxis": { "type": "datetime", "ordinal": False },
            "yAxis": {
                "title": {"text": "Total (€)"},
                "opposite": False,
                "startOnTick": False,
                "endOnTick": False
            },
            "plotOptions": { "area": { "threshold": None, "enableMouseTracking": True } },
            "tooltip": {"valueSuffix": " €"},
            "series": [{
                "name": "Patrimoine Total", 
                "data": chart_data, 
                "color": "#00E272", 
                "fillOpacity": 0.3,
                "tooltip": {"valueDecimals": 2}
            }]
        }
    
    def __get_accounts_evolution_config(self, data_map: dict) -> dict:
        """
        Configure le graphique par compte en mode lignes.
        
        Args:
            - data_map (dict) : Données normalisées des comptes.

        Returns:
            - dict : Configuration Highcharts.
        """
        series = []
        names = {
            "checking": "Compte Chèques", 
            "livret_a": "Livret A", 
            "trade_republic": "Trade Republic"
        }
        
        for key, name in names.items():
            items = list(data_map[key].items())
            n = len(items)
            formatted_data = []

            for i in range(n):
                d, v = items[i]
                # Logique pour garder les points actifs ou entourés d'activité
                is_active = (v != 0)
                has_prev_active = (i > 0 and items[i-1][1] != 0)
                has_next_active = (i < n - 1 and items[i+1][1] != 0)

                if is_active or has_prev_active or has_next_active:
                    timestamp = int(d.timestamp() * 1000)
                    formatted_data.append([timestamp, round(v, 2)])

            if formatted_data:
                series.append({
                    "name": name, 
                    "data": formatted_data,
                    "lineWidth": 3,
                    "marker": { "enabled": False },
                })

        return {
            "rangeSelector": { "enabled": False },
            "navigator": { "enabled": False },
            "scrollbar": { "enabled": False },
            "chart": {"type": "line"},
            "title": { "text": "Évolution détaillée par compte" },
            "xAxis": { "type": "datetime" },
            "yAxis": {
                "title": { "text": "Montant (€)" },
                "opposite": False,
                "startOnTick": False,
                "endOnTick": False
            },
            "legend": {
                "enabled": True,
                "align": "center",
                "verticalAlign": "bottom",
                "layout": "horizontal",
                "itemStyle": { "fontSize": "14px", "cursor": "pointer" }
            },
            "tooltip": { "shared": False, "valueSuffix": " €", "split": True },
            "series": series
        }
    
    def __get_distribution_pie_config(self, data_map: dict) -> dict:
        """
        Configure le camembert de répartition.
        
        Args:
            - data_map (dict) : Données normalisées des comptes.

        Returns:
            - dict : Configuration Highcharts.
        """
        pie_data = []
        names = {"checking": "Compte Chèques", "livret_a": "Livret A", "trade_republic": "Trade Republic"}
        
        for key, name in names.items():
            last_val = round(data_map[key].iloc[-1], 2)
            pie_data.append({"name": name, "y": last_val})

        return {
            "chart": {"type": "pie"},
            "title": {"text": "Répartition Actuelle"},
            "plotOptions": {"pie": {"dataLabels": {"enabled": True, "format": "{point.name}: {point.percentage:.1f}%"}}},
            "tooltip": {"valueSuffix": " €"},
            "series": [{"name": "Part", "colorByPoint": True, "data": pie_data}],
        }

    def __get_liquidity_config(self, data_map: dict) -> dict:
        """
        Configure le graphique de liquidité (Pyramide des risques).
        
        Args:
            - data_map (dict) : Données normalisées des comptes.

        Returns:
            - dict : Configuration Highcharts.
        """
        cash = round(data_map['checking'].iloc[-1], 2)
        precaution = round(data_map['livret_a'].iloc[-1], 2)
        invest = round(data_map['trade_republic'].iloc[-1], 2)
        
        return {
            "chart": { "type": "bar", "height": 300 },
            "title": {"text": "Profil de Liquidité et Risque"},
            "xAxis": {"categories": ["Patrimoine"], "visible": False},
            "yAxis": { "min": 0, "max": 100, "title": {"text": "Répartition en %"} },
            "legend": {"reversed": True},
            "plotOptions": {
                "series": {
                    "stacking": "percent",
                    "dataLabels": { "enabled": True, "format": "{series.name}: {point.percentage:.1f}%" }
                }
            },
            "tooltip": {"valueSuffix": " €"},
            "series": [
                { "name": "Investissements", "data": [invest], "color": "#FF4560" },
                { "name": "Précaution (Livret A)", "data": [precaution], "color": "#FFD700" },
                { "name": "Liquidités", "data": [cash], "color": "#00E272" }
            ]
        }


    # --- [ Configurations Highcharts ] ---
    def __get_fire_gauge_config(self, data_map: dict) -> dict:
        """
        Calcule le score d'Indépendance Financière (Règle des 4%) et configure la jauge.
        
        Args:
            - data_map (dict) : Données normalisées des comptes.

        Returns:
            - dict : Configuration Highcharts (Gauge) avec sous-titre détaillé.
        """
        # Calcul du patrimoine total actuel (somme des derniers points de chaque série)
        total_wealth = (data_map['checking'].iloc[-1] + data_map['livret_a'].iloc[-1] + data_map['trade_republic'].iloc[-1])
        
        # Récupération de la moyenne des dépenses et calcul de l'objectif (x25)
        avg_monthly = self.__average_monthly_expenses()
        fire_objective = avg_monthly * 12 * 25
        
        # Calcul du score d'avancement plafonné à 100%
        remaining_amount = max(0, fire_objective - total_wealth)
        score_pct = min(round((total_wealth / fire_objective) * 100, 1), 100)

        # Fonction interne pour le formatage des montants (ex: 12 345)
        def f_num(n):
            return f"{int(n):,}".replace(",", " ")

        return {
            "chart": {
                "type": "solidgauge", 
                "height": "600px",
                "style": { "fontFamily": "'Segoe UI', Tahoma, sans-serif" }
            },
            "title": { "text": "Score d'Indépendance Financière" },
            "subtitle": {
                # Ajout du patrimoine actuel dans le bloc informatif sous le graphique
                "text": (
                    f"<div style='text-align: center; color: #666; font-size: 14px; margin-top: 10px; line-height: 1.6;'>"
                    f"Moyenne des dépenses : <b>{f_num(avg_monthly)}€ / mois</b><br/>"
                    f"Objectif de liberté financière (FIRE) : <b>{f_num(fire_objective)}€</b><br/>"
                    f"Montant restant à gagner : <b>{f_num(remaining_amount)}€</b>"
                    f"</div>"
                ),
                "useHTML": True,
                "align": "center",
                "verticalAlign": "bottom",
                "y": -20
            },
            "tooltip": { "enabled": False },
            "pane": {
                "center": ['50%', '65%'],
                "size": '100%',
                "startAngle": -90, "endAngle": 90,
                "background": {"innerRadius": "60%", "outerRadius": "100%", "shape": "arc"}
            },
            "plotOptions": {
                "solidgauge": {
                    "enableMouseTracking": False, # Désactive l'affichage au survol
                    "dataLabels": {
                        "y": -40,
                        "borderWidth": 0,
                        "useHTML": True
                    }
                }
            },
            "yAxis": {
                "min": 0, "max": 100,
                "stops": [[0.1, '#FF4560'], [0.5, '#FFD700'], [0.9, '#00E272']],
                "lineWidth": 0, "tickWidth": 0, "minorTickInterval": None,
                "labels": { "y": 16 }
            },
            "series": [{
                "name": "Score",
                "data": [score_pct],
                "dataLabels": {
                    "format": (
                        '<div style="text-align: center;">'
                        '<span style="font-size: 30px; font-weight: bold; color: #333;">{y}%</span>'
                        '</div>'
                    )
                }
            }]
        }

    def __get_alerts_html(self, data_map: dict) -> str:
        """
        Analyse les données pour générer des alertes de gestion financière.
        
        Args:
            - data_map (dict) : Données normalisées des comptes.

        Returns:
            - str : Balises HTML contenant les messages d'alertes.
        """
        minimum_livret_a_amount = 10000
        minimum_checking_amount = 50
        maximum_checking_amount = 200
        alerts = []

        def f_num(n):
            return f"{int(n):,}".replace(",", " ")

        # Analyse épargne de précaution
        precaution_balance = data_map['livret_a'].iloc[-1]
        if precaution_balance < minimum_livret_a_amount:
            alerts.append(f'<div class="alert danger"><strong>⚠️ Alerte Épargne de Précaution :</strong> Ton Livret A est à {f_num(precaution_balance)}€. Seuil recommandé : {f_num(minimum_livret_a_amount)}€.</div>')

        # Analyse compte chèques
        checking_balance = data_map['checking'].iloc[-1]
        if checking_balance < minimum_checking_amount:
            alerts.append(f'<div class="alert danger"><strong>⚠️ Solde Compte Chèques Bas :</strong> Attention, il ne reste que {f_num(checking_balance)}€.</div>')
        elif checking_balance > maximum_checking_amount:
            alerts.append(f'<div class="alert danger"><strong>⚠️ Solde Compte Chèques Haut :</strong> Trop d\'argent dort sur le compte ({f_num(checking_balance)}€).</div>')

        return "".join(alerts)


    # --- [ Traitement des Données ] ---
    def __get_normalized_data(self) -> dict:
        """
        Prépare et aligne les données de tous les comptes sur une échelle de temps commune.

        Returns:
            - dict : Dictionnaire de pd.Series indexées par date.
        """
        # On récupère les DataFrames (qui contiennent déjà operation_date en datetime)
        df_c = self.__bnp_checking_db._get_table_data('categorized_operations')
        df_s = self.__bnp_livret_a_db._get_table_data('categorized_operations')
        
        # Pour Trade Republic, on garde ta logique spécifique
        df_tr = self.__trade_republic_db._get_performance_data(
            'Mes Portefeuilles', 'Mes Portefeuilles', 'portfolio_valuation'
        ).rename(columns={'value': 'amount', 'operation_date': 'date'})

        # Uniformisation des noms de colonnes pour la date
        df_c = df_c.rename(columns={'operation_date': 'date'})
        df_s = df_s.rename(columns={'operation_date': 'date'})
        
        # Conversion des dates
        for df in [df_c, df_s, df_tr]:
            df['date'] = pd.to_datetime(df['date'])

        # Création de la plage temporelle
        all_dates = pd.concat([df_c['date'], df_s['date'], df_tr['date']])
        full_range = pd.date_range(start=all_dates.min(), end=all_dates.max(), freq='D')

        # Sommation cumulée
        checking = df_c.groupby('date')['amount'].sum().reindex(full_range, fill_value=0).cumsum()
        livret_a = df_s.groupby('date')['amount'].sum().reindex(full_range, fill_value=0).cumsum()
        
        # Propagation Trade Republic
        tr_raw = df_tr.groupby('date')['amount'].sum().reindex(full_range)
        trade_republic = tr_raw.ffill().fillna(0)

        return {"checking": checking, "livret_a": livret_a, "trade_republic": trade_republic}

    def __average_monthly_expenses(self) -> float:
        """
        Calcule la moyenne des dépenses mensuelles sur les 12 derniers mois.

        Returns:
            - float : Montant moyen des dépenses mensuelles.
        """
        # Fusion des sources
        df_checking = self.__bnp_checking_db._get_table_data('categorized_operations')
        df_livret_a = self.__bnp_livret_a_db._get_table_data('categorized_operations')
        df_all = pd.concat([df_checking, df_livret_a], ignore_index=True)
        
        # Conversion des dates
        df_all['operation_date'] = pd.to_datetime(df_all['operation_date'])
        
        # Filtrage sur les 12 derniers mois
        last_date = df_all["operation_date"].max()
        start_date = last_date - pd.DateOffset(months=12)
        df_all = df_all[df_all["operation_date"] >= start_date].copy()

        # Exclusion des transferts vers l'épargne/investissement
        exclude_names = ["Épargne", "Investissement"]
        
        # Filtrage des dépenses réelles
        df_expenses = df_all[
            (df_all['amount'] < 0) & 
            (~df_all['category_name'].isin(exclude_names))
        ].copy()
        
        # Agrégation mensuelle
        monthly_totals = df_expenses.groupby(df_expenses['operation_date'].dt.to_period('M'))['amount'].sum().abs()
        
        if monthly_totals.empty:
            return 2000.0
            
        return round(float(monthly_totals.mean()), 2)
