class GraphiquesBase:
    """
    Classe de base pour les graphiques Plotly. Cette classe contient des paramètres généraux et des méthodes communes
    pour générer différents types de graphiques, tels que linéaire, circulaire, et sunburst.
    """

    @staticmethod
    def GenerateGraph(fig):
        """
        Méthode pour générer un graphique à partir de la figure donnée.

        Args:
            fig (go.Figure): La figure Plotly à utiliser pour générer le graphique.
        """
        
        fig.update_layout(
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            font=dict(color='white'),
        )
        
    