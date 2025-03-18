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

    @st.dialog('Criar tipificação', width='large')
    def create_tipyfication():
        with st.form(key='create_tipyfication_form'):
            name = st.text_input('Nome da Tipificação')
            selected_sources = st.multiselect(
                'Fontes', source_list, format_func=lambda x: x['name']
            )
            if st.form_submit_button('Criar Tipificação'):
                taxonomy.post_typification(name, selected_sources)

    @st.dialog('Atualizar Tipificação', width='large')
    def update_typification(t):
        name = st.text_input('🧵 Nome:', value=t['name'])
        selected_sources = st.multiselect(
            '📌 Fontes:',
            options=source_list,
            format_func=lambda x: x['name'],
            default=[s for s in source_list if s['id'] in t['source']],
        )

        if st.button(
            '✏️ Atualizar',
            key=f'update_{t["id"]}_externo',
        ):
            t['name'] = name
            t['source'] = [s['id'] for s in selected_sources]
            taxonomy.put_typification(t)

    st.header('🧵 Gestão de Tipificações')

    st.divider()
    if st.button('➕ Adicionar', use_container_width=True):
        create_tipyfication()

    if not typifications:
        st.error('Nenhuma tipificação encontrada.')

    for index, t in enumerate(typifications):
        container = st.container()
        a, b, c = container.columns([5, 1, 1])
        a.subheader(f'{index + 1} - {t["name"]}')

        if b.button(
            '✏️ Atualizar',
            key=f'update_{t["id"]}',
            use_container_width=True,
        ):
            update_typification(t)
        if c.button(
            '🗑️ Excluir',
            key=f'delete_{t["id"]}_externo',
            use_container_width=True,
        ):
            taxonomy.delete_typification(t['id'])

        with st.expander('Detalhes'):
            st.subheader(
                f'Fontes: {", ".join([s["name"] for s in source_list if s["id"] in t["source"]])}'
            )
            st.subheader(f'Criado em: {format_date(t["created_at"])}')
            st.subheader(
                f'Atualizado em: {format_date(t["updated_at"]) if t["updated_at"] else "N/A"}'
            )
