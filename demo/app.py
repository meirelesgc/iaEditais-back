import streamlit as st
import pandas as pd

from streamlit_pdf_viewer import pdf_viewer
from hooks import source, taxonomy, order
from datetime import datetime


st.set_page_config(
    page_title='Demonstração da API',
    layout='wide',
    initial_sidebar_state='expanded',
    page_icon='📄',
)

POST_SOURCE = DELETE_SOURCE = False
CREATE_TAXONOMY = POST_TAXONOMY = DELETE_TAXONOMY = PUT_TAXONOMY = False
CREATE_ORDER = CREATE_RELEASE = DELETE_RELEASE = False
NUM = 0
tab1, tab2, tab3 = st.tabs(['📌 Fontes', '🧵 Tipificações', '📊 Análise'])


def format_date(date_str):
    if isinstance(date_str, str):
        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    return None


with tab1:

    @st.dialog('➕ Adicionar Fonte')
    def create_source():
        name = st.text_input('Nome da fonte')
        description = st.text_area('Descrição da fonte')
        uploaded_file = st.file_uploader('Escolha um arquivo PDF', type='pdf')

        if st.button('Enviar'):
            if name and description:
                source.post_source(name, description, uploaded_file)
            else:
                st.toast('Por favor, preencha todos os campos.')

    sources = source.get_source()

    container = st.container()
    a, b = container.columns([6, 1])
    a.subheader('📌 Gestão de Fontes')
    if b.button('➕ Adicionar', use_container_width=True):
        create_source()

    st.divider()

    if not sources:
        st.error('Nenhuma fonte encontrada.')

    for _, fonte in enumerate(sources):
        container = st.container()
        a, b = container.columns([6, 1])

        a.subheader(f'{_ + 1} - {fonte["name"]}')
        if b.button(
            '🗑️ Excluir', key=f'exclude_{fonte["id"]}', use_container_width=True
        ):
            source.delete_source(fonte['id'])

        with st.expander(f'📄 Detalhes da Fonte - ID: {fonte["id"]}'):
            st.write(f'**Criado em:** {format_date(fonte["created_at"])}')
            st.write(f'**Descrição da fonte:** {fonte["description"]}')
            update_at = (
                format_date(fonte['updated_at'])
                if fonte['updated_at']
                else 'N/A'
            )
            st.write(f'**Atualizado em:** {update_at}')
            if fonte['has_file']:
                st.divider()
                pdf_viewer(
                    input=source.get_source_file(fonte['id']),
                    key=f'pdf_viewer_{fonte["id"]}',
                    width='100%',
                )

