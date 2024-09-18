import re
import csv
import asyncio
import pandas as pd
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from collections import Counter
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Scraping:
    def __init__(self, empresa, apelido=None, max_page=None):
        self.empresa = empresa
        if apelido == None:
            apelido = empresa
        self.apelido = apelido
        self.url = (
            f"https://www.reclameaqui.com.br/empresa/{self.empresa}/lista-reclamacoes/"
        )
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
            self.navegador.get(self.url)
            return {"status_code": 200, "mensagem": f"URL encontrada: {self.url}"}

        except Exception as e:
            self.navegador.quit()
            return {"status_code": 500, "mensagem": f"Erro ao carregar a página: {e}"}

    def verificar_url(self):
        try:
            self.navegador.get(self.url)
            sleep(1)
            if "404" in self.navegador.current_url:
                return False
            return True
        except Exception as e:
            print(f"Erro ao verificar a URL: {e}")
            return False

    def obter_numero_total_de_paginas(self):
        try:
            total_pages_element = WebDriverWait(self.navegador, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'span[data-testid="pages-label"]')
                )
            )
            total_pages_text = total_pages_element.text
            total_pages = int(total_pages_text.split("de")[-1].strip())
            return total_pages
        except Exception as e:
            return {
                "status_code": 500,
                "mensagem": f"Não foi possível obter o número total de páginas: {e}",
            }

    def obter_detalhes_reclamacao(self, link):
        try:
            self.navegador.get(link)
            sleep(2)
            reclamacao_site = BeautifulSoup(self.navegador.page_source, "html.parser")

            titulo = reclamacao_site.find(
                "h1", {"data-testid": "complaint-title"}
            ).get_text(strip=True)
            descricao = reclamacao_site.find(
                "p", {"data-testid": "complaint-description"}
            ).get_text(strip=True)
            status = reclamacao_site.find("span", class_="sc-1a60wwz-1 zBBWP").get_text(
                strip=True
            )
            localizacao = reclamacao_site.find(
                "span", {"data-testid": "complaint-location"}
            ).get_text(strip=True)
            
            categoria_problema_element = reclamacao_site.find(
                "li", {"data-testid": "listitem-problema"}
            )
            if categoria_problema_element:
                categoria_problema = categoria_problema_element.find("a").get_text(strip=True)
            else:
                categoria_problema = "Categoria não encontrada"


            return {
                "titulo": titulo,
                "descricao": descricao,
                "status": status,
                "localizacao": localizacao,
                "categoria_problema": categoria_problema
            }
            
        except Exception as e:
            print(f"Erro ao obter detalhes da reclamação: {e}")
            return None

    async def scraping(self, total_pages):
        page_number = 1
        total_problemas = 0
        result = {}
        reclamacoes_por_categoria = {}
        setor_empresa = None

        while page_number <= total_pages:
            print(page_number)
            self.navegador.get(f"{self.url}?pagina={page_number}")
            self.site = BeautifulSoup(self.navegador.page_source, "html.parser")
            
            setor_empresa = self.site.find('a', id='info_segmento_hero').get_text(strip=True)
            
            reclamacoes = self.site.find_all("div", class_="sc-1pe7b5t-0 eJgBOc")

            for reclamacao in reclamacoes:
                link = reclamacao.find("a")["href"]
                link_completo = f"https://www.reclameaqui.com.br{link}"
                detalhes = self.obter_detalhes_reclamacao(link_completo)

                if detalhes:
                    categoria = detalhes.get("categoria_problema", "others")

                    if categoria not in reclamacoes_por_categoria:
                        reclamacoes_por_categoria[categoria] = []

                    reclamacoes_por_categoria[categoria].append(
                        {
                            "empresa": self.empresa,
                            "apelido": self.apelido,
                            "titulo": detalhes["titulo"],
                            "link": link_completo,
                            "descricao": detalhes["descricao"],
                            "status": detalhes["status"],
                            "localizacao": detalhes["localizacao"],
                        }
                    )
                total_problemas += 1
            page_number += 1

        result["ramo"] = setor_empresa
        result["total_reclamacoes"] = total_problemas
        result["dados"] = [
            {
                "categoria": categoria,
                "reclamacoes": reclamacoes
            } for categoria, reclamacoes in reclamacoes_por_categoria.items()
        ]

        return {
            "status_code": 200,
            "mensagem": "Web Scraping Concluido com sucesso!",
        }, result
    
    async def iniciar(self):
        status = {}
        status = await self.acessar_web()
        if status["status_code"] != 200:
            return status, []
        total_pages = self.obter_numero_total_de_paginas()
        if self.max_page and self.max_page < total_pages:
            total_pages = self.max_page
        status, self.dados = await self.scraping(total_pages)
        self.navegador.quit()
        return status, self.dados
