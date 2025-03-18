import streamlit as st
from hooks import source, taxonomy
from datetime import datetime


def main():
    source_list = source.get_source()
    typifications = taxonomy.get_typifications()

    def format_date(date_str):
        if isinstance(date_str, str):
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
            return dt.strftime('%d/%m/%Y %H:%M:%S')
        return None

    @st.dialog('Adicionar Taxonomia', width='large')
    def create_taxonomy(t):
        st.button(
            f'🧵 Tipificação **{t["name"]}**',
            disabled=True,
            use_container_width=True,
        )
        title = st.text_input('📝 Título:')
        description = st.text_area('📝 Descrição:')
        selected_sources = st.multiselect(
            '📌 Fontes:',
            options=source_list,
            format_func=lambda x: x['name'],
        )
        if st.button(
            '➕ Adicionar', use_container_width=True, key='add_taxonomy_button'
        ):
            selected_sources = [s['id'] for s in selected_sources]
            taxonomy.post_taxonomy(
                t['id'], title, description, selected_sources
            )

    @st.dialog('Atualizar Taxonomia', width='large')
    def update_taxonomy(tx, t):
        st.button(
            f'🧵 Tipificação **{t["name"]}**',
            disabled=True,
            use_container_width=True,
        )
        title = st.text_input(
            'Titulo:', value=tx['title'], key=f'title_{tx["id"]}'
        )
        description = st.text_area('Descrição:', value=tx['description'])
        selected_sources = st.multiselect(
            'Fontes',
            options=source_list,
            key=f'source_{tx["id"]}',
            format_func=lambda s: s['name'],
            default=[s for s in source_list if s['id'] in tx['source']],
        )
        if st.button(
            '✏️ Atualizar',
            use_container_width=True,
            key=f'update_taxonomy_button_{tx["id"]}',
        ):
            tx['title'] = title
            tx['description'] = description
            tx['source'] = [s['id'] for s in selected_sources]
            taxonomy.put_taxonomy(tx)

    st.header('🪢 Gestão de Taxonomias')
    st.divider()

    st.subheader('🧵 Tipificação:')

    t = st.selectbox(
        '🧵 Tipificações:',
        options=typifications,
        format_func=lambda x: x['name'],
        label_visibility='collapsed',
    )
    if st.button('➕ Adicionar', use_container_width=True):
        create_taxonomy(t)

    taxonomy_list = taxonomy.get_taxonomy(t['id']) if t else []

    if not taxonomy_list:
        st.error('Nenhuma Taxonomia Encontrada.')

    for index, tx in enumerate(taxonomy_list):
        container = st.container()
        a, b, c = container.columns([5, 1, 1])
        a.subheader(f'{index + 1} - {tx["title"]}')

        if b.button(
            '✏️ Atualizar',
            key=f'update_{tx["id"]}',
            use_container_width=True,
        ):
            update_taxonomy(tx, t)
        if c.button(
            '🗑️ Excluir',
            key=f'delete_{tx["id"]}',
            use_container_width=True,
        ):
            taxonomy.delete_taxonomy(tx['id'])

        with st.expander('Detalhes'):
            st.subheader(f'Descrição: {tx["description"]}')
            st.subheader(
                f'Fontes: {", ".join([s["name"] for s in source_list if s["id"] in tx["source"]])}'
            )
            st.subheader(f'Criado em: {format_date(t["created_at"])}')
            st.subheader(
                f'Atualizado em: {format_date(t["updated_at"]) if t["updated_at"] else "N/A"}'
            )
