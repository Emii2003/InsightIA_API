import pandas as pd
import asyncio
from selenium import webdriver
from bs4 import BeautifulSoup
from time import sleep
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import csv
from datetime import datetime

class Scraping:

    def __init__(self, empresa, apelido=None, max_page=None):
        self.empresa = empresa
        if apelido == None:
            apelido = empresa
        self.apelido = apelido
        self.url = f'https://www.reclameaqui.com.br/empresa/{self.empresa}/lista-reclamacoes/'
        self.max_page = max_page
        self.dados = []
        self.navegador = None

    async def acessar_web(self):
        web_options = Options()
        web_options.add_argument("--headless")
        web_options.add_argument("--disable-gpu")
        web_options.add_argument("--no-sandbox")
        web_options.add_argument("--disable-dev-shm-usage")
        
        self.navegador = webdriver.Chrome(options=web_options)
        self.navegador.set_page_load_timeout(60)
        if not self.verificar_url():
            self.navegador.quit()
            return {"status_code": 404, "mensagem": f"URL não encontrada: {self.url}"}
        try:
            # self.navegador.get(self.url)
            return {"status_code": 200, "mensagem": f"URL encontrada: {self.url}"}

        except Exception as e:
            self.navegador.quit()
            return {"status_code": 500, "mensagem": f"Erro ao carregar a página: {e}"}

    def verificar_url(self):
        try:
            # self.navegador.get(self.url)
            sleep(1)  # Adicionar um tempo de espera para garantir que a página seja carregada completamente
            # if "404" in self.navegador.current_url:
            #     return False
            return True
        except Exception as e:
            print(f"Erro ao verificar a URL: {e}")
            return False

    def obter_numero_total_de_paginas(self):
        try:
            total_pages_element = WebDriverWait(self.navegador, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-testid="pages-label"]'))
            )
            total_pages_text = total_pages_element.text
            total_pages = int(total_pages_text.split('de')[-1].strip())
            return total_pages
        except Exception as e:
            print(f"Não foi possível obter o número total de páginas: {e}")
            return 1

    async def scraping(self, total_pages):
        page_number = 1
        dados = []
        while page_number <= total_pages:
            self.navegador.get(f'{self.url}?pagina={page_number}')
            self.site = BeautifulSoup(self.navegador.page_source, 'html.parser')
            reclamacoes = self.site.find_all('div', class_='sc-1pe7b5t-0 eJgBOc')

            for reclamacao in reclamacoes:
                titulo = reclamacao.find('h4', class_='sc-1pe7b5t-1 bVKmkO').get_text() if reclamacao.find('h4', class_='sc-1pe7b5t-1 bVKmkO') else 'Título não encontrado'
                link = reclamacao.find('a')['href'] if reclamacao.find('a') else 'Link não encontrado'
                descricao = reclamacao.find('p', class_='sc-1pe7b5t-2 eHoNfA').get_text() if reclamacao.find('p', class_='sc-1pe7b5t-2 eHoNfA') else 'Descrição não encontrada'
                status = next((reclamacao.find('span', class_=cls).get_text() for cls in ['sc-1pe7b5t-4 jKvVbt', 'sc-1pe7b5t-4 cZrVnt', 'sc-1pe7b5t-4 ihkTSQ'] if reclamacao.find('span', class_=cls)), 'Status não encontrado')
                tempo = reclamacao.find('span', class_='sc-1pe7b5t-5 dspDoZ').get_text() if reclamacao.find('span', class_='sc-1pe7b5t-5 dspDoZ') else 'Tempo não encontrado'

                dados.append({
                    "empresa": self.empresa,
                    "apelido": self.apelido,
                    "data-operacao" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "titulo": titulo,
                    "link": f"https://www.reclameaqui.com.br{link}",
                    "descricao": descricao,
                    "status": status,
                    "tempo": tempo
                })

            page_number += 1
        return {"status_code": 200, "mensagem": f"Web Scraping Concluido com sucesso!"}, dados

    async def iniciar(self):
        status = {}
        status = await self.acessar_web()
        # if status["status_code"] != 200:
        #     return status, []
        # total_pages = self.obter_numero_total_de_paginas()
        # if self.max_page and self.max_page < total_pages:
        #     total_pages = self.max_page
        total_pages = 1
        status, self.dados = await self.scraping(total_pages)
        self.navegador.quit()
        return status, self.dados