
import os
import subprocess
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from transformers import MarianMTModel, MarianTokenizer
import argostranslate.package
import argostranslate.translate
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import lru_cache
import gdown

# Inicialização do FastAPI
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configurações de paralelismo
WORKERS = 4
executor = ThreadPoolExecutor(max_workers=WORKERS)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações dos modelos Argos
# Aqui definimos o caminho local para os modelos
argos_model_path = os.getenv("ARGOS_MODELS_DESTINO", "libraries")
# Essa variável global será inicializada no startup
argos_models = []
# Definindo o caminho dos modelos
argos_model_path = 'caminho_para_modelos_argos'

def download_from_drive(folder_url, output_path):
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
        comando = f'gdown --folder "{folder_url}" --remaining-ok -O {output_path}'
        print(f"Baixando arquivos da pasta: {folder_url}")
        subprocess.run(comando, shell=True)
    else:
        print(f"Pasta '{output_path}' já existe. Pulando download.")

def download_libraries():
    """
    Faz o download das pastas de modelos do Google Drive utilizando gdown.
    """
    # URL das pastas no Google Drive
    folder_urls = [
        os.getenv("ARGOS_MODELS_URL_1", "https://drive.google.com/drive/u/0/folders/https://drive.google.com/drive/u/0/folders/1QyY1Bfa0x8hWgCVc9uQmSnbSnALrTRdF"),
        os.getenv("ARGOS_MODELS_URL_2", "https://drive.google.com/drive/u/1/folders/1StDZgXG2Q2wIClzKcoJQJfEv_xc8RLAo")
    ]
    
    # Baixa todos os arquivos da Conta 1
    download_from_drive(folder_urls[0], os.path.join(argos_model_path, 'modelos_conta_1'))
    
    # Baixa somente os arquivos necessários da Conta 2
    download_path_2 = os.path.join(argos_model_path, 'modelos_conta_2')
    if not os.path.exists(download_path_2):
        os.makedirs(download_path_2, exist_ok=True)
        for file_id in ["1vZFxoZrhH6V7APpxfs4xD0MYcDPz_U_T", "1LiijbZ1UTe2bSj2ifusjH3ywPpZXH1RP", "16ghz1WV1lWH_9rg7zU1A7Nr1raUcsNGY"]:  # IDs dos arquivos na conta 2
            file_url = f"https://drive.google.com/uc?id={file_id}"
            comando = f'gdown {file_url} -O {download_path_2}'
            print(f"Baixando arquivo: {file_id}")
            subprocess.run(comando, shell=True)
    else:
        print(f"Pasta '{download_path_2}' já existe. Pulando download.")

@app.on_event("startup")
async def startup_event():
    # Baixa os arquivos de modelos do Google Drive, se necessário
    download_libraries()
    # Após o download, carrega os modelos Argos da pasta
    global argos_models
    try:
        argos_models = []
        
        # Carregar todos os modelos da Conta 1
        download_path_1 = os.path.join(argos_model_path, 'modelos_conta_1')
        argos_models.extend([
            argostranslate.package.install_from_path(os.path.join(download_path_1, m))
            for m in os.listdir(download_path_1)
        ])
        
        # Carregar apenas os modelos específicos da Conta 2
        download_path_2 = os.path.join(argos_model_path, 'modelos_conta_2')
        modelos_validos = [m for m in os.listdir(download_path_2) if '-en' in m and m.index('-en') > 0]
        argos_models.extend([
            argostranslate.package.install_from_path(os.path.join(download_path_2, m))
            for m in modelos_validos
        ])
        
        print("Modelos Argos carregados com sucesso.")
    except Exception as e:
        print("Erro ao carregar os modelos Argos:", e)

# Modelos MarianMT
MARIAN_MODELS = {
    'en-hr': 'Helsinki-NLP/opus-mt-en-sla',
    'hr-en': 'Helsinki-NLP/opus-mt-sla-en'
}

@lru_cache(maxsize=2)
def load_marian_model(model_name):
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model

# Cache para módulos Argos
translation_cache = {}

def get_argos_translation(from_lang, to_lang):
    cache_key = f"{from_lang}-{to_lang}"
    if cache_key not in translation_cache:
        installed = argostranslate.translate.get_installed_languages()
        from_lang_obj = next((l for l in installed if l.code == from_lang), None)
        to_lang_obj = next((l for l in installed if l.code == to_lang), None)
        translation_cache[cache_key] = from_lang_obj.get_translation(to_lang_obj) if from_lang_obj and to_lang_obj else None
    return translation_cache[cache_key]

