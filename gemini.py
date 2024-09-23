import os
import google.generativeai as genai
import json

prompt = """
Quero que analise este json e me retorne estas informações, enriquece bastante com valores estatisticos seguindo este modelo(pode varias um pouco as palavras conforme necessário para contexto) e formate o melhor que puder:

{EMPRESA} teve {numero de reclamações analisadas} reclamações coletadas e obtemos os seguintes insights:
	Houve diversas reclamações envolvendo {palavras com maiores números de repeticoes} em contextos como {1 contexto nos dados}.
	Concluindo temos algumas sugestões de atenção:
	{Monte de 3 até 5 sugestões pertinentes para pontuar insight valiosos}

Segue textos de reclamacoes.
"""

def configurar_modelo():
    gemini_key = os.getenv('GEMINI_KEY')
    gemini_key = 'AIzaSyCoZBHkcJCnN2VBc5DzeUkMNDc8GKiG8GY'
    if not gemini_key:
        raise ValueError("A chave da API do GEMINI IA não foi encontrada na variável de ambiente 'GEMINI_KEY'.")
    
    genai.configure(api_key=gemini_key)
    return genai.GenerativeModel('gemini-1.5-flash')


def interacao_gemini(model, parts, temperature=0.7):
    try:
        response = model.generate_content(
            {"parts": parts}, 
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )

        if not response or not response.text:
            raise ValueError("A resposta gerada está vazia!")

        return response.text.replace('\n', '<br/>')

    except Exception as e:
        raise ValueError(f"Erro durante a interação com o modelo: {str(e)}")


def conversa_gemini(model, prompt):
    parts = [{"text": prompt}]
    return interacao_gemini(model, parts)

def gerar_analise(model, dados):
    dados_clean = json.dumps(dados, indent=2)
    parts = [{"text": prompt}, {"text": dados_clean}]
    return interacao_gemini(model, parts, temperature=0.2)

def gerar_analise_complexa(model, dados):
    dados_clean = json.dumps(dados, indent=2)
    details = {}
    chat = model.start_chat(history=[])
    chat.history.append({"role": "user", "parts": [{"text": prompt}, {"text": dados_clean}] })
    response = chat.send_message("Faça sugestões de melhoria. (Seu retorno sera mostrado em uma tela, entao seja agradavel para usuario e nao confunda)")
    details['sugestao'] = response.text.replace('\n', '<br/>')
    response = chat.send_message("Possiveis causas e soluções. (Seu retorno sera mostrado em uma tela, entao seja agradavel para usuario e nao confunda)")
    details['causas'] = response.text.replace('\n', '<br/>')
    return details

def gerar_grafico_pizza(model, dados):
    dados_clean = json.dumps(dados, indent=2)
    chat = model.start_chat(history=[])
    chat.history.append({"role": "user", "parts": [{"text": prompt}, {"text": dados_clean}] })
    response = chat.send_message("Analise os dados e tire um insight que possa mostrar graficamente. Exemplo: Principais motivos de reclamacoes, melhorias, assuntos e tempo (Quero no retorno somente seguindo este modelo de json {'titulo' : 'exemplo de analise', 'labels' : ['exemplo', 'label denovo'], 'values': [3, 4]}) SEM INFORMACOES DE MARKDOWN e Sem '/', somente o retorno de arquivo")
    return response.text.replace('\n', '<br/>')

def gerar_analise_concorrencia(model, dados_empresa, dados_concorrencia):
    dados_empresa_clean = json.dumps(dados_empresa, indent=2)
    dados_concorrencia_clean = json.dumps(dados_concorrencia, indent=2)
    concorrencia = {}
    chat = model.start_chat(history=[{"role": "user", "parts": [{"text": prompt}, {"text": dados_empresa_clean}] }, {"role": "user", "parts": [{"text": prompt}, {"text": dados_concorrencia_clean}] }])
    response = chat.send_message("Compare as reclamacoes entre as empresas e encontre pontos em comum. (Seu retorno sera mostrado em uma tela, entao seja agradavel para usuario e nao confunda)")
    concorrencia['comum'] = response.text.replace('\n', '<br/>').replace("\\", "")
    response = chat.send_message("Compare as reclamacoes entre as empresas e vantagens e desvantagens entre elas. (Seu retorno sera mostrado em uma tela, entao seja agradavel para usuario e nao confunda)")
    concorrencia['vantagem_desvantagem'] = response.text.replace('\n', '<br/>').replace("\\", "")
    return concorrencia