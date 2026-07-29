import pandas as pd
import streamlit as st

import jobsearch_agent as agent

st.set_page_config(page_title='Ollama Job-FInder', page_icon='💼', layout='centered')

st.title(f'Ollama Job Finder')
st.subheader(f'Current LLM model: {agent.llm_model}')

cv_file = st.file_uploader('Faça upload do seu currículo em PDF', type=['PDF'])

max_open_time = st.selectbox(
    'Tempo máximo da vaga aberta:',
    ['1 dia', '1 semana', '1 mês', '1 ano']
)

modalities = st.multiselect(
    'Modalidade de trabalho:',
    ['Presencial', 'Remoto', 'Híbrido'],
    default=['Presencial', 'Remoto', 'Híbrido']
)

max_results = st.number_input('Quantidade máxima de vagas', min_value=1, max_value=200, value=10, step=1)

req = st.button('Buscar vagas')

if (req):
    if cv_file is not None:
        options = {
            'modality': modalities,
            'time': max_open_time,
            'max': max_results,
        }
        with st.spinner('Buscando vagas e calculando compatibilidade ATS...'):
            results = agent.submit_cv(cv_file, options)

        if results:
            df = pd.DataFrame(results)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Link': st.column_config.LinkColumn('Link', display_text='Abrir vaga'),
                },
            )
        else:
            st.warning('Nenhuma vaga encontrada com os filtros selecionados.')
    else:
        st.error('Você precisa submeter um arquivo.')
