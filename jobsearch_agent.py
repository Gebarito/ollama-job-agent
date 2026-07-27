from ddgs import DDGS
import ollama
from pypdf import PdfReader

llm_model = 'qwen3:0.6b'

job_match_data = {
    "Job title": ["Engenheiro"],
    "Company name": ["Teste"],
    "ATS Rate": ["90%"],
    "url": ["http://google.com"]
}

def job_search(query: str, max: int = 5) -> list[str]:
    results = DDGS().text(query, max_results=max)
    return results

def get_compatible_position(cv: str) -> str:
    response = ollama.chat(model=llm_model, messages=[
        {
            "role": "system",
            "content": (
                "Você é um classificador de currículos. Sua única tarefa é extrair "
                "o cargo mais compatível com o currículo fornecido.\n\n"
                "REGRAS OBRIGATÓRIAS:\n"
                "- Responda APENAS com o nome do cargo, em português do Brasil.\n"
                "- NÃO escreva frases, explicações, saudações ou pontuação final.\n"
                "- NÃO use verbos, artigos, ou nomes de pessoas.\n"
                "- A resposta deve ter no máximo 5 palavras.\n"
                "- Formato de saída: apenas o título do cargo, nada mais.\n\n"
                "Exemplos:\n"
                "Currículo: 'Desenvolvedor com 5 anos em Python e Django...'\n"
                "Resposta: Engenheiro de Software\n\n"
                "Currículo: 'Gestão de folha de pagamento, recrutamento...'\n"
                "Resposta: Administrador de Recursos Humanos\n\n"
                "Currículo: 'Professor de matemática no ensino médio...'\n"
                "Resposta: Professor de Matemática"
            )
        },
        {"role": "user", "content": f"Currículo:\n{cv}\n\nResposta:"}
    ],
    options={"temperature": 0}
    )

    return response['message']['content']

def get_pdf_text(cv_file) -> str:
    reader = PdfReader(cv_file)
    file_size = reader.get_num_pages()
    output = ''
    for i in range(file_size):
        page = reader.pages[i]
        output += page.extract_text()

    return output

def make_query(position, options):
    sites = '(site:gupy.io OR site:glassdoor.com.br OR site:linkedin.com OR site:br.indeed.com OR site:nerdin.com.br OR site:vagas.com.br OR site:workday.com)'
    ddgs_query = f'{sites} "{position}" {options['modality']}'
    return ddgs_query

'''
    PUBLIC API
'''
def submit_cv(cv_file, options):
    cv_text = get_pdf_text(cv_file)
    search_position = get_compatible_position(cv_text)
    search_query = make_query(search_position, options)
    print(search_query)
    search_output = job_search(search_query, options['max'])

    return search_output
