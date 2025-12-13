import math
import pandas as pd
import plotly.graph_objects as go


class SankeyGenerator:
    """
    Classe pour générer un diagramme de Sankey représentant les flux financiers.

    Fonctionnalités :
    - Les sous-catégories de "Revenus" sont placées à gauche.
    - Un nœud "Revenus total" est positionné au centre.
    - Les catégories de dépenses (hors "Revenus") sont triées par montant et placées au centre-droite.
    - Les sous-catégories de chaque catégorie sont placées à droite, regroupées sous leur catégorie parent.

    Chaque flux relie :
    - les sous-catégories de revenus → le total des revenus,
    - le total des revenus → les catégories de dépenses,
    - les catégories de dépenses → leurs sous-catégories.

    Arguments du constructeur :
    - df (pd.DataFrame) : DataFrame contenant au minimum les colonnes ['categorie', 'sous_categorie', 'montant'].
    - title (str, optionnel) : titre du diagramme Sankey.
    """
    
    def __init__(self, df: pd.DataFrame, title: str = ""):
        for col in ("categorie", "sous_categorie", "montant"):
            assert col in df.columns, f"DataFrame must contain column '{col}'"

        self.__df = df.copy()
        # On utilise les valeurs absolues pour déterminer l'épaisseur des flux
        self.__df["montant_abs"] = self.__df["montant"].abs()
        self.__title = title

        # Listes et dictionnaires internes pour construire le Sankey
        self.__labels = []
        self.__label_index = {}
        self.__sources = []
        self.__targets = []
        self.__values = []

        # Construction de la structure des nœuds et des liens, puis création de la figure
        self.__build_structure()
        self.__build_figure()


    def __add_label(self, label: str) -> int:
        """
        Ajoute une étiquette (label) à la liste interne si elle n'existe pas encore.

        Args:
        - label (str) : le nom de l'étiquette à ajouter

        Returns:
        - int : l'index de l'étiquette dans la liste `self.__labels`, qu'elle ait été ajoutée ou déjà existante.
        """
        if label not in self.__label_index:
            self.__label_index[label] = len(self.__labels)
            self.__labels.append(label)
        return self.__label_index[label]

    @staticmethod
    def __even_spread(n, margin=0.1) -> list[float]:
        """
        Calcule des positions uniformément réparties sur l'intervalle [margin, 1-margin].

        Args:
        - n (int) : nombre de positions à générer
        - margin (float, optionnel) : marge à laisser de chaque côté de l'intervalle (défaut 0.1)

        Returns:
        - list[float] : liste des positions uniformes
        """
        if n <= 1:
            return [0.5]
        step = (1.0 - 2 * margin) / (n - 1)
        return [margin + i * step for i in range(n)]

    def __build_structure(self):
        """
        Construit la structure des nœuds et des liens pour le diagramme Sankey.

        - Sépare les revenus et les dépenses.
        - Calcule les totaux par sous-catégorie et par catégorie.
        - Génère les labels pour les nœuds (gauche, centre, droite).
        - Crée les liens (sources → cibles) avec les valeurs correspondantes.
        - Calcule les positions x et y pour chaque nœud pour un affichage esthétique :
            - Sous-catégories de revenus à gauche
            - Total des revenus au centre
            - Catégories de dépenses à droite
            - Sous-catégories de dépenses à droite, réparties autour de la catégorie parent
        """
        # Séparer revenus / dépenses
        df_revenus = self.__df[self.__df["categorie"] == "Revenus"]
        df_depenses = self.__df[self.__df["categorie"] != "Revenus"]

        # Totaux par sous-catégorie de revenus (gauche)
        revenus_by_sub = df_revenus.groupby("sous_categorie")["montant_abs"].sum()
        revenus_by_sub = revenus_by_sub.sort_values(ascending=False)  # décroissant (top = plus gros)

        # total revenus (pour label central)
        total_revenus = revenus_by_sub.sum()

        # Totaux par catégorie (hors Revenus) triés décroissant
        cat_totals = df_depenses.groupby("categorie")["montant_abs"].sum()
        cat_totals = cat_totals.sort_values(ascending=False)

        # Sous-catégories par catégorie (droite), triées décroissant
        sous_by_cat = {}
        for cat, grp in df_depenses.groupby("categorie"):
            sous = grp.groupby("sous_categorie")["montant_abs"].sum().sort_values(ascending=False)
            sous_by_cat[cat] = sous

        # ---- création des nœuds ----
        # gauche : chaque sous-catégorie de revenus
        left_sub_labels = []
        for sous, val in revenus_by_sub.items():
            label = f"{sous}: {val:.2f} €"
            left_sub_labels.append((sous, label, val))
            self.__add_label(label)

        # centre : revenus total
        revenus_total_label = f"Revenus: {total_revenus:.2f} €"
        revenus_total_idx = self.__add_label(revenus_total_label)

        # centre-droite : catégories (triées décroissant)
        cat_label_map = {}
        for cat, val in cat_totals.items():
            label = f"{cat}: {val:.2f} €"
            cat_label_map[cat] = label
            self.__add_label(label)

        # droite : sous-catégories finales (groupées sous chaque catégorie)
        sous_label_map = {}  # key (cat, sous) -> label_idx
        for cat, sous_series in sous_by_cat.items():
            for sous, val in sous_series.items():
                label = f"{sous}: {val:.2f} €"
                idx = self.__add_label(label)
                sous_label_map[(cat, sous)] = idx

        # ---- liens ----
        # A) chaque sous-categorie de revenus (gauche) -> revenus total
        left_indexes = []
        for sous, label, val in left_sub_labels:
            left_idx = self.__label_index[label]
            left_indexes.append((left_idx, val))
            self.__sources.append(left_idx)
            self.__targets.append(revenus_total_idx)
            self.__values.append(round(val, 2))

        # B) revenus total -> chaque catégorie (montant = total per category)
        for cat, val in cat_totals.items():
            cat_idx = self.__label_index[cat_label_map[cat]]
            self.__sources.append(revenus_total_idx)
            self.__targets.append(cat_idx)
            self.__values.append(round(val, 2))

        # C) chaque catégorie -> ses sous-catégories (droite)
        for cat, sous_series in sous_by_cat.items():
            cat_idx = self.__label_index[cat_label_map[cat]]
            for sous, val in sous_series.items():
                sous_idx = sous_label_map[(cat, sous)]
                self.__sources.append(cat_idx)
                self.__targets.append(sous_idx)
                self.__values.append(round(val, 2))

        # ---- positions x/y pour esthétique et tri décroissant pour catégories ----
        n_left = len(left_indexes)
        n_cat = len(cat_totals)

        # x positions par couche
        x_left = 0.02
        x_center = 0.35
        x_cat = 0.62
        x_right = 0.92

        # y positions :
        # - catégories : tri décroissant, on veut la plus grande en haut => y small -> top
        if n_cat > 0:
            cat_ys = self.__even_spread(n_cat, margin=0.08)  # de haut (0.08) à bas (0.92)
        else:
            cat_ys = []

        # construire mapping cat -> y
        cat_list = list(cat_totals.index)
        cat_y_map = {cat: cat_ys[i] for i, cat in enumerate(cat_list)}

        # left (sous revenus) : on tri par montant décroissant et on répartit top->bottom
        left_sorted = sorted(left_indexes, key=lambda t: -t[1])  # déjà trié mais on s'assure
        left_ys = self.__even_spread(n_left, margin=0.08)
        # associer left idx -> y
        left_y_map = {left_sorted[i][0]: left_ys[i] for i in range(n_left)}

        # right (sous-catégories) : on place chaque sous-cat autour du y de sa catégorie
        # si une catégorie a k sous-cats on les répartit autour du y de la catégorie sur une petite fenêtre
        right_positions = {}
        for cat in cat_list:
            sous_series = sous_by_cat.get(cat, pd.Series(dtype=float))
            k = len(sous_series)
            if k == 0:
                continue
            base_y = cat_y_map[cat]
            # small band height depends on k
            band = min(0.12, 0.12 * k)  # garde la bande raisonnable
            band_margin = band / 2.0
            sub_ys = []
            if k == 1:
                sub_ys = [base_y]
            else:
                # spread inside [base_y - band_margin, base_y + band_margin]
                step = (2 * band_margin) / (k - 1)
                sub_ys = [base_y - band_margin + i * step for i in range(k)]
            for i, (sous, val) in enumerate(sous_series.items()):
                idx = self.__label_index[f"{sous}: {val:.2f} €"]
                right_positions[idx] = sub_ys[i]

        # build final node_x & node_y arrays in label order
        total_nodes = len(self.__labels)
        node_x = [0.5] * total_nodes
        node_y = [0.5] * total_nodes

        # assign left x/y
        for idx, y in left_y_map.items():
            node_x[idx] = x_left
            node_y[idx] = y

        # assign revenus_total
        node_x[revenus_total_idx] = x_center
        # positionner le revenus_total au centre vertical (ou pondéré)
        node_y[revenus_total_idx] = 0.5

        # assign categories x/y
        for cat, label in cat_label_map.items():
            idx = self.__label_index[label]
            node_x[idx] = x_cat
            node_y[idx] = cat_y_map[cat]

        # assign right subcategories x/y
        for idx, y in right_positions.items():
            node_x[idx] = x_right
            node_y[idx] = y

        # fallback pour nœuds non positionnés (rare)
        for i in range(total_nodes):
            if math.isnan(node_x[i]) or math.isnan(node_y[i]):  # shouldn't happen but safe
                node_x[i] = 0.5
                node_y[i] = 0.5

    def __build_figure(self):
        """
        Construit la figure Sankey à partir des nœuds et des liens précédemment définis.

        - Utilise Plotly pour créer le diagramme.
        - Configure les propriétés des nœuds (labels, espacement, épaisseur, contours).
        - Associe les liens aux sources, cibles et valeurs correspondantes.
        - Met à jour la mise en page : titre, taille, marges et taille de police.
        - Stocke la figure finale dans `self.figure` pour un affichage ou une exportation ultérieure.
        """
        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        label=self.__labels,
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                    ),
                    link=dict(
                        source=self.__sources,
                        target=self.__targets,
                        value=self.__values,
                    ),
                )
            ]
        )

        fig.update_layout(
            title_text=self.__title,
            title_x=0.5,
            font_size=11,
            width=1800,
            height=900,
            margin=dict(l=80, r=80, t=70, b=50),
        )

        self.figure = fig


    def get_figure(self) -> go.Figure:
        """
        Renvoie la figure Sankey construite précédemment.

        Returns:
        - go.Figure : l'objet figure Plotly contenant le diagramme Sankey prêt à être affiché ou exporté.
        """
        return self.figure
