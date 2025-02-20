import streamlit as st
from source import source
from methodology import branch, taxonomy, typification
from publication import publication


st.set_page_config(
    page_title="Ia Editais",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Base de conhecimento": [
        st.Page(source.main, title="Fontes", url_path="source", default=True),
    ],
    "Metodologia": [
        st.Page(typification.main, title="Tipificação", url_path="typification"),
        st.Page(taxonomy.main, title="Taxonomia", url_path="taxonomy"),
        st.Page(branch.main, title="Ramos", url_path="branch"),
    ],
    "Analise": [st.Page(publication.main, title="Publicações", url_path="publication")],
}

st.navigation(pages).run()