# Função de tradução otimizada
async def translate_text(text, from_lang, to_lang):
    # Verificar combinação croata
    if {from_lang, to_lang}.intersection({'hr'}):
        if from_lang == 'hr' and to_lang != 'en':
            # Traduzir hr -> en -> target
            trans_hr_en = await marian_translate(text, 'hr', 'en')
            return await argos_translate(trans_hr_en, 'en', to_lang)
        elif to_lang == 'hr' and from_lang != 'en':
            # Traduzir source -> en -> hr
            trans_en = await argos_translate(text, from_lang, 'en')
            return await marian_translate(trans_en, 'en', 'hr')
        else:
            # Usar MarianMT direto para en<->hr
            return await marian_translate(text, from_lang, to_lang)
    else:
        # Usar Argos para outras combinações
        return await argos_translate(text, from_lang, to_lang)

async def marian_translate(text, from_lang, to_lang):
    model_key = f"{from_lang}-{to_lang}"
    if model_key not in MARIAN_MODELS:
        raise HTTPException(400, "Combinação de idiomas não suportada")
   
    tokenizer, model = load_marian_model(MARIAN_MODELS[model_key])
    loop = asyncio.get_event_loop()
   
    def _translate():
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        outputs = model.generate(**inputs)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
   
    return await loop.run_in_executor(executor, _translate)

async def argos_translate(text, from_lang, to_lang):
    loop = asyncio.get_event_loop()
    translation = get_argos_translation(from_lang, to_lang)
   
    if not translation:
        raise HTTPException(400, "Tradução não suportada")
   
    return await loop.run_in_executor(executor, translation.translate, text)

# Dicionário de idiomas suportados
LANGUAGES = {
    'pt': 'Português (Brasil/Portuguese Brazilian)',
    'en': 'Inglês (English/United States)',
    'es': 'Espanhol (Español/Spain)',
    'de': 'Alemão (Deutsch/Germany)',
    'zt': 'Chinês Simplificado (简体中文/Simplified Chinese)',
    'ca': 'Catalão (Català/Catalan)',
    'eu': 'Basco (Euskara/Basque)',
    'fr': 'Francês (Français/France)',
    'it': 'Italiano (Italian/Italy)',
    'ja': 'Japonês (日本語/Japanese)',
    'pl': 'Polonês (Polska/Polish)',
    'hr': 'Croata (Hrvatski/Croatian)',
    'sk': 'Eslovaco (Slovenský/Slovak)',
    'ru': 'Russo (Русский/Russian)',
    'bg': 'Búlgaro (български/Bulgarian)',
    'sv': 'Sueco (Svenska/Swedish)',
    'fi': 'Finlandês (Suomi/Finnish)',
    'cs': 'Tcheco (čeština/Czech Rep)',
    'sl': 'Esloveno (Slovenščina/Slovenian)',
    'ro': 'Romeno (Română/Romanian)',
    'da': 'Dinamarquês (Dansk/Danish)',
    'el': 'Grego (ΕΛΛΗΝΙΚΑ/Greek)',
    'tr': 'Turco (Türkçe/Turkish)',
    'th': 'Tailandês (แบบไทย/Thai)',
    'nl': 'Neerlandês (Nederlands/Dutch)',
    'hu': 'Húngaro (magyar/Hungarian)',
    'ga': 'Irlandês (Gaeilge/Irish)',
    'nb': 'Norsk (Norwegian)',
    'lt': 'Lietuvių Kalba (Lithuanian)',
    'lv': 'Latviešu (Latvian)',
    'ko': '한국인 (Korean)',
    'ms': 'Melayu (Malay)',
    'sq': 'Shqip (Albanian)',
    'uk': 'українська (Ukranian)',
    'et': 'Eesti (Estonian)',
}

# Rotas
class TranslateRequest(BaseModel):
    text: str
    from_lang: str = "auto"
    to_lang: str = "en"

class BatchItem(BaseModel):
    key: str
    text: str

class BatchRequest(BaseModel):
    texts: list[BatchItem]
    from_lang: str
    to_lang: str

@app.post("/translate/")
async def single_translate(request: TranslateRequest):
    try:
        translated = await translate_text(request.text, request.from_lang, request.to_lang)
        return {"translated_text": translated}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/translate/all/")
async def batch_translate(request: BatchRequest):
    try:
        tasks = [translate_text(item.text, request.from_lang, request.to_lang)
                 for item in request.texts]
        translated_texts = await asyncio.gather(*tasks)
        return {item.key: text for item, text in zip(request.texts, translated_texts)}
    except Exception as e:
        raise HTTPException(500, str(e))

# Rota para obter os idiomas disponíveis
@app.get("/languages/")
async def get_languages():
    return LANGUAGES

# Página inicial com HTML para enviar texto e traduzir
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "languages": LANGUAGES})

# Executando o servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=WORKERS)
