import json
import os

import pandas as pd

from database.trade_republic_database import TradeRepublicDatabase


class PortfolioVisualizer(TradeRepublicDatabase):
    """
    Classe responsable de la génération de rapports visuels (HTML/Highcharts)
    basés sur les données de performance du portefeuille.
    """

    def __init__(self, db_path: str, root_path: str):
        """
        Initialise le visualiseur et prépare l'environnement de sortie.

        Args:
            - db_path (str) : Chemin vers la base de données SQLite.
            - root_path (str) : Dossier racine où les rapports seront stockés.
        """
        super().__init__(db_path)
        self.__root_path = root_path
        # Création automatique de l'arborescence de sortie
        self.__ensure_directory_structure()


    # --- [ Flux Principal ] ---
    def generate_performance_report(self):
        """
        Point d'entrée principal pour extraire les données et générer le fichier HTML.
        """
        clean_df = self.__fetch_clean_data()
        
        if not clean_df.empty:
            self.__build_html_dashboard(clean_df)

    # --- [ Gestion du Système de Fichiers ] ---
    def __ensure_directory_structure(self):
        """
        Vérifie et crée les dossiers nécessaires pour le stockage du rapport.
        """
        # Création récursive du dossier si n'existe pas
        if not os.path.exists(self.__root_path):
            os.makedirs(self.__root_path)

    # --- [ Traitement des Données ] ---
    def __fetch_clean_data(self) -> pd.DataFrame:
        """
        Extrait les données de la base et filtre les actifs obsolètes.

        Returns:
            - pd.DataFrame : Données nettoyées prêtes pour la visualisation.
        """
        df = self._get_performance_data()
        
        if df.empty:
            return df
        
        # Conversion des dates pour les manipulations temporelles
        df['date'] = pd.to_datetime(df['date'])

        # Identification de la date la plus récente pour filtrer les positions fermées
        val_df = df[df['metric_type'] == 'tickers_valuation']
        if val_df.empty:
            return df
        
        latest_date = val_df['date'].max()
        
        # On ne garde que les tickers ayant une valeur positive à la dernière date
        active_tickers = val_df[(val_df['date'] == latest_date) & (val_df['value'] > 0)]['ticker'].unique()
        
        # Filtrage incluant les totaux de portefeuilles et les actifs actifs
        mask = (df['ticker'].isin(active_tickers)) | \
               (df['ticker'] == "Mes Portefeuilles") | \
               (df['metric_type'].str.contains('portfolio_'))
            
        return df[mask].copy()

    # --- [ Génération HTML & Graphiques ] ---
    def __build_html_dashboard(self, df: pd.DataFrame):
        """
        Construit le fichier HTML intégrant la bibliothèque Highcharts et les données.

        Args:
            - df (pd.DataFrame) : Le DataFrame filtré contenant les métriques.
        """
        all_charts_config = []
        # Regroupement par portefeuille et type de métrique pour structurer les graphiques
        grouped = df.sort_values(['metric_type', 'ticker']).groupby(['portfolio_name', 'metric_type'])

        for (portfolio, metric), data in grouped:
            series_list = []
            is_ticker_level = metric.startswith('tickers_')
            
            # Définition du style : Aires empilées pour le global, lignes pour le détail
            if not is_ticker_level and "valuation" in metric:
                chart_style = "area"
                stacking_type = "normal"
            else:
                chart_style = "line"
                stacking_type = None
                
            for ticker in data['ticker'].unique():
                subset = data[data['ticker'] == ticker]
                
                # Conversion des données pour le format JS (Timestamp en MS, Valeur arrondie)
                points = [
                    [int(row['date'].timestamp() * 1000), round(float(row['value']), 2)] 
                    for _, row in subset.iterrows()
                ]
                
                series_list.append({
                    "name": ticker,
                    "data": points
                })

            all_charts_config.append({
                "metric": metric,
                "is_ticker": is_ticker_level,
                "config": {
                    "chart": {"type": chart_style, "zoomType": "x"},
                    "title": {"text": f"{metric.replace('_', ' ').upper()}"},
                    "subtitle": {"text": f"Source : {portfolio}"},
                    "xAxis": {"type": "datetime"},
                    "yAxis": {"title": {"text": "Valeur (€)"}},
                    "tooltip": {
                        "shared": False, 
                        "crosshairs": True,
                        "valueDecimals": 2,
                        "valueSuffix": " €"
                    },
                    "plotOptions": {
                        "series": {
                            "stacking": stacking_type,
                            "marker": {"enabled": False},
                            "connectNulls": True
                        }
                    },
                    "series": series_list
                }
            })

        # Extraction des noms de métriques pour le menu déroulant dynamique
        ticker_metrics = sorted(list(set([c['metric'] for c in all_charts_config if c['is_ticker']])))

        # Assemblage du template HTML
        html_output = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>Performance Portefeuille</title>
            <script src="https://code.highcharts.com/highcharts.js"></script>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; padding: 20px; }}
                h1 {{ text-align: center; color: #2c3e50; }}
                .section-title {{ 
                    background: #2c3e50; color: white; padding: 15px; 
                    border-radius: 8px; margin: 20px 0; display: flex; justify-content: space-between;
                }}
                .grid-container {{
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px;
                }}
                .chart-box {{ background: white; border-radius: 12px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); height: 450px; }}
                .large-box {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 6px 15px rgba(0,0,0,0.1); height: 700px; }}
                .controls {{ margin-bottom: 20px; }}
                select {{ padding: 10px; border-radius: 5px; border: 1px solid #ccc; }}
            </style>
        </head>
        <body>
            <h1>📈 Dashboard de Performance</h1>
            
            <div class="section-title">VUE D'ENSEMBLE DU PORTEFEUILLE</div>
            <div class="grid-container" id="global-charts"></div>

            <div class="section-title">ANALYSE DÉTAILLÉE PAR ACTIF</div>
            <div class="controls">
                <select id="metric-selector" onchange="refreshDetailChart()">
                    {"".join([f'<option value="{m}">{m.replace("tickers_", "").upper()}</option>' for m in ticker_metrics])}
                </select>
            </div>
            <div id="detail-chart" class="large-box"></div>

            <script>
                const dataConfigs = {json.dumps(all_charts_config)};

                // Rendu des graphiques globaux
                dataConfigs.filter(c => !c.is_ticker).forEach((item, i) => {{
                    const el = document.createElement('div');
                    el.className = 'chart-box';
                    el.id = 'chart-glob-' + i;
                    document.getElementById('global-charts').appendChild(el);
                    Highcharts.chart(el.id, item.config);
                }});

                // Logique de mise à jour du graphique de détail
                function refreshDetailChart() {{
                    const selected = document.getElementById('metric-selector').value;
                    const chartInfo = dataConfigs.find(c => c.metric === selected);
                    if (chartInfo) {{
                        Highcharts.chart('detail-chart', chartInfo.config);
                    }}
                }}
                refreshDetailChart();
            </script>
        </body>
        </html>
        """
        
        # Export final vers le système de fichiers
        file_path = os.path.join(self.__root_path, "Bilan Portefeuille.html")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(html_output)