with tab2:

    @st.dialog('Criar tipificação')
    def create_tipyfication():
        with st.form(key='create_tipyfication_form'):
            name = st.text_input('Nome da Tipificação')
            selected_sources = st.multiselect(
                'Fontes', sources, format_func=lambda x: x['name']
            )
            if st.form_submit_button('Criar Tipificação'):
                taxonomy.post_typification(name, selected_sources)

    @st.dialog('✏️ Atualizar Tipificação')
    def update_tipyfication(typ):
        with st.form(key='update_tipyfication_form'):
            default_sources = [s for s in sources if s['id'] in typ['source']]
            typ['name'] = st.text_input(
                'Nome da Tipificação',
                value=typ['name'],
            )
            selected_sources = st.multiselect(
                'Fontes',
                sources,
                format_func=lambda x: x['name'],
                default=default_sources,
            )
            typ['source'] = [s['id'] for s in selected_sources]
            if st.form_submit_button('Atualizar Tipificação'):
                taxonomy.put_typification(typ)

    @st.dialog('➕ Criar Taxonomia')
    def create_taxonomy(typ):
        with st.form(key='create_taxonomy_form'):
            title = st.text_input('Título da Taxonomia')
            description = st.text_area('Descrição da Taxonomia')
            selected_sources = st.multiselect(
                'Fontes', sources, format_func=lambda x: x['name'][:-4]
            )
            post_sources = [s['id'] for s in selected_sources]
            if st.form_submit_button('Criar Taxonomia'):
                taxonomy.post_taxonomy(
                    typ['id'],
                    title,
                    description,
                    post_sources,
                )

    @st.dialog('✏️ Atualizar Taxonomia')
    def update_taxonomy(tax):
        with st.form(key='update_taxonomy_form'):
            tax['title'] = st.text_input('Título da Taxonomia')
            tax['description'] = st.text_area('Descrição da Taxonomia')
            tax['sources'] = st.multiselect(
                'Fontes',
                sources,
                format_func=lambda x: x['name'][:-4],
                default=tax['source'],
            )
            if st.form_submit_button('Atualizar Taxonomia'):
                taxonomy.put_taxonomy(tax)

    @st.dialog('➕ Criar Ramo')
    def create_branch(taxonomy_id):
        with st.form(key='create_branch_form'):
            title = st.text_input('Título da Taxonomia')
            description = st.text_area('Descrição da Taxonomia')
            if st.form_submit_button('Criar Ramo'):
                taxonomy.post_branch(taxonomy_id, title, description)

    @st.dialog('✏️ Editar Ramo')
    def edit_branch(taxonomy_id):
        branches = taxonomy.get_branches_by_taxonomy_id(taxonomy_id)
        branch = st.selectbox(
            'Ramo',
            branches,
            key='branch_select',
            format_func=lambda x: x['id'],
        )
        if branch:
            with st.form(key='edit_branch_form'):
                branch['title'] = st.text_input(
                    'Título da Taxonomia',
                    value=branch['title'],
                )

                branch['description'] = st.text_area(
                    'Descrição da Taxonomia',
                    branch['description'],
                )

                if st.form_submit_button('Criar Ramo'):
                    taxonomy.post_branch(branch)

    @st.fragment
    def taxonomy_form(typ):
        st.subheader('📜 Gestão de Taxonomias')
        title = st.text_input('📝 Título:')
        description = st.text_area('📝 Descrição:')
        selected_sources = st.multiselect(
            '📌 Fontes:',
            options=sources,
            format_func=lambda x: x['name'],
        )
        if st.button(
            '➕ Adicionar', use_container_width=True, key='add_taxonomy_button'
        ):
            selected_sources = [s['id'] for s in selected_sources]
            taxonomy.post_taxonomy(
                typ['id'], title, description, selected_sources
            )

    @st.fragment
    def taxonomy_list(typ):
        taxonomies = taxonomy.get_taxonomy(typ['id'])
        if not taxonomies:
            st.error('Nenhuma taxonomia encontrada.')
        for tax in taxonomies:
            st.title(f'{tax["title"]}')
            with st.expander(f'🆔 {tax["id"][:8]}'):
                taxonomy_details(tax)

    @st.fragment
    def taxonomy_details(tax):
        title = st.text_input(
            'Titulo:', value=tax['title'], key=f'title_{tax["id"]}'
        )
        description = st.text_area('Descrição:', value=tax['description'])
        pre_selected_sources = [s for s in sources if s['id'] in tax['source']]
        selected_sources = st.multiselect(
            'Fontes',
            options=sources,
            key=f'source_{tax["id"]}',
            format_func=lambda s: s['name'],
            default=pre_selected_sources,
        )
        if st.button(
            '✏️ Atualizar',
            use_container_width=True,
            key=f'update_taxonomy_button_{tax["id"]}',
        ):
            tax['title'] = title
            tax['description'] = description
            tax['source'] = [s['id'] for s in selected_sources]
            taxonomy.put_taxonomy(tax)
        st.subheader(f'Criado em: {tax["created_at"]}')
        update_at = tax['updated_at'] if tax['updated_at'] else 'N/A'
        st.subheader(f'Atualizado em: {update_at}')
        st.divider()
        branch_management(tax)

    @st.fragment
    def branch_management(tax):
        st.subheader('🔍 Lista de ramos')
        title = st.text_input('Nome do ramo:', key=f'title_input_{tax["id"]}')
        description = st.text_area(
            'Descrição do ramo:', key=f'description_input_{tax["id"]}'
        )
        if st.button('➕ Adicionar', key=f'add_branch_{tax["id"]}'):
            taxonomy.post_branch(tax['id'], title, description)
        branches = taxonomy.get_branches_by_taxonomy_id(tax['id'])
        if not branches:
            st.error('Nenhum ramo encontrado.')
        else:
            branches = pd.DataFrame(branches)
            new_branches = st.data_editor(
                branches,
                use_container_width=True,
                hide_index=True,
                column_config={'taxonomy_id': None, 'id': None},
                disabled=['created_at', 'updated_at'],
            )
            if st.button(
                '✏️ Atualizar (Apague o nome do ramo para Excluir)',
                key=f'update_branch_{tax["id"]}',
            ):
                for _, branch in new_branches.iterrows():
                    if not branch['title']:
                        taxonomy.delete_branch(branch['id'])
                    else:
                        taxonomy.put_branch(branch.to_dict())

    @st.dialog('Visão detalhada', width='large')
    def open_taxonomy(typ):
        taxonomy_form(typ)
        st.divider()
        taxonomy_list(typ)

    typifications = taxonomy.get_typifications()

    container = st.container()
    a, b = container.columns([6, 1])
    a.subheader('🧵 Gestão de Tipificações')
    st.divider()
    if b.button(
        '➕ Adicionar', use_container_width=True, key='add_typification'
    ):
        create_tipyfication()

    for _, typ in enumerate(typifications):
        container = st.container()
        a, b, c = container.columns([5, 1, 1])
        a.subheader(f'{typ["name"]}')
        if b.button(
            '🔍 Abrir',
            key=f'open_{typ["id"]}',
            use_container_width=True,
        ):
            open_taxonomy(typ)
        if c.button(
            '🗑️ Remover',
            key=f'delete_{typ["id"]}_externo',
            use_container_width=True,
        ):
            taxonomy.delete_typification(typ['id'])
        with st.expander('📝 Detalhes'):
            container = st.container()
            a, b = container.columns([4, 1])
            a.subheader(f'🆔 {typ["id"][:8]}')

            name = st.text_input('🧵 Nome:', value=typ['name'])

            pre_selected_sources = [
                s for s in sources if s['id'] in typ['source']
            ]
            selected_sources = st.multiselect(
                '📌 Fontes:',
                options=sources,
                format_func=lambda x: x['name'],
                default=pre_selected_sources,
            )
            if st.button(
                '✏️ Atualizar',
                use_container_width=True,
                key=f'update_{typ["id"]}_externo',
            ):
                typ['name'] = name
                typ['source'] = [s['id'] for s in selected_sources]
                taxonomy.put_typification(typ)

