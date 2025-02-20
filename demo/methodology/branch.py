import streamlit as st

from hooks import source, taxonomy
from datetime import datetime


def main():
    typifications = taxonomy.get_typifications()

    def format_date(date_str):
        if isinstance(date_str, str):
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        return None

    @st.dialog("Adicionar Ramo")
    def add_branch(tx):
        title = st.text_input("Nome do ramo:", key=f'title_input_{tx["id"]}')
        description = st.text_area(
            "Descrição do ramo:",
            key=f'description_input_{tx["id"]}',
        )
        if st.button("➕ Adicionar", key=f'add_branch_{tx["id"]}'):
            taxonomy.post_branch(tx["id"], title, description)

    @st.dialog("Atualizar Ramo")
    def update_branch(br):
        title = st.text_input(
            "Nome do ramo:",
            key=f'title_input_{br["id"]}',
            value=br["title"],
        )
        description = st.text_area(
            "Descrição do ramo:",
            key=f'description_input_{br["id"]}',
            value=br["description"],
        )
        if st.button("➕ Atualizar", key=f'update_branch_{br["id"]}'):
            br["title"] = title
            br["description"] = description
            taxonomy.put_branch(br)

    st.title("🪡 Gestão de Ramos")
    st.divider()

    st.subheader("🧵 Tipificação:")
    t = st.selectbox(
        "🧵 Tipificações:",
        options=typifications,
        format_func=lambda x: x["name"],
        label_visibility="collapsed",
    )
    taxonomy_list = taxonomy.get_taxonomy(t["id"]) if t else []

    st.subheader("🪢 Taxonomia:")
    tx = st.selectbox(
        "🪢 Taxonomia:",
        options=taxonomy_list,
        format_func=lambda x: x["title"],
        label_visibility="collapsed",
    )
    if st.button("➕ Adicionar", use_container_width=True, disabled=not bool(tx)):
        add_branch(tx)

    branch_list = taxonomy.get_branches(tx["id"]) if tx else []

    if not branch_list:
        st.error("Nenhum ramo encontrado.")

    for index, br in enumerate(branch_list):
        container = st.container()
        a, b, c = container.columns([5, 1, 1])
        a.header(f'{index + 1} - {br["title"]}')

        if b.button(
            "✏️ Atualizar",
            key=f'update_{br["id"]}',
            use_container_width=True,
        ):
            update_branch(br)
        if c.button(
            "🗑️ Excluir",
            key=f'delete_{br["id"]}_externo',
            use_container_width=True,
        ):
            taxonomy.delete_branch(br["id"])

        with st.expander("Detalhes"):
            st.subheader(f'Descrição {br["description"]}')
            st.subheader(f'Criado em: {format_date(t["created_at"])}')
            st.subheader(
                f'Atualizado em: {format_date(t["updated_at"]) if t["updated_at"] else "N/A"}'
            )
