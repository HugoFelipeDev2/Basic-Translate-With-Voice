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

def download_libraries():
    """
    # Faz o download das pastas de modelos do Mega e do pCloud utilizando links diretos.
    """
    mega_urls = [
        "https://mega.nz/file/JP91kAZQ#yihXJcXCYN7WsjYTY728L0ZN7mFvFr0rXbJHT35K3mE",
        "https://mega.nz/file/EOll3ZjJ#wR1LBA8N-gEvLhpUZVgAZgwArQubzOQ086mdt09zlho",
        "https://mega.nz/file/tSkmFIYR#SnNowWjEP2lrWLiGjHmwHZNORiXvBMB56YPLBRsf1C8",
        "https://mega.nz/file/1f1kQZrI#I8bPm867Vl0Xeu39MgNgwbNioMF-AOsDvnt7wJmomT4",
        "https://mega.nz/file/9aEREbRK#o0sEXMhsxxuSaf0we2SxeJu-f2clk5VcXXUSfstDqYM",
        "https://mega.nz/file/FPEVUQKB#XuwkizV-de1iJ8gsSRdYBhDnj1SzkvV85w63ph0jvbI",
        "https://mega.nz/file/4LEw2LRC#OtfXdeWAzo1qGKAb56gbHaYrq9uU-gg6W_wdrAph5Ck",
        "https://mega.nz/file/4e00UAIa#xY-FPXzkiofrWuvmdiFlTDaCu9Sn_3fnaCosV9IXwHg",
        "https://mega.nz/file/tf02FQpa#F1jL51M02Y0kDM05j-TdFoR1snMKFPn4D1MmzZULKoY",
        "https://mega.nz/file/VXNVCRjB#4WAhaQu0QlGGNJ4h4LAchdcV6UnRVtQGQ88epfSqeAE",
        "https://mega.nz/file/wHUXDKLA#YbMMFvqdoong5OkyFz7CWgJzFHKdDNxqSgAqo9J3CHs",
        "https://mega.nz/file/hS11EIAC#lSfuiHp0XKhv-Y0J9WiFQ_lR0fgkA2sYf-UHt_kPo30",
        "https://mega.nz/file/gbExTCwC#Ymeanvee87ox3h0CXOY4AzKfFTMC1921oiLvt8yltJ8",
        "https://mega.nz/file/NCNBBQ7S#aVsnJGd586ZcHKNm9adOk4I9PMJhFlF8nWYfPY-zjms",
        "https://mega.nz/file/heNWwTyA#0AGnJMZGXK0h1CIIW6H0AJs8cX7pA5oJR383jnjWYP0",
        "https://mega.nz/file/dbtTyRhK#ahHDzjfSl5tuQ15fABIxug17aszuTY12A79GLxe51rM",
        "https://mega.nz/file/ATlSADiZ#gLojL_Mj9F__KeJy6mi7W8rw-tD7QUwCLOf1V6zootg",
        "https://mega.nz/file/JSFEHbKR#TxEQsGbROQ0-g8ZnOOqb5qe28uTmT20lh3bh4YIPZBI",
        "https://mega.nz/file/pTF33AKQ#7L5Drac7g5NJ6cDiUY16e6lOy_PCJPtB14C5Se5E4Iw",
        "https://mega.nz/file/ZKV1SLiQ#DpXDcVYNkvqg8hKhi765QfP5YPx5p49Bpz-_4s06QPI",
        "https://mega.nz/file/geVjQDKA#6Zmh8J8WVlPLYYfbfPwg7uciU47BEM6toDMvX__LTB8",
        "https://mega.nz/file/9D9GiS6L#aDWzOO9PU8PwKaYF311KcGKtWc7RKTCUtZ6PZjsb28o",
        "https://mega.nz/file/pC9QHDrY#Q6N6X980CxW4ZUVyBiBgwWX5HuVf3qZXUaM7tM5JIng",
        "https://mega.nz/file/hacmCBYA#AqEVD0B7ueCCypLi2k3lXqSp7J7p3n8YO719zQsSJWY",
        "https://mega.nz/file/EHd1yLpK#3g6ErvmDwUbfokmYIvOjt1-v0ndY9AST9E2CSilqbUc",
        "https://mega.nz/file/8W8E1AZK#y1O-sttPI6TeMuYiFOGXCfIsOw1Gqnpn5S1owM8LFWg",
        "https://mega.nz/file/Vf9xwSCA#j8u6tXdI-zMQMEoJmFZ2d2jDC02RqhQ1f_O05BJR7jI",
        "https://mega.nz/file/RPEQ0DYb#ByHyat8-V9NWQ-F2f8TsYvXnczFv2QZ-MxenAGuYKNg",
        "https://mega.nz/file/wX8zjLyD#xd3BwUZlTJxkjBu2QLDzyZ78k9XeLRJLbzdZSQsDkN8",
        "https://mega.nz/file/YWFCkbzZ#k66EFpzaQeDCVuvXJo0oLm-99hprKPcp_i7nprIMMoU",
        "https://mega.nz/file/MO0i3bAa#aM2oYjUw0a69m9_OqGlIV_WHCoG_c27_b68TKyTMVpw",
        "https://mega.nz/file/lCtW0ZoJ#hURbUPiMZ3_iBnbOYwzv4h617NGC7DaDUNGZkah_WNA",
        "https://mega.nz/file/hXtQDJpS#Vz7khoHUu-M_z72hi_4rbH2Zz6z19X3UJqR2Abmy0oU",
        "https://mega.nz/file/ZKUy3IqJ#UwS2aDDUtmAi72VmArc4qTEOwiQKFJJv1ZLH9EjPEn0",
        "https://mega.nz/file/sS0W1BLS#rX--6p7w7kve2K4dsWAjc7pLD_kU0mr5XCGs-flcWSo",
        "https://mega.nz/file/lH1hFTpT#Aaaxija__JulKZsJb8gR2kzvsjxLOTPMoy3sgG8eDAQ",
        "https://mega.nz/file/ZWcFAZbA#wEP7mxDcvgAq2bxPgc69su_LKrQDDMn1bIEzq7q8lCQ"

    ]
    
    pcloud_urls = [
        "https://u.pcloud.link/publink/show?code=XZbirL5ZmOOjtN22jCz5Kti0b5dD6FFjswAX",
        "https://u.pcloud.link/publink/show?code=XZsirL5ZB5IDmhDpb5yHjYPmgVp5qyqJNOKV",
        "https://u.pcloud.link/publink/show?code=XZTirL5ZwNup43FCmT5JA5p2OsgjhuCquuMk",
        "https://u.pcloud.link/publink/show?code=XZlirL5Zzsz1gxCvvCzaAQGCH4l9g72bYetX",
        "https://u.pcloud.link/publink/show?code=XZUirL5ZUYl8sjhzrRuqYz8Tvz0FdXGkhaqV",
        "https://u.pcloud.link/publink/show?code=XZHrrL5Z9M77VsEj0IjRzUcuD3A7AYurDbMV",
        "https://u.pcloud.link/publink/show?code=XZhrrL5ZvVznzBCcVCzkJUv5KoM4LS4pDBQy",
        "https://u.pcloud.link/publink/show?code=XZWrrL5Zuks0Sdhh2VjyCC9M9a4OlhVr3fkk",
        "https://u.pcloud.link/publink/show?code=XZerrL5ZpG46tG7Xum58cqW4zGXUAS4txTr7",
        "https://u.pcloud.link/publink/show?code=XZTrrL5Z3XzHdiAWHv8WHDIxP9jbuYDirxJk",
        "https://u.pcloud.link/publink/show?code=XZTrrL5Z3XzHdiAWHv8WHDIxP9jbuYDirxJk",
        "https://u.pcloud.link/publink/show?code=XZErrL5ZEeiWlketB4zoxAVei0lGwRkqVqSV",
        "https://u.pcloud.link/publink/show?code=XZArrL5ZQ8bEOe55nJkC13BB01p5cYL90oay",
        "https://u.pcloud.link/publink/show?code=XZcrrL5Z7bwyCW8dK7Jg7HdIfAUhc7UxB22V",
        "https://u.pcloud.link/publink/show?code=XZkcrL5Ze94LwDI4OXyhX5m1QbsQFXfViUpy",
        "https://u.pcloud.link/publink/show?code=XZ5crL5ZHLdQQ6VI1l81rbHJpMJLRXXGB0KX",
        "https://u.pcloud.link/publink/show?code=XZScrL5ZpNvl9U1vTskunqmtuoz4Q0gNmgIk",
        "https://u.pcloud.link/publink/show?code=XZncrL5ZClUn6DUP25JmEN5ewSKVKHBdbpCy",
        "https://u.pcloud.link/publink/show?code=XZdcrL5ZV8Ljo3QAOIFq10dgQETrp5R5NQXX",
        "https://u.pcloud.link/publink/show?code=XZNcrL5Z4z6UUJcyncQESTlj6MgIL8cO9TwX",
        "https://u.pcloud.link/publink/show?code=XZJorL5Z4nbNMTlTrnf8kiuni813uXYcayUX",
        "https://u.pcloud.link/publink/show?code=XZRorL5ZG40RLb6XMD74trLmzOsCFXQjdtyy",
        "https://u.pcloud.link/publink/show?code=XZ8orL5ZD892ByFtcT5IaYdnQHUkc0WDalB7",
        "https://u.pcloud.link/publink/show?code=XZmorL5ZIo73XXNtz7h8mngyNolgd5hIewHX",
        "https://u.pcloud.link/publink/show?code=XZuorL5ZtLhG5SrgBF4TmQOVwnkbTfM1gxRX",
        "https://u.pcloud.link/publink/show?code=XZforL5ZXikw64i3CmuHqJa9akjsjRYwOrXy",
        "https://u.pcloud.link/publink/show?code=XZWorL5Z3OrpSkCqGouMR0sETyQgLYlWv1vy",
        "https://u.pcloud.link/publink/show?code=XZMorL5ZOzoTcEh6DOJIsGLx5w5E2uWyxqH7",
        "https://u.pcloud.link/publink/show?code=XZKorL5ZWv3OMErfChQpkfcxkBmXgRQNp8TX",
        "https://u.pcloud.link/publink/show?code=XZtorL5ZLWxcIwOixE40cDDiezOdY7Sy6M2X",
        "https://u.pcloud.link/publink/show?code=XZEorL5ZO8CkTHQeS8bFQsWcC89IXjumD2w7",
        "https://u.pcloud.link/publink/show?code=XZUorL5ZkBYD88Y6YThUdRoIRj4mm4k1IYV7",
        "https://u.pcloud.link/publink/show?code=XZvorL5ZmLjK7WhHJrR6oiebn5c2hJK8zrD7",
        "https://u.pcloud.link/publink/show?code=XZrorL5ZL7vjRO0MkpLhEvdhMMySQm6jsaTX",
        "https://u.pcloud.link/publink/show?code=XZyycL5ZzE7UJ73aLAzgJSeCvXKI6JRmSih7"
        
    ]
    
    if not os.path.exists(argos_model_path):
        os.makedirs(argos_model_path, exist_ok=True)
        
        for url in mega_urls:
            mega_comando = f'megatools dl --path {argos_model_path} {url}'
            print("Baixando arquivos do Mega:", url)
            subprocess.run(mega_comando, shell=True)
        
        for url in pcloud_urls:
            pcloud_comando = f'wget -P {argos_model_path} {url}'
            print("Baixando arquivos do pCloud:", url)
            subprocess.run(pcloud_comando, shell=True)
    else:
        print(f"Pasta '{argos_model_path}' já existe. Pulando download.")

