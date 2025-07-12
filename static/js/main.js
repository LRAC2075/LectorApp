document.addEventListener('DOMContentLoaded', () => {
    // Referencias a los elementos del DOM
    const uploadSection = document.getElementById('upload-section');
    const loadingSection = document.getElementById('loading-section');
    const resultSection = document.getElementById('result-section');
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const dropArea = document.getElementById('drop-area');
    const textOutput = document.getElementById('text-output');
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    const speedControl = document.getElementById('speed-control');
    const speedLabel = document.getElementById('speed-label');
    const restartBtn = document.getElementById('restart-btn');

    const synth = window.speechSynthesis;
    let utterance = null;
    let fullText = '';
    let lastSpokenCharIndex = 0;

    // --- LÓGICA DE CARGA DE ARCHIVOS ---
    function handleFiles(files) {
        if (files.length === 0) return;
        fileInput.files = files;
        fileNameDisplay.textContent = files[0].name;
        uploadForm.requestSubmit();
    }
    dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('drag-over'); });
    dropArea.addEventListener('dragleave', () => dropArea.classList.remove('drag-over'));
    dropArea.addEventListener('drop', (e) => { e.preventDefault(); dropArea.classList.remove('drag-over'); handleFiles(e.dataTransfer.files); });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files[0]) { alert('Por favor, selecciona un archivo primero.'); return; }
        uploadSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');
        const formData = new FormData(uploadForm);
        try {
            const response = await fetch('/process', { method: 'POST', body: formData });
            const data = await response.json();
            loadingSection.classList.add('hidden');
            resultSection.classList.remove('hidden');
            if (response.ok) {
                renderText(data.text);
            } else {
                renderText(`Error: ${data.error}`);
            }
        } catch (error) {
            loadingSection.classList.add('hidden');
            resultSection.classList.remove('hidden');
            renderText(`Error de conexión: ${error.message}`);
        }
    });

    // --- NUEVA FUNCIÓN PARA RENDERIZAR TEXTO INTERACTIVO ---
    function renderText(text) {
        fullText = text;
        textOutput.innerHTML = ''; // Limpiamos el contenido anterior
        let charIndex = 0;
        text.split(/(\s+)/).forEach(part => {
            if (part.trim() !== '') {
                const wordSpan = document.createElement('span');
                wordSpan.textContent = part;
                wordSpan.dataset.charIndex = charIndex; // Guardamos su posición
                textOutput.appendChild(wordSpan);
            } else {
                // Mantenemos los espacios y saltos de línea
                textOutput.appendChild(document.createTextNode(part));
            }
            charIndex += part.length;
        });
    }

    // --- LÓGICA DE TEXTO A VOZ MEJORADA ---
    function playText(startIndex = 0) {
        if (synth.speaking) {
            synth.cancel();
        }
        const textToSpeak = fullText.substring(startIndex);
        if (textToSpeak.trim() === '') return;

        utterance = new SpeechSynthesisUtterance(textToSpeak);
        const langSelect = document.getElementById('output-lang-select').value.toLowerCase();
        const langMap = { "español": "es-ES", "inglés": "en-US", "alemán": "de-DE", "coreano": "ko-KR", "japonés": "ja-JP" };
        utterance.lang = langMap[langSelect] || 'es-ES'; // Default a español si no es una traducción
        utterance.rate = parseFloat(speedControl.value);

        utterance.onboundary = (event) => {
            lastSpokenCharIndex = startIndex + event.charIndex;
            highlightWordAt(lastSpokenCharIndex, event.charLength);
        };
        
        utterance.onend = () => {
            lastSpokenCharIndex = 0;
            removeHighlight();
        };

        synth.speak(utterance);
    }

    function highlightWordAt(charIndex, charLength) {
        removeHighlight();
        const spans = textOutput.querySelectorAll('span');
        for (const span of spans) {
            const spanIndex = parseInt(span.dataset.charIndex, 10);
            if (spanIndex >= charIndex && spanIndex < charIndex + charLength) {
                span.classList.add('highlight');
                return;
            }
        }
    }

    function removeHighlight() {
        const highlighted = textOutput.querySelector('.highlight');
        if (highlighted) {
            highlighted.classList.remove('highlight');
        }
    }

    // --- EVENT LISTENERS PARA CONTROLES ---
    playBtn.addEventListener('click', () => {
        if (synth.paused) synth.resume();
        else playText(lastSpokenCharIndex);
    });
    pauseBtn.addEventListener('click', () => synth.pause());
    stopBtn.addEventListener('click', () => {
        synth.cancel();
        lastSpokenCharIndex = 0;
        removeHighlight();
    });
    speedControl.addEventListener('input', () => {
        const speed = parseFloat(speedControl.value).toFixed(1);
        speedLabel.textContent = `${speed}x`;
        if (synth.speaking && !synth.paused) {
            playText(lastSpokenCharIndex);
        }
    });
    restartBtn.addEventListener('click', () => {
        synth.cancel();
        resultSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        uploadForm.reset();
        fileNameDisplay.textContent = '';
        textOutput.innerHTML = '';
        fullText = '';
        lastSpokenCharIndex = 0;
    });

    // --- NUEVO EVENT LISTENER PARA CLIC EN TEXTO ---
    textOutput.addEventListener('click', (e) => {
        if (e.target.tagName === 'SPAN') {
            const charIndex = parseInt(e.target.dataset.charIndex, 10);
            lastSpokenCharIndex = charIndex;
            playText(charIndex);
        }
    });
});