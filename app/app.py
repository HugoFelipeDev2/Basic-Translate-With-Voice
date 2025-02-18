import os
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

# Carregamento de modelos
argos_model_path = "F:\\Basic-Translate-With-Voice-main\\libraries"
argos_models = [argostranslate.package.install_from_path(os.path.join(argos_model_path, m)) 
               for m in os.listdir(argos_model_path)]


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
        from_lang = next((l for l in installed if l.code == from_lang), None)
        to_lang = next((l for l in installed if l.code == to_lang), None)
        translation_cache[cache_key] = from_lang.get_translation(to_lang) if from_lang and to_lang else None
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
