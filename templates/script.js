// Texto traduzido
let translatedText = document.getElementById('translatedText').innerText; // Pega o conteúdo do div com id 'translatedText'

// Limite de caracteres
const charLimit = 5000;

// Exibindo o texto inicial
function displayInitialText() {
    const textContainer = document.getElementById('translatedText');
    
    // Se o texto for maior que o limite, mostra o botão de "Ver mais"
    if (translatedText.length > charLimit) {
        textContainer.textContent = translatedText.substring(0, charLimit); // Exibe os primeiros 5000 caracteres
        document.getElementById('showMoreBtn').style.display = 'block'; // Exibe o botão de "Ver mais"
    } else {
        textContainer.textContent = translatedText;
    }
}

// Função para mostrar o restante do texto
function showMoreText() {
    const textContainer = document.getElementById('translatedText');
    textContainer.textContent = translatedText; // Exibe o texto completo
    document.getElementById('showMoreBtn').style.display = 'none'; // Esconde o botão "Ver mais"
}

// Chama a função para exibir o texto inicialmente
displayInitialText();

// Event listener para o botão de "Ver mais"
document.getElementById('showMoreBtn').addEventListener('click', showMoreText);
