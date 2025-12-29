import json
import uuid

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from bank_accounts.bnp_paribas.report_data_handler import ReportDataHandler
from database.bnp_paribas_database import BnpParibasDatabase


class GraphiqueFinancier(BnpParibasDatabase):
    """
    Génère différents graphiques financiers à partir des opérations catégorisées d'un compte bancaire. 
    Elle hérite de `BnpParibasDatabase` et fournit des méthodes pour :

    - Créer des dossiers annuels pour organiser les graphiques.
    - Générer des graphiques Sankey, en barres empilées et circulaires (sunburst) pour visualiser 
    les revenus, les dépenses et leur répartition par catégorie et sous-catégorie.
    - Combiner plusieurs graphiques côte à côte si nécessaire pour éviter les doublons.
    - Produire des bilans annuels et mensuels en créant et sauvegardant automatiquement les fichiers HTML.
    """

    def __init__(self, db_path: str, root_path: str):
        """
        Initialise le générateur de graphiques et charge les données.

        Args :
        - db_path (str) : Chemin vers la base de données.
        - root_path (str) : Dossier de destination pour les rapports HTML.
        """
        super().__init__(db_path)
        self.__root_path = root_path
        self.__file_highcharts = []

        self.report_data_handler = ReportDataHandler()
        self.report_data_handler._create_annual_folders(self.__root_path, self._get_categorized_operations_df())


    # --- [ Flux Principal ] ---
    def generate_all_reports(self, two_last_year_only: bool):
        """
        Génère les bilans financiers annuels et mensuels à partir des opérations catégorisées.

        Cette méthode crée pour chaque année (ou uniquement pour les deux dernières si `last_year` est True) :
        - Des graphiques Sankey pour visualiser les flux financiers.
        - Des graphiques circulaires (sunburst) pour détailler la répartition des revenus et dépenses.
        - Des histogrammes empilés pour visualiser les dépenses par mois.

        Les fichiers HTML correspondants sont sauvegardés dans des dossiers par année.

        Args :
        - two_last_year_only (bool) : si True, génère les bilans pour les deux dernières années disponibles.
        """
        years_operations_categorisees = self._get_categorized_operations_by_year()

        # Créez les graphiques uniquement pour les 2 dernières années
        if two_last_year_only:
            two_last_years = list(years_operations_categorisees.keys())[-2:]
            years_operations_categorisees = {year: years_operations_categorisees[year] for year in two_last_years}

        # Regroupe toutes les opérations pour faire le bilan des différentes années
        all_operation_categorisees = pd.DataFrame()

        for year, operation_categorisees in years_operations_categorisees.items():
            self.__output_file = f"{self.__root_path}{year}/Bilan {year}.html"
            df_revenus = self.report_data_handler._get_income_df(operation_categorisees)
            df_depenses = self.report_data_handler._get_expense_df(operation_categorisees)
            all_operation_categorisees = pd.concat([all_operation_categorisees, operation_categorisees], ignore_index=True)

            self.__generate_annual_report(df_revenus, df_depenses, operation_categorisees)
            self.__generate_monthly_report(operation_categorisees, year)
            
        # Bilan de toutes les années
        annees = list(years_operations_categorisees.keys())
        self.__output_file = f"{self.__root_path}/Bilan {annees[0]}-{annees[-1]}.html"
        df_revenus = self.report_data_handler._get_income_df(all_operation_categorisees)
        df_depenses = self.report_data_handler._get_expense_df(all_operation_categorisees)
        self.__generate_annual_report(df_revenus, df_depenses, all_operation_categorisees)

    
    # --- [ Production des Bilans ] ---
    def __generate_annual_report(self, df_revenus: pd.DataFrame, df_depenses: pd.DataFrame, df_all: pd.DataFrame):
        """
        Crée les graphiques pour le bilan annuel selon la présence de revenus et/ou dépenses.

        Args :
            df_revenus (pd.DataFrame) : DataFrame des opérations de revenus.
            df_depenses (pd.DataFrame) : DataFrame des opérations de dépenses.
            df_all (pd.DataFrame) : DataFrame complet des opérations (revenus + dépenses).
        """

        if (not df_revenus.empty) and (not df_depenses.empty):
            self.__compte_courant_income_expenses(df_revenus, df_depenses, df_all)
        elif (not df_revenus.empty) and (df_depenses.empty):
            self.__compte_courant_income(df_revenus)
        else:
            self.__compte_courant_expenses(df_depenses)
            
    def __generate_monthly_report(self, df_all: pd.DataFrame, year: int):
        """
        Génère les graphiques mensuels pour le bilan d'une année donnée.

        Args :
            df_all (pd.DataFrame) : DataFrame complet des opérations financières de l'année.
            year (int) : Année pour laquelle les graphiques mensuels sont créés.
        """
        month_operations_categorisees = self.__get_categorized_month_operations(df_all)

        for month, operations_categorisees in month_operations_categorisees.items():
            self.__output_file = f"{self.__root_path}{year}/{year}-{month}.html"
            df_revenus_month = self.report_data_handler._get_income_df(operations_categorisees)
            df_depenses_month = self.report_data_handler._get_expense_df(operations_categorisees)
            df_all_month = pd.concat([df_revenus_month, df_depenses_month], ignore_index=True)

            if (not df_revenus_month.empty) and (not df_depenses_month.empty):
                self.__compte_courant_income_expenses(df_revenus_month, df_depenses_month, df_all_month)
            elif (not df_revenus_month.empty) and (df_depenses_month.empty):
                self.__compte_courant_income(df_revenus_month)
            else:
                self.__compte_courant_expenses(df_depenses_month)


    # --- [ Traitement des Données ] ---
    def __compte_courant_income_expenses(self, df_revenus: pd.DataFrame, df_depenses: pd.DataFrame, df_all: pd.DataFrame):
        """
        Génère et organise les graphiques pour un compte courant avec revenus et dépenses.

        Args :
            df_revenus (pd.DataFrame) : DataFrame contenant les opérations de revenus.
            df_depenses (pd.DataFrame) : DataFrame contenant les opérations de dépenses.
            df_all (pd.DataFrame) : DataFrame combinant toutes les opérations (revenus + dépenses).

        Actions :
            - Crée un graphique Sankey pour l’ensemble des opérations.
            - Crée un histogramme empilé pour les dépenses.
            - Génère des graphiques circulaires des dépenses et des revenus,
            en séparant éventuellement les sous-catégories spécifiques (Investissement, Épargne, Virements internes).
            - Combine plusieurs graphiques côte à côte si nécessaire.
            - Sauvegarde tous les graphiques générés dans un fichier HTML.
        """
        self.__generate_html_file(df_all)

        # Filtrer les lignes où la colonne 'category' n'est pas 'Investissement' ni "Épargne"
        df_filtre = df_depenses[
            (df_depenses['category'] != 'Investissement') &
            (df_depenses['category'] != 'Épargne')
        ]
        # Vérifier si le DataFrame complet des revenus est identique au DataFrame filtré ou que le DataFrame filtré est vide
        if (df_depenses.equals(df_filtre)) or (df_filtre.empty):
            self.__create_pie_chart(df=df_depenses, name="Dépenses")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_depenses = self.__create_pie_chart(df=df_filtre, name="Dépenses", save=False)
            fig_soleil = self.__create_pie_chart(df=df_depenses, name="Dépenses + Investissement", save=False)
        
            # Création des graphiques dans l'ordre dans le fichier
            self.__create_combined_charts(fig_soleil_depenses, fig_soleil)
        
        # Filtrer les lignes où la colonne 'sub_category' n'est pas 'Virements internes'
        df_filtre = df_revenus[df_revenus['sub_category'] != 'Virements internes']
        # Vérifier si le DataFrame filtré est identique au DataFrame complet des revenus
        if df_filtre.equals(df_revenus):
            # Si les deux DataFrames sont identiques, créer un seul graphique
            self.__create_pie_chart(df=df_filtre, name="Revenus gagné")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_revenus = self.__create_pie_chart(df=df_filtre, name="Revenus gagné", save=False)
            fig_soleil_all_revenus = self.__create_pie_chart(df=df_revenus, name="Revenus gagné + Virements internes", save=False)
            
            # Création des graphiques combinés dans l'ordre
            self.__create_combined_charts(fig_soleil_revenus, fig_soleil_all_revenus)

        self.__save_in_file()

    def __compte_courant_expenses(self, df_depenses: pd.DataFrame):
        """
        Génère et organise les graphiques pour un compte courant ne contenant que des dépenses.

        Args :
            df_depenses (pd.DataFrame) : DataFrame contenant les opérations de dépenses.

        Actions :
            - Crée un histogramme empilé pour les dépenses.
            - Génère un graphique circulaire des dépenses, en séparant éventuellement la catégorie 'Investissement' et 'Épargne'.
            - Combine plusieurs graphiques côte à côte si nécessaire pour éviter les doublons.
            - Sauvegarde tous les graphiques générés dans un fichier HTML.
        """
        self.__generate_html_file(df_depenses)

        # Filtrer les lignes où la colonne 'category' n'est pas 'Investissement' ni "Épargne"
        df_filtre = df_depenses[
            (df_depenses['category'] != 'Investissement') &
            (df_depenses['category'] != 'Épargne')
        ]
        
        # Vérifier si le DataFrame complet des revenus est identique au DataFrame filtré ou que le DataFrame filtré est vide
        if (df_depenses.equals(df_filtre)) or (df_filtre.empty):
            self.__create_pie_chart(df=df_depenses, name="Dépenses")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_depenses = self.__create_pie_chart(df=df_filtre, name="Dépenses", save=False)
            fig_soleil = self.__create_pie_chart(df=df_depenses, name="Dépenses + Investissement", save=False)
        
            # Création des graphiques dans l'ordre dans le fichier
            self.__create_combined_charts(fig_soleil_depenses, fig_soleil)

        self.__save_in_file()

    def __compte_courant_income(self, df_revenus: pd.DataFrame):
        """
        Génère et organise les graphiques pour un compte courant contenant uniquement des revenus.

        Args :
            df_revenus (pd.DataFrame) : DataFrame contenant les opérations de revenus.

        Actions :
            - Génère un graphique circulaire des revenus gagnés, en séparant éventuellement les 'Virements internes'.
            - Combine plusieurs graphiques côte à côte si nécessaire pour éviter les doublons.
            - Sauvegarde tous les graphiques générés dans un fichier HTML.
        """
        self.__generate_html_file(df_revenus)
        # Filtrer les lignes où la colonne 'sub_category' n'est pas 'Virements internes'
        df_filtre = df_revenus[df_revenus['sub_category'] != 'Virements internes']
        
        # Vérifier si le DataFrame filtré est identique au DataFrame complet des revenus
        if df_filtre.equals(df_revenus):
            # Si les deux DataFrames sont identiques, créer un seul graphique
            self.__create_pie_chart(df=df_filtre, name="Revenus gagné")
        else:
            # Si les DataFrames ne sont pas identiques, créer deux graphiques
            fig_soleil_revenus = self.__create_pie_chart(df=df_filtre, name="Revenus gagné", save=False)
            fig_soleil_all_revenus = self.__create_pie_chart(df=df_revenus, name="Revenus gagné + Virements internes", save=False)
            
            # Création des graphiques combinés dans l'ordre
            self.__create_combined_charts(fig_soleil_revenus, fig_soleil_all_revenus)
        
        # Enregistrer les graphiques dans un fichier
        self.__save_in_file()

    def __save_in_file(self):
        """
        Enregistre tous les graphiques générés dans un fichier HTML.
        Accepte à la fois :
        - des figures Plotly (go.Figure)
        - du HTML brut (str)
        """
        with open(self.__output_file, "w", encoding="utf-8") as f:
            for item in self.__file_highcharts:
                if isinstance(item, str):
                    # HTML brut (ex: Highcharts)
                    f.write(item)
                else:
                    # Figure Plotly
                    item.write_html(f, include_plotlyjs="cdn")

        # Reset après écriture
        self.__file_highcharts = []


    # --- [ Génération de Graphiques ] ---
    @staticmethod
    def __create_sankey_chart(df_all: pd.DataFrame) -> str:
        """
        Génère le code HTML/JavaScript nécessaire pour afficher un diagramme de Sankey interactif.

        Cette méthode transforme un DataFrame de transactions en une structure de flux 
        "Source -> Cible" (links) compatible avec Highcharts. Le diagramme visualise 
        le cycle financier selon trois niveaux :
        1. Origines des revenus -> Nœud central "Revenus".
        2. Nœud central "Revenus" -> Catégories de dépenses.
        3. Catégories de dépenses -> Sous-catégories détaillées.

        Fonctionnalités incluses :
        - Filtrage dynamique par année via un menu déroulant (Select).
        - Tri automatique des dépenses par amount décroissant pour la lisibilité.
        - Gestion automatique des couleurs par branche (une couleur par catégorie de dépense).
        - Formatage des montants (valeurs absolues pour les dépenses et arrondi à 2 décimales).

        Args:
            df_all (pd.DataFrame): Données brutes contenant au minimum les colonnes 
                                   ['year', 'category', 'sub_category', 'amount'].

        Returns:
            str: Bloc de code HTML contenant le conteneur du graphique, le sélecteur 
                 d'année et le script JavaScript Highcharts injecté avec les données JSON.
        """
        # Génération d'un ID unique
        graph_id = "sankey_" + str(uuid.uuid4()).replace('-', '_')

        # Tri des années : reverse=True pour avoir la plus récente en premier
        years = sorted([int(y) for y in df_all['year'].unique()], reverse=True)
        multiple_years = len(years) > 1

        df_copy = df_all.copy()
        df_copy['operation_date'] = df_copy['operation_date'].astype(str)
        df_copy['amount'] = df_copy['amount'].astype(float)
        df_copy['year'] = df_copy['year'].astype(int)
        data_json = json.dumps(df_copy.to_dict(orient='records'), ensure_ascii=False)

        # Couleurs pour les flux
        colors = ["#544FC5", "#2CAFFE", "#FF7F50", "#32CD32", "#FF69B4","#FFA500","#8A2BE2","#00CED1","#DC143C","#7FFF00"]

        html = ""
        if multiple_years:
            html += '<h2>Choisir l\'année pour Sankey :</h2>'
            html += f'<select id="sankeyYearSelect_{graph_id}">'
            for i, y in enumerate(years):
                # On force "selected" sur le premier élément (l'année la plus récente)
                is_selected = "selected" if i == 0 else ""
                html += f'<option value="{y}" {is_selected}>{y}</option>'
            html += '</select>'

        html += f'<div id="sankeyContainer_{graph_id}" style="width:100%; height:950px; margin-top:20px;"></div>'

        html += f"""
            <script>
            (function() {{
                const sankeyData = {data_json};
                const sankeyColors = {json.dumps(colors)};
                const sankeyYears = {json.dumps(years)};
                const containerId = 'sankeyContainer_{graph_id}';
                const yearSelectId = 'sankeyYearSelect_{graph_id}';

                function round2(value) {{ return Math.round((value + Number.EPSILON) * 100) / 100; }}

                function buildSankeyLinks(selectedYear) {{
                    let links = [];
                    const filteredData = sankeyData.filter(d => d.year === selectedYear);

                    // --- Revenus ---
                    const revenus = filteredData.filter(d => d.category === "Revenus");
                    const revenus_souscat = {{}};
                    revenus.forEach(d => {{ revenus_souscat[d.sub_category] = (revenus_souscat[d.sub_category] || 0) + d.amount; }});
                    
                    Object.entries(revenus_souscat).forEach(([s, v]) => {{
                        links.push({{ from: s, to: "Revenus", weight: round2(v) }});
                    }});
                    
                    // --- Dépenses ---
                    const depenses = filteredData.filter(d => d.category !== "Revenus").map(d => ({{
                        ...d,
                        amount: Math.abs(d.amount)
                    }}));

                    const depCatsTotals = {{}};
                    depenses.forEach(d => {{ 
                        depCatsTotals[d.category] = (depCatsTotals[d.category] || 0) + d.amount; 
                    }});
                    
                    let sortedDepCats = Object.entries(depCatsTotals);
                    sortedDepCats.sort(([, a], [, b]) => b - a);

                    sortedDepCats.forEach(([cat, catTotal], idx) => {{
                        const color = sankeyColors[idx % sankeyColors.length];
                        
                        links.push({{ 
                            from: "Revenus", 
                            to: cat, 
                            weight: round2(catTotal), 
                            color: color 
                        }});

                        const subs = {{}};
                        depenses.filter(d => d.category === cat).forEach(d => {{ 
                            subs[d.sub_category] = (subs[d.sub_category] || 0) + d.amount; 
                        }});
                        
                        Object.entries(subs).forEach(([s, amt]) => {{
                            links.push({{ 
                                from: cat, 
                                to: s, 
                                weight: round2(amt), 
                                color: color 
                            }});
                        }});
                    }});

                    return links;
                }}

                function renderSankey(selectedYear) {{
                    // Si non défini, on prend la valeur du select ou la première année dispo
                    if(!selectedYear) {{
                        const selectEl = document.getElementById(yearSelectId);
                        selectedYear = selectEl ? parseInt(selectEl.value) : (sankeyYears.length > 0 ? sankeyYears[0] : null);
                    }}
                    
                    if(!selectedYear) return;
                    
                    const links = buildSankeyLinks(selectedYear);
                    
                    Highcharts.chart(containerId, {{
                        chart: {{ type: 'sankey', height: 850 }},
                        title: {{ text: 'Répartition des revenus et dépenses de ' + selectedYear }},
                        tooltip: {{
                            pointFormatter: function () {{
                                return this.toNode.name === 'Revenus' 
                                    ? this.fromNode.name + ': <b>' + this.weight.toFixed(2) + ' €</b>'
                                    : this.fromNode.name + ' \u2192 ' + this.toNode.name + ': <b>' + this.weight.toFixed(2) + ' €</b>';
                            }}
                        }},
                        series:[{{
                            keys: ['from', 'to', 'weight', 'color'],
                            data: links,
                            type: 'sankey',
                            dataLabels: {{
                                nodeFormatter: function() {{
                                    return this.point.name; 
                                }}
                            }}
                        }}]
                    }});
                }}

                const sankeySelect = document.getElementById(yearSelectId);
                if(sankeySelect) {{
                    sankeySelect.addEventListener('change', (e) => renderSankey(parseInt(e.target.value)));
                }}
                
                // Premier rendu automatique
                renderSankey();
            }})();
            </script>
        """
        return html
    
    def __create_pie_chart(self, df: pd.DataFrame, name: str, save: bool = True) -> go.Figure:
        """
        Crée un graphique circulaire (sunburst) représentant la répartition des montants par catégorie et sous-catégorie.

        Args :
            df (pd.DataFrame) : DataFrame contenant les opérations catégorisées.
            name (str) : nom du graphique ou du nœud racine.
            save (bool, optionnel) : indique si le graphique doit être sauvegardé dans la liste interne (par défaut True).

        Returns :
            go.Figure : objet figure Plotly contenant le graphique circulaire généré.
        """
        labels = [name]
        parents = ['']
        values = [df['amount'].sum()]

        for category in df['category'].unique():
            labels.append(category)
            parents.append(name)
            values.append(df[df['category'] == category]['amount'].sum())

            for type_op in df[df['category'] == category]['sub_category'].unique():
                labels.append(type_op)
                parents.append(category)
                values.append(df[(df['category'] == category) & (df['sub_category'] == type_op)]['amount'].sum())

        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues='total',
            textinfo='label+percent entry'
        ))
        fig.update_layout(
            showlegend=True,
            width=1800,
            height=900,
            margin=dict(l=200, r=100, t=50, b=50)
        )
        if save:
            self.__file_highcharts.append(fig)
        return fig

    @staticmethod
    def __create_income_expense_evolution_chart(df_all: pd.DataFrame) -> str:
        """
        Génère un tableau de bord interactif Highcharts avec bascule Revenus/Dépenses.

        Cette méthode produit un graphique hybride (Colonnes + Courbes) permettant 
        d'analyser l'évolution financière selon deux axes temporels (Annuel ou Mensuel) 
        et deux niveaux de granularité (Total ou par Catégorie).

        Architecture des données :
        1.  **Bascule (Switch)** : Permute entre les données de 'Revenus' et de 'Dépenses'.
        2.  **Modes de vue** :
            -   'Par année' : Affiche l'évolution globale sur toutes les années disponibles.
            -   'Par mois' : Affiche le détail des 12 mois pour une année spécifique.
        3.  **Granularité** : 
            -   Vue Totale : Une seule barre par période (somme agrégée).
            -   Vue Catégories : Barres empilées (stacked columns) triées par ordre alphabétique.
        4.  **Indicateurs d'analyse** :
            -   Ligne de moyenne : Calculée dynamiquement selon les catégories visibles.
            -   Ligne de variation (%) : Calcule le taux de croissance entre deux périodes.

        Args:
            df_all (pd.DataFrame): DataFrame contenant les colonnes 'operation_date', 
                                   'category', 'sub_category' et 'amount'.

        Returns:
            str: Fragment HTML/JS complet incluant le CSS personnalisé (switch toggle), 
                 les contrôles d'interface (radio, select) et la logique Highcharts.
        """
        # Préparation des dates
        df_all["operation_date"] = pd.to_datetime(df_all["operation_date"]) 
        df_all["year"] = df_all["operation_date"].dt.year
        df_all["month"] = df_all["operation_date"].dt.month

        # MODIFICATION : Tri décroissant pour le menu (le graphique gère son propre tri)
        years = sorted(df_all["year"].unique().tolist(), reverse=True)
        months_labels = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Août','Sep','Oct','Nov','Déc']

        # --- Séparation des données : Revenus vs Dépenses ---
        df_rev = df_all[df_all['category'] == 'Revenus']
        df_dep = df_all[df_all['category'] != 'Revenus']

        datasets = {
            'revenus': {'data': {}, 'categories': sorted(df_rev['sub_category'].unique().tolist())},
            'depenses': {'data': {}, 'categories': sorted(df_dep['category'].unique().tolist())}
        }

        def fill_data(sub_df, type_key, is_revenu):
            cat_col = 'sub_category' if is_revenu else 'category'
            for cat in datasets[type_key]['categories']:
                datasets[type_key]['data'][cat] = {}
                # On utilise years_graph (croissant) pour la structure de données interne
                years_internal = sorted(years)
                for y in years_internal:
                    vals = sub_df[(sub_df[cat_col]==cat) & (sub_df.year==y)] \
                        .groupby('month')['amount'].sum().abs() \
                        .reindex(range(1,13), fill_value=0).tolist()
                    datasets[type_key]['data'][cat][y] = [round(v, 2) for v in vals]

        fill_data(df_rev, 'revenus', True)
        fill_data(df_dep, 'depenses', False)

        data_json = json.dumps(datasets)
        months_json = json.dumps(months_labels)
        # On passe les années triées de façon croissante pour l'axe X du graphique
        years_json = json.dumps(sorted(years)) 

        graph_id = "switch_" + str(uuid.uuid4()).replace('-', '_')

        html = f"""
            <style>
                .switch-container_{graph_id} {{ display: flex; align-items: center; margin-bottom: 15px; }}
                .switch_{graph_id} {{ position: relative; display: inline-block; width: 50px; height: 26px; margin-right: 10px; }}
                .switch_{graph_id} input {{ opacity: 0; width: 0; height: 0; }}
                .slider_{graph_id} {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #2CAFFE; transition: .4s; border-radius: 34px; }}
                .slider_{graph_id}:before {{ position: absolute; content: ""; height: 18px; width: 18px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }}
                input:checked + .slider_{graph_id} {{ background-color: #544FC5; }} 
                input:focus + .slider_{graph_id} {{ box-shadow: 0 0 1px #544FC5; }}
                input:checked + .slider_{graph_id}:before {{ transform: translateX(24px); }}
                .switch-label_{graph_id} {{ font-weight: bold; font-size: 16px; margin-right: 20px; }}
            </style>

            <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                <div class="switch-container_{graph_id}">
                    <span class="switch-label_{graph_id}" id="label_switch_{graph_id}">Dépenses</span>
                    <label class="switch_{graph_id}">
                        <input type="checkbox" id="typeSwitch_{graph_id}">
                        <span class="slider_{graph_id}"></span>
                    </label>
                    
                    <span style="border-left: 2px solid #ccc; margin: 0 15px; height: 20px;"></span>

                    <label><input type="radio" name="mode_{graph_id}" value="year" checked> Par année</label>
                    <label style="margin-left:10px;"><input type="radio" name="mode_{graph_id}" value="month"> Par mois</label>
                    
                    <select id="yearSelect_{graph_id}" style="display:none; margin-left:10px;">
                        {''.join([f'<option value="{y}" {"selected" if i==0 else ""}>{y}</option>' for i, y in enumerate(years)])}
                    </select>

                    <label style="margin-left:20px;">
                        <input type="checkbox" id="subCategoryCheckbox_{graph_id}"> Afficher les catégories
                    </label>
                </div>

                <div id="container_{graph_id}" style="width:100%; height:875px;"></div>
            </div>

            <script>
            (function() {{
                const fullData = {data_json};
                const months = {months_json};
                const years = {years_json}; // Toujours croissant pour l'axe X
                const graphId = '{graph_id}';
                
                const container = document.getElementById(`container_${{graphId}}`);
                const typeSwitch = document.getElementById(`typeSwitch_${{graphId}}`);
                const labelSwitch = document.getElementById(`label_switch_${{graphId}}`);
                const yearSelect = document.getElementById(`yearSelect_${{graphId}}`);
                const subCategoryCheckbox = document.getElementById(`subCategoryCheckbox_${{graphId}}`);
                
                let currentType = 'depenses';
                let mode = 'year';
                let chart;

                function round2(value) {{ return Math.round((value + Number.EPSILON) * 100) / 100; }}

                function calculatePctChange(values) {{
                    let result = Array(values.length).fill(null);
                    for(let i=1; i<values.length; i++) {{
                        const prev = values[i-1];
                        const current = values[i];
                        if (Math.abs(prev) > 0.01) {{
                            result[i] = round2(((current - prev) / prev) * 100);
                        }}
                    }}
                    return result;
                }}
                
                function getAggregatedTotals(seriesNamesToAggregate) {{
                    const activeData = fullData[currentType].data;
                    let totals;
                    
                    if (mode === 'year') {{
                        totals = years.map(y => {{
                            return seriesNamesToAggregate.reduce((s, cat) => {{
                                if (activeData[cat] && activeData[cat][y]) {{
                                    return s + activeData[cat][y].reduce((a, b) => a + b, 0);
                                }}
                                return s;
                            }}, 0);
                        }});
                    }} else {{
                        const selectedYear = parseInt(yearSelect.value) || years[years.length - 1];
                        totals = Array.from({{length: 12}}, (_, i) => {{
                            return seriesNamesToAggregate.reduce((s, cat) => {{
                                if (activeData[cat] && activeData[cat][selectedYear]) {{
                                    return s + (activeData[cat][selectedYear][i] || 0);
                                }}
                                return s;
                            }}, 0);
                        }});
                    }}
                    return totals.map(v => round2(v));
                }}
                
                function updateAvgAndPct(chartInstance) {{
                    let namesToAggregate;
                    if (subCategoryCheckbox.checked) {{
                        const seriesColumn = chartInstance.series.filter(s => s.options.type === 'column' && s.visible);
                        namesToAggregate = seriesColumn.length === 0 ? [] : seriesColumn.map(s => s.name);
                    }} else {{
                        namesToAggregate = fullData[currentType].categories;
                    }}

                    const totals = getAggregatedTotals(namesToAggregate);
                    const avgVal = totals.length > 0 ? round2(totals.reduce((a, b) => a + b, 0) / totals.length) : 0;
                    
                    const sAvg = chartInstance.series.find(s => s.userOptions.id === 'avg_line');
                    if(sAvg) {{
                        sAvg.update({{ name: mode === 'year' ? 'Moyenne Annuelle' : 'Moyenne Mensuelle', data: Array(totals.length).fill(avgVal) }}, false);
                    }}
                    
                    const sPct = chartInstance.series.find(s => s.userOptions.id === 'pct_line');
                    if(sPct) {{
                        sPct.setData(calculatePctChange(totals), false);
                    }}
                    chartInstance.redraw();
                }}

                function buildSeries(selectedYear, showSub) {{
                    let columnSeries = []; 
                    let lineSeries = [];  
                    let initialTotals;
                    
                    const activeData = fullData[currentType].data;
                    const activeCats = fullData[currentType].categories;
                    const baseColor = currentType === 'revenus' ? '#544FC5' : '#2CAFFE'; 
                    
                    if(showSub) {{
                        activeCats.forEach(cat => {{
                            const data_cat = mode==='year' ? 
                                years.map(y => activeData[cat][y] ? activeData[cat][y].reduce((a,b)=>a+b,0) : 0) : 
                                (activeData[cat][selectedYear] || Array(12).fill(0));

                            columnSeries.push({{
                                id: 'cat_' + cat.replace(/\s+/g, '_'), 
                                name: cat, 
                                type: 'column', 
                                data: data_cat.map(round2), 
                                stack: 'total',
                                showInLegend: true
                            }});
                        }});
                    }} else {{
                        initialTotals = getAggregatedTotals(activeCats); 
                        columnSeries.push({{
                            id: 'series_total_sum',
                            name: currentType === 'revenus' ? 'Total Revenus' : 'Total Dépenses',
                            type: 'column',
                            data: initialTotals,
                            color: baseColor,
                            showInLegend: true
                        }});
                    }}

                    columnSeries.sort((a, b) => a.name.localeCompare(b.name));
                    if (!initialTotals) initialTotals = getAggregatedTotals(activeCats);

                    const avgVal = initialTotals.length > 0 ? round2(initialTotals.reduce((a,b)=>a+b,0)/initialTotals.length) : 0;
                    lineSeries.push({{
                        name: mode === 'year' ? 'Moyenne Annuelle' : 'Moyenne Mensuelle', 
                        type: 'line', 
                        data: Array(initialTotals.length).fill(avgVal), 
                        color: '#ff4d4d', dashStyle: 'Dot', marker:{{enabled:false}},
                        id: 'avg_line', zIndex: 10,
                        showInLegend: false
                    }});

                    if(mode==='year') {{
                        lineSeries.push({{
                            name: 'Variation', 
                            type: 'line', 
                            data: calculatePctChange(initialTotals), 
                            yAxis: 1, 
                            color: '#00E272', 
                            marker:{{enabled:true,symbol:'circle',radius:4}},
                            zones:[{{value:0,color:'#FF0000'}},{{color:'#00E272'}}],
                            id: 'pct_line', 
                            zIndex: 10,
                            showInLegend: false
                        }});
                    }}
                    
                    return columnSeries.concat(lineSeries);
                }}

                function renderChart(resetLegend = false, forceRecalculateLines = false) {{
                    mode = document.querySelector(`input[name="mode_${{graphId}}"]:checked`).value;
                    const showSub = subCategoryCheckbox.checked;
                    const selectedYear = parseInt(yearSelect.value);
                    
                    labelSwitch.innerText = currentType === 'revenus' ? 'Revenus' : 'Dépenses';
                    labelSwitch.style.color = currentType === 'revenus' ? '#544FC5' : '#2CAFFE';

                    const categoriesAxis = mode==='year' ? years.map(y=>y.toString()) : months;
                    const titleText = `Evolution des ${{currentType}} (${{mode==='year' ? 'Annuel' : 'Mensuel ' + selectedYear}})`;
                    
                    const options = {{
                        chart: {{ type: 'column' }},
                        title: {{ text: titleText }},
                        xAxis: {{ categories: categoriesAxis, crosshair: true }},
                        yAxis: [
                            {{ title: {{ text: 'Montant (€)' }}, labels: {{ format: '{{value:.2f}} €' }} }},
                            {{ title: {{ text: 'Variation (%)' }}, opposite: true, labels: {{ format: '{{value:.1f}} %' }} }}
                        ],
                        tooltip: {{ 
                            shared: false, valueDecimals: 2,
                            formatter: function() {{
                                let s = `<span style="font-size: 10px">${{this.key}}</span><br/>`;
                                if (this.series.name === 'Variation') {{
                                    s += `<span style="color:${{this.y>=0?'#2ecc71':'#ff4d4d'}}">\u25CF</span> ${{this.series.name}}: <span style="color:${{this.y>=0?'#2ecc71':'#ff4d4d'}}"><b>${{this.y>0?'+':''}}${{this.y.toFixed(1)}}%</span></b>`;
                                }} else {{
                                    s += `<span style="color:${{this.series.color}}">\u25CF</span> ${{this.series.name}}: <b>${{this.y.toFixed(2)}} €</b>`;
                                }}
                                return s;
                            }}
                        }},
                        plotOptions: {{
                            column: {{ stacking: showSub ? 'normal' : undefined }},
                            series: {{
                                events: {{
                                    legendItemClick: function() {{
                                        setTimeout(() => updateAvgAndPct(this.chart), 50);
                                    }}
                                }}
                            }}
                        }},
                        series: buildSeries(selectedYear, showSub)
                    }};

                    if (chart) {{
                        chart.update(options, true, true); 
                        if(resetLegend || forceRecalculateLines) updateAvgAndPct(chart);
                    }} else {{
                        chart = Highcharts.chart(container, options);
                    }}
                }}

                typeSwitch.addEventListener('change', (e) => {{
                    currentType = e.target.checked ? 'revenus' : 'depenses';
                    renderChart(true, true);
                }});

                subCategoryCheckbox.addEventListener('change', () => renderChart(true, true));
                
                document.querySelectorAll(`input[name="mode_${{graphId}}"]`).forEach(r => r.addEventListener('change', (e) => {{
                    yearSelect.style.display = e.target.value==='month' ? 'inline' : 'none';
                    renderChart(true, true);
                }}));
                
                yearSelect.addEventListener('change', () => renderChart(false, true));

                renderChart();
            }})();
            </script>
            """
        return html
    
    def __create_combined_charts(self, fig1: go.Figure, fig2: go.Figure, save: bool = True) -> go.Figure:
        """
        Combine deux graphiques sunburst côte à côte dans une seule figure.

        Args :
            fig1 (go.Figure) : premier graphique sunburst.
            fig2 (go.Figure) : second graphique sunburst.
            save (bool, optionnel) : indique si la figure combinée doit être sauvegardée dans la liste interne (par défaut True).

        Returns :
            go.Figure : objet figure Plotly contenant les deux graphiques combinés.
        """
        fig_combined = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "sunburst"}, {"type": "sunburst"}]]
        )

        for trace in fig1.data:
            fig_combined.add_trace(trace, row=1, col=1)
        for trace in fig2.data:
            fig_combined.add_trace(trace, row=1, col=2)

        fig_combined.update_layout(
            showlegend=True,
            width=1800,
            height=900,
            margin=dict(l=200, r=100, t=50, b=50)
        )
        if save:
            self.__file_highcharts.append(fig_combined)
        return fig_combined

    @staticmethod
    def __create_income_expense_bar_chart(df_all: pd.DataFrame) -> str:
        """
        Génère un histogramme comparatif empilé (Stacked Bar Chart) pour l'analyse globale.

        Cette méthode est le pivot de l'analyse comparative. Elle permet de visualiser 
        simultanément les flux entrants (Revenus) et sortants (Dépenses) afin d'en 
        déduire l'épargne nette.

        Logique de construction :
        1.  **Agrégation multiniveau** : Les données sont groupées par catégorie, 
            sous-catégorie, puis par année et mois pour créer un dictionnaire JSON 
            profond consommé par le front-end.
        2.  **Double Empilage (Stacks)** : 
            -   'revenus' : Toutes les séries de revenus sont empilées dans une colonne dédiée.
            -   'depenses' : Toutes les catégories de dépenses sont empilées dans une seconde colonne.
            -   Cela permet de comparer visuellement la hauteur des deux colonnes côte à côte.
        3.  **Indicateur d'Épargne Nette** : Une ligne dynamique calcule la différence 
            (Revenus - Dépenses) pour chaque période. La ligne change de couleur 
            automatiquement (Rouge si négatif, Vert si positif).
        4.  **Modes d'affichage** :
            -   Vue Annuelle : Évolution globale sur l'historique complet.
            -   Vue Mensuelle : Focus sur une année spécifique sélectionnée via menu déroulant.
            -   Vue Détaillée : Option pour ventiler les colonnes par catégories/sous-catégories.

        Args:
            df_all (pd.DataFrame): Données transactionnelles avec colonnes 'operation_date', 
                                   'category', 'sub_categories' et 'amount'.

        Returns:
            str: Code HTML/JS complet intégrant le sélecteur d'année, les options de vue 
                 et le graphique Highcharts avec calcul automatique de l'épargne.
        """
        df_all["year"] = df_all["operation_date"].dt.year
        df_all["month"] = df_all["operation_date"].dt.month

        # Construction de la structure DATA
        data_dict = {}
        for cat, cat_df in df_all.groupby('category'):
            data_dict[cat] = {}
            for sub_cat, sub_df in cat_df.groupby("sub_category"):
                data_dict[cat][sub_cat] = {}
                for year, year_df in sub_df.groupby("year"):
                    # Calcul de la somme mensuelle.
                    monthly = year_df.groupby(year_df["operation_date"].dt.month)['amount'].sum().abs().reindex(range(1,13), fill_value=0).tolist()
                    data_dict[cat][sub_cat][int(year)] = [round(m, 2) for m in monthly]

        json_data = json.dumps(data_dict, indent=2)

        html = f"""
            <div class="controls">
            <label><input type="radio" name="viewMode" value="years" checked /> Années</label>
            <label><input type="radio" name="viewMode" value="months" /> Mois</label>
            <select id="yearSelect" style="display:none; padding: 5px;"></select>
            <label style="margin-left: 20px;"><input type="checkbox" id="showCategories" /> Afficher les catégories</label>
            </div>

            <div id="container" style="width:100%; height:875px"></div>

            <script>
            const DATA = {json_data};
            let chart;
            let viewMode = 'years';
            let showCategories = false;

            const months = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Août','Sep','Oct','Nov','Déc'];

            function round_amount(v) {{
                return Math.round((v + Number.EPSILON) * 100) / 100;
            }}

            function getAllYears() {{
                const yearSet = new Set();
                Object.keys(DATA).forEach(cat => {{
                    Object.values(DATA[cat]).forEach(sub => {{
                        Object.keys(sub).forEach(y => yearSet.add(Number(y)));
                    }});
                }});
                // MODIFICATION ICI : Tri décroissant (reverse) pour le menu
                return Array.from(yearSet).sort((a,b) => b - a);
            }}

            let allYears = getAllYears();
            // MODIFICATION ICI : On sélectionne l'index 0 (l'année la plus élevée après le tri)
            let selectedYear = allYears.length > 0 ? allYears[0] : new Date().getFullYear();

            function buildSeries() {{
                let categories = [];
                let columnSeries = []; 

                if (viewMode === 'years') {{
                    // Pour le graphique en mode années, on garde l'ordre chronologique (croissant)
                    categories = [...allYears].sort((a,b) => a - b);

                    if (showCategories) {{
                        Object.keys(DATA).filter(c => c !== 'Revenus').forEach(cat => {{
                            const subCats = Object.keys(DATA[cat]);
                            const data = categories.map(y =>
                                round_amount(subCats.reduce((s,sub) => s + (DATA[cat][sub][y]?.reduce((a,b)=>a+b,0) || 0), 0))
                            );
                            columnSeries.push({{ name: cat, type: 'column', stack: 'depenses', data }});
                        }});

                        if (DATA.Revenus) {{
                            Object.keys(DATA.Revenus).forEach(sub => {{
                                const data = categories.map(y =>
                                    DATA.Revenus[sub][y] ? round_amount(DATA.Revenus[sub][y].reduce((a,b)=>a+b,0)) : 0
                                );
                                if (data.some(v=>v!==0)) {{
                                    columnSeries.push({{ name: sub, type: 'column', stack: 'revenus', data }});
                                }}
                            }});
                        }}
                    }} else {{
                        columnSeries.push({{
                            name: 'Dépenses', type: 'column', stack: 'depenses', color: '#2CAFFE',
                            data: categories.map(y => round_amount(Object.keys(DATA).filter(c=>c!=='Revenus').reduce((s,c)=> s + Object.values(DATA[c]).reduce((s2,sub)=> s2 + (sub[y]?.reduce((a,b)=>a+b,0) || 0),0),0)))
                        }});
                        columnSeries.push({{
                            name: 'Revenus', type: 'column', stack: 'revenus', color:'#544FC5',
                            data: categories.map(y => round_amount(DATA.Revenus ? Object.values(DATA.Revenus).reduce((s,sub)=> s + (sub[y]?.reduce((a,b)=>a+b,0) || 0),0) : 0))
                        }});
                    }}
                }} else {{
                    categories = months;
                    if (showCategories) {{
                        Object.keys(DATA).filter(c=>c!=='Revenus').forEach(cat => {{
                            const subCats = Object.keys(DATA[cat]).filter(sub => DATA[cat][sub][selectedYear]);
                            if(!subCats.length) return;
                            columnSeries.push({{
                                name: cat, type:'column', stack:'depenses',
                                data: months.map((_,i)=> round_amount(subCats.reduce((s,sub)=> s + (DATA[cat][sub][selectedYear]?.[i] || 0),0)))
                            }});
                        }});
                        if (DATA.Revenus) {{
                            Object.keys(DATA.Revenus).filter(sub => DATA.Revenus[sub][selectedYear]).forEach(sub => {{
                                columnSeries.push({{
                                    name: sub, type:'column', stack:'revenus',
                                    data: DATA.Revenus[sub][selectedYear].map(v => round_amount(v))
                                }});
                            }});
                        }}
                    }} else {{
                        columnSeries.push({{
                            name:'Dépenses', type:'column', stack:'depenses', color: '#2CAFFE',
                            data: months.map((_,i)=> round_amount(Object.keys(DATA).filter(c=>c!=='Revenus').reduce((s,c)=> s + Object.values(DATA[c]).reduce((s2,sub)=> s2 + (sub[selectedYear]?.[i] || 0),0),0)))
                        }});
                        columnSeries.push({{
                            name:'Revenus', type:'column', stack:'revenus', color:'#544FC5',
                            data: months.map((_,i)=> round_amount(DATA.Revenus ? Object.values(DATA.Revenus).reduce((s,sub)=> s + (sub[selectedYear]?.[i] || 0),0) : 0))
                        }});
                    }}
                }}

                columnSeries.sort((a, b) => a.name.localeCompare(b.name));
                let series = columnSeries; 

                series.push({{
                    name:'Épargne nette', type:'line', yAxis:1, color:'#00E272',
                    data: categories.map(()=>0), lineWidth:2,
                    marker:{{enabled:true,symbol:'circle',radius:4}},
                    zones:[{{value:0,color:'#FF0000'}},{{color:'#00E272'}}]
                }});

                return {{ categories, series }};
            }}

            function updateNetSavings() {{
                const net = chart.series.find(s=>s.name==='Épargne nette');
                if(!net) return;
                const revenus = chart.series.filter(s=>s.visible && s.options.stack==='revenus');
                const depenses = chart.series.filter(s=>s.visible && s.options.stack==='depenses');
                const data = chart.xAxis[0].categories.map((_,i)=> {{
                    const r = revenus.reduce((s,ser)=> s + (ser.data[i] ? (ser.data[i].y !== undefined ? ser.data[i].y : ser.data[i]) : 0), 0);
                    const d = depenses.reduce((s,ser)=> s + (ser.data[i] ? (ser.data[i].y !== undefined ? ser.data[i].y : ser.data[i]) : 0), 0);
                    return round_amount(r - d);
                }});
                net.setData(data,true);
            }}

            function renderChart() {{
                const data = buildSeries();
                if (!chart) {{
                    chart = Highcharts.chart('container', {{
                        chart: {{ type:'column' }},
                        title: {{ text: 'Analyse Financière' }},
                        xAxis: {{ categories: data.categories, crosshair: true }},
                        yAxis:[ {{ title:{{text:'Montant (€)'}} }}, {{ title:{{text:'Épargne nette (€)'}}, opposite:true }} ],
                        tooltip: {{
                            shared: false, useHTML: true,
                            formatter: function() {{
                                const color_montant = this.y >= 0 ? '#00E272' : '#FF0000';
                                let tooltipHtml = `<span style="color:${{color_montant}}">\u25CF</span> <b>${{this.series.name}}</b><br/>` +
                                                `Montant: <b style="color:${{color_montant}}">${{this.y}} €</b>`;
                                if(this.series.name === 'Épargne nette' && viewMode === 'years') {{
                                    const index = this.point.index;
                                    if (index > 0) {{
                                        const prevY = this.series.points[index - 1].y;
                                        if (prevY && prevY !== 0) {{
                                            const change = ((this.y - prevY) / Math.abs(prevY)) * 100;
                                            const color_v = change >= 0 ? '#00E272' : '#FF0000';
                                            tooltipHtml += `<br/>Variation: <b style="color:${{color_v}}">${{change > 0 ? '+' : ''}}${{change.toFixed(1)}}%</b>`;
                                        }}
                                    }}}}
                                return tooltipHtml;
                            }}
                        }},
                        plotOptions: {{ column: {{ stacking:'normal' }}, series: {{ events: {{ legendItemClick: () => setTimeout(updateNetSavings, 50) }} }} }},
                        series: data.series
                    }});
                }} else {{
                    while(chart.series.length) chart.series[0].remove(false);
                    data.series.forEach(s=>chart.addSeries(s,false));
                    chart.xAxis[0].setCategories(data.categories,false);
                    chart.redraw();
                }}
                updateNetSavings();
            }}

            // --- GESTION DU MENU DÉROULANT ---
            const yearSelect = document.getElementById('yearSelect');
            allYears.forEach((y, index) => {{
                const opt = document.createElement('option');
                opt.value = y;
                opt.text = y;
                if (index === 0) opt.selected = true; // Sélectionne l'année la plus récente
                yearSelect.appendChild(opt);
            }});

            yearSelect.onchange = () => {{
                selectedYear = Number(yearSelect.value);
                renderChart();
            }};

            document.querySelectorAll('input[name="viewMode"]').forEach(r => r.onchange = () => {{
                viewMode = r.value;
                document.getElementById('yearSelect').style.display = viewMode==='months' ? 'inline' : 'none';
                renderChart();
            }});

            document.getElementById('showCategories').onchange = (e) => {{
                showCategories = e.target.checked;
                renderChart();
            }};

            renderChart();
            </script>
        """
        return html
    
    def __generate_html_file(self, df_all: pd.DataFrame):
        """
        Assemble et compile l'ensemble des visualisations dans un document HTML unique.

        Cette méthode agit comme le moteur de rendu principal. Elle construit la structure 
        du document (DOM), importe les bibliothèques JavaScript nécessaires (Highcharts Core, 
        Sankey et Exporting) et concatène les sorties des différentes méthodes de génération 
        de graphiques.

        L'ordre d'affichage dans le document est le suivant :
        1. Analyse Financière (Histogramme comparatif avec épargne nette).
        2. Évolution Revenus/Dépenses (Graphique avec switch interactif).
        3. Flux de trésorerie (Diagramme de Sankey).

        Args:
            df_all (pd.DataFrame): Le jeu de données complet contenant les transactions 
                                   nécessaires à l'alimentation des trois modules graphiques.
        """
        html = """
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <title>Graphiques</title>
            <script src="https://code.highcharts.com/highcharts.js"></script>
            <script src="https://code.highcharts.com/modules/sankey.js"></script>
            <script src="https://code.highcharts.com/modules/exporting.js"></script>
            </head>
            <body>
        """
        html += self.__create_income_expense_bar_chart(df_all)
        html += self.__create_income_expense_evolution_chart(df_all)
        html += self.__create_sankey_chart(df_all)
        html += "</body></html>"

        self.__file_highcharts.append(html)


    # --- [ Récupération des Données ] ---
    @staticmethod
    def __get_categorized_month_operations(df_all: pd.DataFrame) -> dict:
        """
        Regroupe les opérations catégorisées par mois.

        Args :
        - df_all (pd.DataFrame) : DataFrame contenant les opérations catégorisées, 
                                avec une colonne 'operation_date' de type datetime.

        Returns :
        - dict : dictionnaire { mois (str) : DataFrame des opérations de ce mois }
        """
        # Extraction de l'année
        df_all["month"] = df_all["operation_date"].dt.strftime('%m')

        month_dict = {}

        # Groupement par année
        for year, df_annee in df_all.groupby("month"):
            month_dict[year] = df_annee.reset_index(drop=True)

        return month_dict
