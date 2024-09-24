import uvicorn
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web_scraping import Scraping
from database import iniciar_conexao   
from gemini import configurar_modelo, gerar_analise, gerar_analise_complexa, conversa_gemini, gerar_grafico_pizza, gerar_analise_concorrencia
from collections import defaultdict

app = FastAPI(
    title="API InsightIA",
    description="API para realizar web scraping no ReclameAqui, Analise de faturamento e Insight das reclamacoes",
    version="0.8.1",
    docs_url="/doc",  # Customiza a URL do Swagger
    openapi_url="/openapi.json",  # Customiza a URL do JSON do OpenAPI
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global db
    global model
    model = configurar_modelo()
    db = iniciar_conexao()

# Uteis
async def save_db(dados):
    if db is None:
        raise HTTPException(status_code=500, detail="A conexão com o Firestore não foi estabelecida")
    try:
        colecao = db.collection("reclamacoes")
        for dado in dados:
            colecao.add(dado)
        return {"status_code": 200, "mensagem": "Dados coletados e salvos com sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no banco de dados: {str(e)}")

async def buscar_doc_por_empresa_apelido(db, nome):
    # Primeiro tenta buscar por 'empresa'
    dados = [doc.to_dict() for doc in db.collection("reclamacoes").where('empresa', '==', nome).stream() if doc.to_dict().get("empresa")]

    # Se não encontrar, tenta buscar por 'apelido'
    if not dados:
        dados = [doc.to_dict() for doc in db.collection("reclamacoes").where('apelido', '==', nome).stream() if doc.to_dict().get("apelido")]

    return dados 


@app.get("/")
async def hello_world():
    return {"status_code": 200, "mensagem": "Bem Vindo ao InsightIA"}

# Realizar WebScraping no ReclameAqui buscando a empresa selecionada
@app.post("/scraping/{empresa}")
async def web_scraping(empresa: str, apelido: str = Query(None, description="Apelido para nome da Empresa"), max_page: int = Query(None, description="Número máximo de páginas para scraping")):
    try:
        empresa = empresa.replace(' ', '-')
        scraper = Scraping(empresa, apelido, max_page)
        dados = await buscar_doc_por_empresa_apelido(db, empresa)
        if dados:
            await apagar_reclamacoes_por_empresa(empresa)

            
        status, dados = await scraper.iniciar()
        if status['status_code'] == 200:
            return await save_db(dados)
        else:
            raise HTTPException(status_code=status['status_code'], detail=f"{status['mensagem']}")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao realizar web scraping: " +str(e))

# Buscar as empresas cadastradas
@app.get("/empresas/")
async def consultar_empresa():
    try:
        dados = {doc.to_dict().get("empresa") for doc in db.collection("reclamacoes").stream() if doc.to_dict().get("empresa")}
        if not dados:
            raise HTTPException(status_code=404, detail=f"Nenhuma empresa com reclamações encontrada.")
        
        return {"status_code": 200, "Empresas": [dados] }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar empresas:  {str(e)}")
    
@app.get("/historico/")
async def historico():
    try:
        dados = [doc.to_dict() for doc in db.collection("reclamacoes").stream()]
        if not dados:
            raise HTTPException(status_code=404, detail="Nenhuma reclamação encontrada.")

        responseData = defaultdict(lambda: {
            "empresa": "",
            "apelido": "",
            "qtd_reclamacoes": 0,
            "data-operacao": ""
        }) 

        for dado in dados:
            empresa = dado.get("empresa")
            if empresa:
                responseData[empresa]["empresa"] = empresa
                responseData[empresa]["apelido"] = dado.get("apelido")
                responseData[empresa]["qtd_reclamacoes"] += 1
                responseData[empresa]["data-operacao"] = dado.get("data-operacao")

        response = list(responseData.values())

        return {"status_code": 200, "dados": response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar historico da empresa: {str(e)}")

@app.get("/reclamacoes/{empresa}")
async def consultar_reclamacoes(empresa: str, max_reclamacao: int = Query(None, description="Número máximo de reclamacoes desejadas")):
    empresa = empresa.replace(' ', '-')
    try:
        collection_ref = db.collection("reclamacoes").where('empresa', '==', empresa)
        if not collection_ref:
            collection_ref = db.collection("apelido").where('apelido', '==', empresa)

        if max_reclamacao:
            collection_ref = collection_ref.limit(max_reclamacao)
        
        dados = [doc.to_dict() for doc in collection_ref.stream()]
        if not dados:
            raise HTTPException(status_code=404, detail=f"Nenhuma reclamação encontrada para a empresa informada.")

        return {"status_code": 200, "dados": dados}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar dados: {str(e)}")


@app.delete("/reclamacoes/{empresa}")
async def apagar_reclamacoes_por_empresa(empresa: str):
    try:
        deletados = 0
        deletados = sum(1 for _ in [doc.reference.delete() for doc in db.collection("reclamacoes").where('empresa', '==', empresa).stream()])

        if deletados == 0:
            return {"status_code": 404, "mensagem": f"Nenhuma reclamação encontrada para a empresa '{empresa}'."}
        
        return {"status_code": 200, "mensagem": f"Todas as reclamações da empresa '{empresa}' foram apagadas com sucesso."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar os dados: {str(e)}")

@app.delete("/reclamacoes/")
async def apagar_todas_reclamacoes():
    try:
        docs = db.collection("reclamacoes").stream()
        for doc in docs:
            doc.reference.delete()

        return {"status_code": 200, "mensagem": "Todas as reclamações foram apagadas com sucesso."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletear os dados: {str(e)}")

@app.post("/gemini/{empresa}")
async def analise_gemini(empresa : str):
    dados = await buscar_doc_por_empresa_apelido(db, empresa)
    try:
        return {"status_code": 200, "mensagem": f"{gerar_analise(model, dados)}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")

@app.post("/gemini/complexa/{empresa}")
async def analise_gemini_complexa(empresa : str):
    dados = await buscar_doc_por_empresa_apelido(db, empresa)
    try:
        return {"status_code": 200, "mensagem": gerar_analise_complexa(model, dados)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")

@app.post("/gemini/pizza/{empresa}")
async def analise_gemini_pizza(empresa : str):
    dados = await buscar_doc_por_empresa_apelido(db, empresa)
    try:
        return {"status_code": 200, "mensagem": gerar_grafico_pizza(model, dados)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")

@app.post("/gemini/concorrencia/{empresa}/{concorrente}")
async def analise_gemini_concorrencia(empresa : str, concorrente : str):
    dados = await buscar_doc_por_empresa_apelido(db, empresa)
    dados_concorrente = await buscar_doc_por_empresa_apelido(db, concorrente)
    try:
        return {"status_code": 200, "mensagem": gerar_analise_concorrencia(model, dados, dados_concorrente)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")
    
@app.get("/gemini/{prompt}")
async def msg_gemini(prompt : str):
    try:
        return {"status_code": 200, "mensagem": conversa_gemini(model, prompt)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, log_level="debug")
