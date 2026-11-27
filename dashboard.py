"""Dashboard BigData Commerce Analytics (TP3).

Lancement, depuis la racine du projet :
    streamlit run dashboard.py
Les données viennent des datasets pseudonymisés data/analytique/*.parquet
(produits par le notebook atelier_jour3.ipynb). Aucun identifiant direct.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parent / "data" / "analytique"

st.set_page_config(page_title="BigData Commerce Analytics", layout="wide")


@st.cache_data
def charger_donnees():
    commandes = pd.read_parquet(DATA / "commandes_pseudo.parquet")
    paiements = pd.read_parquet(DATA / "paiements_pseudo.parquet")
    commandes["order_date"] = pd.to_datetime(commandes["order_date"], errors="coerce")
    paiements["payment_date"] = pd.to_datetime(paiements["payment_date"], errors="coerce")
    return commandes, paiements


commandes, paiements = charger_donnees()
paid = paiements[paiements["status"] == "PAID"]

# ---------- Navigation ----------
st.sidebar.title("BigData Commerce Analytics")
vue = st.sidebar.radio(
    "Navigation",
    ["Vue d'ensemble", "Catégories", "Encaissements", "Clients", "Exploration"],
)
st.sidebar.caption("Données fictives (DummyJSON) et paiements simulés. "
                   "Clients identifiés uniquement par un pseudonyme HMAC-SHA256.")

# ---------- Vue d'ensemble ----------
if vue == "Vue d'ensemble":
    st.title("Vue d'ensemble")

    ca_commandes = commandes["discounted_line_total"].sum()
    encaisse = paid["amount"].sum()
    nb_paniers = commandes["cart_id"].nunique()
    taux_acceptes = len(paid) / len(paiements) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA des commandes", f"{ca_commandes:,.0f}".replace(",", " "))
    c2.metric("Encaissements PAID", f"{encaisse:,.0f}".replace(",", " "))
    c3.metric("Nombre de paniers", nb_paniers)
    c4.metric("Paiements acceptés", f"{taux_acceptes:.1f} %")

    statuts = (paiements.groupby("status")
               .agg(nombre=("payment_id", "count"), montant=("amount", "sum"))
               .reset_index())
    fig = px.pie(statuts, names="status", values="nombre",
                 title="Répartition des statuts de paiement")
    st.plotly_chart(fig)
    st.dataframe(statuts.round(2), hide_index=True)

# ---------- Catégories ----------
elif vue == "Catégories":
    st.title("Chiffre d'affaires par catégorie")
    st.caption("Somme de discounted_line_total (après remise) par catégorie.")

    ca_cat = (commandes.groupby("category")["discounted_line_total"].sum()
              .round(2).sort_values().reset_index())
    nb = st.slider("Nombre de catégories affichées", 5, len(ca_cat), 10)
    fig = px.bar(ca_cat.tail(nb), x="discounted_line_total", y="category",
                 orientation="h",
                 labels={"discounted_line_total": "Chiffre d'affaires", "category": "Catégorie"})
    st.plotly_chart(fig)

# ---------- Encaissements ----------
elif vue == "Encaissements":
    st.title("Évolution mensuelle des encaissements")
    st.caption("Paiements PAID uniquement, par mois de payment_date (date synthétique).")

    mensuel = (paid.groupby(paid["payment_date"].dt.to_period("M").astype(str))
               .agg(montant=("amount", "sum"), paiements=("payment_id", "count"))
               .round(2).reset_index(names="mois"))
    fig = px.line(mensuel, x="mois", y="montant", markers=True,
                  labels={"mois": "Mois", "montant": "Montant encaissé"})
    st.plotly_chart(fig)
    st.dataframe(mensuel, hide_index=True)

# ---------- Clients ----------
elif vue == "Clients":
    st.title("Top clients pseudonymisés")
    st.caption("Somme des paiements PAID par user_id_pseudo.")

    nb = st.slider("Nombre de clients", 5, 30, 10)
    top = (paid.groupby("user_id_pseudo")["amount"].sum().round(2)
           .sort_values(ascending=False).head(nb).reset_index())
    top["client"] = top["user_id_pseudo"].str[:10] + "..."
    fig = px.bar(top.iloc[::-1], x="amount", y="client", orientation="h",
                 hover_data={"user_id_pseudo": True},
                 labels={"amount": "Montant encaissé", "client": "Client (pseudonyme)"})
    st.plotly_chart(fig)
    part = top["amount"].sum() / paid["amount"].sum() * 100
    st.write(f"Ces {nb} clients représentent **{part:.1f} %** des encaissements.")

# ---------- Exploration ----------
else:
    st.title("Exploration des données")
    source = st.radio("Données", ["Commandes", "Paiements"], horizontal=True)

    if source == "Commandes":
        cats = st.multiselect("Catégories", sorted(commandes["category"].unique()))
        d = commandes[commandes["category"].isin(cats)] if cats else commandes
    else:
        stats = st.multiselect("Statuts", sorted(paiements["status"].unique()))
        d = paiements[paiements["status"].isin(stats)] if stats else paiements

    st.write(f"{len(d)} lignes")
    st.dataframe(d, hide_index=True)