with tab3:
    st.subheader('📊 Gestão de Editais')
    orders = order.get_order()

    @st.dialog('➕ Adicionar Edital')
    def create_order():
        with st.form(key='create_order_form'):
            name = st.text_input('Nome do edital')
            type = st.multiselect(
                'Tipo do edital',
                options=typifications,
                format_func=lambda t: t['name'],
            )
            if st.form_submit_button('Adicionar Edital'):
                order.post_order(name, type)
                st.success('Edital criado com sucesso!')

    @st.dialog('Adicionar Versão')
    def create_release(ord):
        uploaded_file = st.file_uploader('Escolha um arquivo PDF', type='pdf')
        if st.button('Enviar arquivo') and uploaded_file:
            order.post_release(uploaded_file, ord['id'])

    @st.dialog('Visualizar Versões', width='large')
    def show_release(release):
        st.header(f'Release ID: {release["id"]}')
        for taxonomy in release['taxonomy']:
            st.subheader(f'Taxonomia: {taxonomy["title"]}')
            st.write(taxonomy['description'])

            for branch in taxonomy['branches']:
                st.markdown(f'### {branch["title"]}')
                st.write(branch['description'])

                taxonomy_score = next(
                    (
                        t
                        for t in release['taxonomy_score']
                        if t['id'] == taxonomy['id']
                    ),
                    None,
                )
                if taxonomy_score:
                    branch_score = next(
                        (
                            b
                            for b in taxonomy_score['branches']
                            if b['id'] == branch['id']
                        ),
                        None,
                    )
                    if branch_score:
                        st.write(f'**Feedback:** {branch_score["feedback"]}')
                        st.write(
                            f'**Cumprido:** {"✅ Sim" if branch_score["fulfilled"] else "❌ Não"}'
                        )
                        st.markdown('---')

    container = st.container()
    a, b = container.columns([6, 1])
    a.button('🔍 Lista de Editais', use_container_width=True)
    if b.button('➕ Adicionar Edital', use_container_width=True):
        create_order()

    st.subheader('📜 Lista de Editais')
    if not orders:
        st.error('Nenhum edital encontrado.')

    for ord in orders:
        container = st.container()
        a, b = container.columns([6, 1])
        a.button(ord['name'], use_container_width=True)
        if b.button('🗑️ Remover Edital', use_container_width=True):
            order.delete_order(ord['id'])

        with st.expander(f'📄 Detalhes do Edital - ID: {ord["id"]}'):
            st.write(f'**Criado em:** {format_date(ord["created_at"])}')
            update_at = (
                format_date(ord['updated_at']) if ord['updated_at'] else 'N/A'
            )
            st.write(f'**Atualizado em:** {update_at}')
            st.divider()

            if st.button(
                '➕ Adicionar Versão',
                key=f'add_version_{ord["id"]}',
                use_container_width=True,
            ):
                create_release(ord)
            ord = order.get_detailed_order(ord['id'])
            ord['releases'] = sorted(
                ord['releases'],
                key=lambda x: x['created_at'],
            )
            for release in ord['releases']:
                container = st.container()
                a, b = container.columns([6, 1])

                if a.button(
                    f'📄 Detalhes da análise - ID: {release["id"]}',
                    key=f'show_versions_{release["id"]}',
                    use_container_width=True,
                ):
                    show_release(release)
                b.button(
                    format_date(release['created_at']),
                    use_container_width=True,
                )
