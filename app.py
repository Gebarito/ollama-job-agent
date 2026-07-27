import streamlit as st
import jobsearch_agent as agent

st.set_page_config(page_title='Ollama Job-FInder', page_icon='💼', layout='centered')

st.title(f'Ollama Job Finder')
st.subheader(f'Current LLM model: {agent.llm_model}')

cv_file = st.file_uploader('Faça upload do seu currículo em PDF', type=['PDF'])

max_open_time = st.selectbox(
    'Tempo máximo da vaga aberta:',
    ['1 dia', '3 dias', '1 semana', '1 mês', '3 meses', '6 meses']
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
        results = agent.submit_cv(cv_file, options)
        st.table(results, border='horizontal')
    else:
        st.error('Você precisa submeter um arquivo.')
