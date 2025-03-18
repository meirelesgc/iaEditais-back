import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from hooks import taxonomy, publication as order
from datetime import datetime


def main():
    typifications = taxonomy.get_typifications()

    def format_date(date_str):
        if isinstance(date_str, str):
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
            return dt.strftime('%d/%m/%Y %H:%M:%S')
        return None

    @st.dialog('Adicionar Edital', width='large')
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

    @st.dialog('Adicionar Versão', width='large')
    def create_release(ord):
        uploaded_file = st.file_uploader('Escolha um arquivo PDF', type='pdf')
        if st.button('Enviar arquivo') and uploaded_file:
            with st.status('Analisando versão...', expanded=True) as status:
                order.post_release(uploaded_file, ord['id'])
                status.update(label='Analise concluida!', state='complete')

    def show_release(r):
        for t in r['taxonomy']:
            st.caption('🧵 Tipificação:')
            st.caption(t['name'])
            for tx in t['taxonomy']:
                st.write('🪢 Taxonomia:')
                st.caption(tx['title'])
                for br in tx['branch']:
                    st.write('🪡 Ramo:')
                    st.caption(br['title'])
                    emote = '✅' if br['evaluate']['fulfilled'] else '❌'
                    st.write(f'Descrição: {br["description"]}')
                    st.write(f'Critério cumprido: {emote}')
                    st.write(f'Feedback: {br["evaluate"]["feedback"]}')
                    st.divider()

    st.header('📊 Gestão de Editais')
    st.divider()
    if st.button('➕ Adicionar Edital', use_container_width=True):
        create_order()

    orders = order.get_order()

    if not orders:
        st.error('Nenhum edital encontrado.')

    o = st.selectbox(
        'Selecione o edital', options=orders, format_func=lambda x: x['name']
    )

    if o:
        if st.button(
            '➕ Adicionar Versão',
            key=o['id'],
            use_container_width=True,
        ):
            create_release(o)

        if st.button(
            '🗑️ Excluir',
            use_container_width=True,
            key=f'delete_{o["id"]}',
        ):
            order.delete_order(o['id'])

        releases = sorted(
            order.get_release(o['id']) or [],
            key=lambda r: r['created_at'],
            reverse=True,
        )

        r = st.selectbox(
            'Selecione a versão',
            options=releases,
            format_func=lambda x: f'Edital {releases.index(x) + 1} - {format_date(x["created_at"])}',
        )
        if not releases:
            st.error('Nenhuma versão encontrada.')

        if r:
            col1, col2 = st.columns(2, gap='small')
            with col1:
                pdf_viewer(
                    input=order.get_release_file(r['id']),
                    key=f'pdf_viewer_{r["id"]}',
                    width='100%',
                    height=1200,
                )
            with col2:
                with st.container(height=1200):
                    show_release(r)