@app.on_event("startup")
async def startup_event():
    # Baixa os arquivos de modelos do Mega e do pCloud, se necessário
    download_libraries()
    # Após o download, carrega os modelos Argos da pasta
    global argos_models
    try:
        argos_models = [
            argostranslate.package.install_from_path(os.path.join(argos_model_path, m))
            for m in os.listdir(argos_model_path)
        ]
        print("Modelos Argos carregados com sucesso.")
    except Exception as e:
        print("Erro ao carregar os modelos Argos:", e)


@app.on_event("startup")
async def startup_event():
    # Baixa os arquivos de modelos do Google Drive, se necessário
    download_libraries()
    # Após o download, carrega os modelos Argos da pasta
    global argos_models
    try:
        argos_models = []
        
        # Carregar os modelos da Conta 1
        download_path_1 = os.path.join(argos_model_path, 'modelos_conta_1')
        argos_models.extend([
            argostranslate.package.install_from_path(os.path.join(download_path_1, m))
            for m in os.listdir(download_path_1)
        ])
        
        # Carregar os modelos da Conta 2
        download_path_2 = os.path.join(argos_model_path, 'modelos_conta_2')
        argos_models.extend([
            argostranslate.package.install_from_path(os.path.join(download_path_2, m))
            for m in os.listdir(download_path_2)
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
