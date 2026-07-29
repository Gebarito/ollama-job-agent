import re
from urllib.parse import urlparse

import ollama
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from pypdf import PdfReader

llm_model = 'qwen3:0.6b'

TIME_FILTER_MAP = {
    '1 dia': 'd',
    '1 semana': 'w',
    '1 mês': 'm',
    '1 ano': 'y',
}
MIN_BODY_CHARS = 300

MAX_SCRAPE_CHARS = 6000

def job_search(query: str, max: int = 5, timelimit: str | None = None) -> list[dict]:
    results = DDGS().text(query, max_results=max, timelimit=timelimit)
    return results


def get_compatible_position(cv: str) -> str:
    response = ollama.chat(model=llm_model, messages=[
        {
            "role": "system",
            "content": (
                "Você é um classificador de currículos. Sua única tarefa é extrair "
                "os 3 cargos mais compatíveis com o currículo fornecido.\n\n"
                "REGRAS OBRIGATÓRIAS:\n"
                "- Responda APENAS o nome do cargo separado por uma vírgula (','), em português do Brasil.\n"
                "- NÃO escreva frases, explicações, saudações ou pontuação final.\n"
                "- NÃO use verbos, artigos, ou nomes de pessoas.\n"
                "- A resposta deve ter no máximo 20 palavras.\n"
                "- O título do cargo deve ser composto de no máximo 5 palavras, não use verbos.\n"
                "- Formato de saída: apenas os título do cargo separado por ',' , nada mais.\n\n"
                "Exemplos:\n"
                "Currículo: 'Desenvolvedor com 5 anos em Python e Django...'\n"
                "Resposta: Engenheiro de Software, Desenvolvedor Python, Desenvolvedor Web\n\n"
                "Currículo: 'Gestão de folha de pagamento, recrutamento...'\n"
                "Resposta: Administrador de Recursos Humanos, Gestor de Pagamento, Recrutador\n\n"
                "Currículo: 'Professor de matemática no ensino médio...'\n"
                "Resposta: Professor de Matemática, Professor, Professor Ensino Médio"
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
    sites = '(site:gupy.io OR site:nerdin.com.br OR site:vagas.com.br OR site:workday.com)'
    modalities = ' OR '.join(options['modality'])
    ddgs_query = f'{sites} {position} {modalities}'
    return ddgs_query


def scrape_page_text(url: str, timeout: int = 10, max_chars: int = MAX_SCRAPE_CHARS) -> str:
    """Abre o link da vaga e extrai o texto visível da página."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; JobFinderBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'svg']):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:max_chars]
    except requests.RequestException:
        return ''
    except Exception:
        return ''


def compute_ats_score(cv_text: str, job_text: str) -> int:
    """Usa o LLM local para estimar a compatibilidade (0-100) entre o CV e a vaga."""
    if not job_text or not job_text.strip():
        return 0

    response = ollama.chat(model=llm_model, messages=[
        {
            "role": "system",
            "content": (
                "Você é um sistema ATS (Applicant Tracking System). Sua tarefa é comparar "
                "o currículo de um candidato com a descrição de uma vaga e estimar a "
                "porcentagem de compatibilidade entre os dois, considerando principalmente "
                "habilidades técnicas, experiência e requisitos mencionados na vaga.\n\n"
                "REGRAS OBRIGATÓRIAS:\n"
                "- Responda APENAS com um número inteiro de 0 a 100.\n"
                "- NÃO escreva o símbolo '%'.\n"
                "- NÃO escreva nenhum texto, explicação ou pontuação além do número."
            )
        },
        {
            "role": "user",
            "content": (
                f"Currículo:\n{cv_text[:MAX_SCRAPE_CHARS]}\n\n"
                f"Descrição da vaga:\n{job_text}\n\n"
                "Compatibilidade (0-100):"
            )
        }
    ],
    options={"temperature": 0}
    )

    content = response['message']['content']
    match = re.search(r'\d{1,3}', content)
    if not match:
        return 0
    score = int(match.group())
    return max(0, min(score, 100))


def get_company_name(url: str) -> str:
    """Aproxima o nome da empresa/portal a partir do domínio do link da vaga."""
    try:
        netloc = urlparse(url).netloc
        netloc = netloc.replace('www.', '')
        domain = netloc.split('.')[0]
        return domain.capitalize() if domain else 'Desconhecida'
    except Exception:
        return 'Desconhecida'


def format_output(search_results: list[dict], cv_text: str) -> list[dict]:
    rows = []
    for r in search_results:
        title = r.get('title', 'Vaga sem título')
        url = r.get('href') or r.get('url') or ''
        body = (r.get('body') or '').strip()

        if len(body) < MIN_BODY_CHARS and url:
            scraped = scrape_page_text(url)
            job_text = scraped if scraped else body
        else:
            job_text = body

        score = compute_ats_score(cv_text, job_text)

        rows.append({
            'Vaga': title,
            'Empresa': get_company_name(url),
            'ATS': f'{score}%',
            '_ats_score': score,
            'Link': url,
        })

    rows.sort(key=lambda row: row['_ats_score'], reverse=True)
    for row in rows:
        row.pop('_ats_score', None)

    return rows


'''
    PUBLIC API
'''
def submit_cv(cv_file, options):
    cv_text = get_pdf_text(cv_file)
    search_position = get_compatible_position(cv_text)
    search_query = make_query(search_position, options)
    print(search_query)
    timelimit = TIME_FILTER_MAP.get(options.get('time'))
    search_output = job_search(search_query, options['max'], timelimit)
    results = format_output(search_output, cv_text)
    return results
