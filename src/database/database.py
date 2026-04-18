import os
import sqlite3
from contextlib import contextmanager

import pandas as pd


class Database:
    """Fournit une interface de base pour interagir avec une base de données SQLite."""

    def __init__(self, db_path: str):
        """Initialise la connexion et crée le dossier parent si nécessaire."""

        self._db_path = db_path

        # Création automatique du dossier si inexistant
        folder = os.path.dirname(self._db_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

    @contextmanager
    def _get_db(self):
        """
        Gestionnaire de contexte qui valide les modifications en cas de réussite,
        annule les modifications en cas d'erreur et se ferme systématiquement.
        """

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except sqlite3.Error as error:
            conn.rollback()
            print(f"Erreur SQL : {error}")
            raise
        finally:
            conn.close()

    def _get_table_df(self, table_name: str) -> pd.DataFrame:
        """Récupère toutes les données d'une table."""

        query = f'SELECT * FROM "{table_name}"'

        with self._get_db() as conn:
            return pd.read_sql_query(query, conn)

    def get_filtered_data(
        self, table_name: str, columns: list | None = None, filters: dict | None = None
    ) -> pd.DataFrame:
        """
        Récupère des colonnes spécifiques avec des filtres dans une table donnée.

        Args:
            table_name (str) : Le nom de la table SQL à interroger.
            columns (list, optional) : Liste des colonnes à récupérer.
                                       Si None, récupère toutes les colonnes (*).
            filters (dict, optional) : Dictionnaire {colonne: valeur} pour la clause WHERE.

        Returns:
            pd.DataFrame : Résultats de la requête sous forme de DataFrame.
        """

        # Construction de la sélection des colonnes
        if columns:
            column_selection = ", ".join([f'"{col}"' for col in columns])
        else:
            column_selection = "*"

        query = f'SELECT {column_selection} FROM "{table_name}"'
        params = []

        # Construction de la clause WHERE
        if filters:
            conditions = [f'"{key}" = ?' for key in filters.keys()]
            query += " WHERE " + " AND ".join(conditions)
            params = list(filters.values())

        with self._get_db() as conn:
            return pd.read_sql_query(query, conn, params=params)
