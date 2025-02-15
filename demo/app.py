import streamlit as st
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

tab1, tab2, tab3 = st.tabs(['📌 Fontes', '📂 Taxonomia', '📊 Análise'])


def format_date(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    return dt.strftime('%d/%m/%Y %H:%M:%S')


with tab1:
    st.subheader('📌 Gestão de Fontes')
    sources = source.get_source()

    @st.dialog('➕ Adicionar Fonte')
    def create_source():
        name = st.text_input('Nome da fonte')
        description = st.text_input('Descrição da fonte')
        uploaded_file = st.file_uploader('Escolha um arquivo PDF', type='pdf')

        if st.button('Enviar'):
            if name and description:
                source.post_source(name, description, uploaded_file)
            else:
                st.toast('Por favor, preencha todos os campos.')

    container = st.container()
    a, b = container.columns([6, 1])
    a.button('🔍 Fontes', use_container_width=True)
    if b.button('➕ Adicionar Fonte', use_container_width=True):
        create_source()

    st.subheader('📜 Lista de Fontes')
    if not sources:
        st.error('Nenhuma fonte encontrada.')

    for fonte in sources:
        container = st.container()
        a, b = container.columns([6, 1])
        a.button(fonte['name'], use_container_width=True)
        if b.button(
            '🗑️ Excluir', key=f'exclude_{fonte["id"]}', use_container_width=True
        ):
            source.delete_source(fonte['id'])
            st.toast('Fonte excluída com sucesso!', icon='🗑️')
        with st.expander(f'📄 Detalhes da Fonte - ID: {fonte["id"]}'):
            st.write(f'**Criado em:** {format_date(fonte["created_at"])}')
            st.write(f'**Descrição da fnte:** {fonte["description"]}')
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
    def create_taxonomy():
        with st.form(key='create_taxonomy_form'):
            title = st.text_input('Título da Taxonomia')
            description = st.text_area('Descrição da Taxonomia')
            selected_sources = st.multiselect(
                'Fontes', sources, format_func=lambda x: x['name'][:-4]
            )
            if st.form_submit_button('Criar Taxonomia'):
                taxonomy.post_taxonomy(title, description, selected_sources)

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

    st.subheader('🧵 Gestão de Tipificações')
    typifications = taxonomy.get_typifications()

    container = st.container()
    a, b = container.columns([6, 1])
    a.button('🔍 Tipificações', use_container_width=True)
    if b.button('➕ Criar Tipificação', use_container_width=True):
        create_tipyfication()

    for typ in typifications:
        container = st.container()
        a, b, c = container.columns([5, 1, 1])
        a.button(typ['name'], use_container_width=True, key=f'tax_{typ["id"]}')
        if b.button(
            '✏️ Atualizar',
            key=f'update_{typ["id"]}',
            use_container_width=True,
        ):
            update_tipyfication(typ)
        if c.button(
            '🗑️ Remover',
            key=f'delete_{typ["id"]}',
            use_container_width=True,
        ):
            taxonomy.delete_typification(typ['id'])
        with st.expander(f'📄 Detalhes da Tipificação - ID: {typ["id"]}'):
            expander_source = [
                s['name'] for s in sources if s['id'] in typ['source']
            ]
            st.write(f'**Fontes:** {expander_source}')

    st.subheader('📂 Gestão de Taxonomias')
    taxonomies = taxonomy.get_taxonomy()

    container = st.container()
    a, b = container.columns([6, 1])
    a.button('🔍 Taxonomias', use_container_width=True)
    if b.button('➕ Criar Taxonomia', use_container_width=True):
        create_taxonomy()

    st.subheader('📜 Lista de Taxonomias')
    if not taxonomies:
        st.error('Nenhuma taxonomia encontrada.')

    for tax in taxonomies:
        container = st.container()
        a, b, c = container.columns([5, 1, 1])
        a.button(
            tax['title'], use_container_width=True, key=f'tax_{tax["id"]}'
        )
        if b.button(
            '✏️ Atualizar',
            key=f'update_{tax["id"]}',
            use_container_width=True,
        ):
            update_taxonomy(tax)
            st.toast('Taxonomia atualizada com sucesso!', icon='✏️')
        if c.button(
            '🗑️ Remover',
            key=f'delete_{tax["id"]}',
            use_container_width=True,
        ):
            taxonomy.delete_taxonomy(tax['id'])
            st.toast('Taxonomia deletada com sucesso!', icon='🗑️')
        with st.expander(f'📄 Detalhes da Taxonomia - ID: {tax["id"]}'):
            st.write(f'**Descrição:** {tax["description"]}')
            st.write(f'**Criado em:** {format_date(tax["created_at"])}')
            update_at = (
                format_date(tax['updated_at']) if tax['updated_at'] else 'N/A'
            )
            st.write(f'**Atualizado em:** {update_at}')
            st.divider()
            container = st.container()
            a, b, c = container.columns([5, 1, 1])
            a.button(
                '🔍 Lista de ramos',
                use_container_width=True,
                key=f'list_branch_{tax["id"]}',
            )
            if b.button(
                '✏️ Editar ramos',
                use_container_width=True,
                key=f'edit_branch_{tax["id"]}',
            ):
                edit_branch(tax['id'])
            if c.button(
                '➕ Adicionar Ramo',
                use_container_width=True,
                key=f'add_branch_{tax["id"]}',
            ):
                create_branch(tax['id'])
            branches = taxonomy.get_branches_by_taxonomy_id(tax['id'])
            st.dataframe(
                branches,
                use_container_width=True,
            )

with tab3:
    st.subheader('📊 Gestão de Editais')
    orders = order.get_order()

    @st.dialog('➕ Adicionar Edital')
    def create_order():
        with st.form(key='create_order_form'):
            name = st.text_input('Nome do edital')
            type = st.text_input('Tipo do edital')
            if st.form_submit_button('Adicionar Edital'):
                order.post_order(name, type)
                st.success('Edital criado com sucesso!')

    @st.dialog('Adicionar Versão')
    def create_release(ord):
        uploaded_file = st.file_uploader('Escolha um arquivo PDF', type='pdf')
        taxonomies = st.multiselect(
            'Escolha uma ou mais taxonomias',
            options=taxonomy.get_taxonomy(),
            format_func=lambda x: x['title'],
        )
        if st.button('Enviar arquivo') and uploaded_file:
            order.post_release(uploaded_file, ord['id'], taxonomies)

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
