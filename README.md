# 🎬 ClipForge AI - Generador Automático de Clips Virales (9:16)

> Convierte videos largos y streams de YouTube en **clips verticales (9:16) con ganchos virales y subtítulos animados estilo Alex Hormozi / TikTok**, 100% gratis y de código abierto.

---

## ⚡ ¿Por qué es mejor que la arquitectura inicial de Render?

En la conversación previa se planteó alojar este sistema en el plan gratuito de **Render**. Sin embargo, en el mundo real de la edición de video con IA:

| Comparativa | ⚠️ Render (Free Tier) | 👑 Hugging Face Spaces (Recomendado) | 💻 Local (Tu PC) |
| :--- | :--- | :--- | :--- |
| **Memoria RAM** | **512 MB** *(Se cuelga con FFmpeg `Exit 137`)* | **16 GB RAM Gratis** (32x más memoria) | Toda la de tu PC |
| **Procesador (CPU)** | 0.1 vCPU compartida (muy lento) | **2 vCPU dedicadas** de alto rendimiento | Tu CPU/GPU (NVENC) |
| **Límite de Tiempo** | Timeout estricto a los 100 segundos | Sin timeout corto para Docker | Ilimitado |
| **Suspensión / Sleep** | Se duerme a los 15 minutos | Permanece despierto (o con ping) | Nunca |
| **Bloqueo IP YouTube** | Alto (IPs de AWS/Render bloqueadas) | Medio | **Cero bloqueo (Tu IP de casa)** |
| **Costo** | Gratis | **100% Gratis para siempre** | Gratis |

💡 **ClipForge AI está diseñado para funcionar en los 3 entornos**:
1. **Hugging Face Spaces**: La opción en la nube definitiva sin gastar un solo centavo.
2. **Local (Docker / Python)**: Para procesar videos sin restricciones de IP de YouTube.
3. **Render**: Incluye modo de ultra-baja memoria (`LOW_MEMORY_MODE=true` a 720p y `-threads 2`) por si decides usarlo en Render.

---

## 🚀 Arquitectura y Tecnologías

1. **Entrada Dual**:
   - URL de YouTube (video o stream).
   - **Subida directa de video (MP4, MOV, WebM)**: Permite procesar archivos desde tu PC si YouTube bloquea la IP del servidor en la nube.
   - Soporte para importar `cookies.txt` con 1 clic para bypass de bots.
2. **Extracción y Transcripción**:
   - Descarga **únicamente el audio** a 128 kbps (ahorro del 90% de ancho de banda).
   - **Groq Whisper** (`whisper-large-v3-turbo`): Transcribe videos de 20 minutos en apenas **3 a 5 segundos** con marcas de tiempo a nivel de palabra.
   - Alternativa: **Google Gemini Flash** (vía SDK oficial `google-genai`).
3. **Detección Inteligente de Ganchos (Virality Brain)**:
   - Modelo LLM (Gemini 2.5 Flash o Groq Llama 3.3 70B).
   - Extrae el gancho inicial (primeros 3-5s), arco temático completo (30s a 60s), estimación de impacto viral (puntuación de 0 a 100), explicación y hashtags listos para copiar.
4. **Corte y Edición 9:16 (FFmpeg Engine)**:
   - `yt-dlp --download-sections`: Descarga **solo el fragmento exacto** del video en lugar del stream completo.
   - **Modos de diseño vertical**:
     - 🟣 **Fondo Borroso Cinematográfico (Blur Pillarbox)**: Mantiene el video nítido en el centro con un fondo desenfocado oscuro. Ideal para podcasts, entrevistas y streams (no corta cabezas ni caras).
     - 🔵 **Recorte Inteligente al Centro**: Zoom vertical 9:16 para planos individuales.
     - ⚪ **Original**: Mantener aspecto 16:9 con subtítulos.
5. **Subtítulos Animados Estilo TikTok / Alex Hormozi**:
   - Generación de archivos `.ass` con resaltado dinámico de la palabra activa en amarillo neón (`#FFFF00`) o cyan (`#00FFFF`).
   - Fuente gruesa en mayúsculas, contorno negro profundo y ubicada en la zona segura (por encima de los botones de TikTok/Shorts).
6. **Almacenamiento y Descarga**:
   - Servidor directo o integración opcional con **Cloudflare R2** (10 GB gratis).

---

## 🛠️ Guía de Despliegue Rápido

### Opción 1: En Hugging Face Spaces (El mejor host gratuito en la nube)
1. Crea una cuenta gratuita en [Hugging Face](https://huggingface.co/).
2. Haz clic en **Spaces** > **Create new Space**.
3. Selecciona:
   - **Space SDK**: `Docker` > `Blank`.
   - **Space Hardware**: `CPU basic • 2 vCPU • 16GB RAM` (**Gratis**).
4. Sube los archivos de este repositorio o conecta tu repositorio de GitHub.
5. En la pestaña **Settings** > **Variables and secrets**, añade:
   - `GROQ_API_KEY`: Tu clave de [Groq Console](https://console.groq.com/keys) (gratuita).
   - `GEMINI_API_KEY`: Tu clave de [Google AI Studio](https://aistudio.google.com/app/apikey) (gratuita).
6. ¡Listo! Tu aplicación estará activa en `https://huggingface.co/spaces/tu-usuario/nombre-space`.

---

### Opción 2: En Render (Web Service con Docker)
1. Crea una cuenta en [Render.com](https://render.com/).
2. Haz clic en **New +** > **Web Service**.
3. Conecta tu repositorio de GitHub con este código.
4. Selecciona **Environment**: `Docker`.
5. En **Environment Variables**, define:
   - `LOW_MEMORY_MODE`: `true` (Obligatorio para no sobrepasar los 512 MB).
   - `GROQ_API_KEY`: Tu API key de Groq.
   - `GEMINI_API_KEY`: Tu API key de Gemini.
6. Haz clic en **Deploy Web Service**.

---

### Opción 3: Ejecución Local en tu PC (Máxima velocidad, 0 bloqueos)

#### Con Docker:
```bash
docker compose up --build
```
Abre tu navegador en `http://localhost:7860`.

#### Con Python directo:
```bash
# 1. Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1    # (En Linux/Mac: source venv/bin/activate)

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar la aplicación
python -m uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```
Abre tu navegador en `http://localhost:7860`.

---

## 🔑 Cómo obtener las APIs Gratuitas

1. **Groq API** *(Recomendada para Whisper ultrarrápido)*:
   - Entra a [console.groq.com](https://console.groq.com/keys).
   - Crea una cuenta gratuita y genera un API Key. Te da miles de segundos de transcripción diaria a velocidad récord.
2. **Google Gemini API** *(Para detección de ganchos virales)*:
   - Entra a [aistudio.google.com](https://aistudio.google.com/app/apikey).
   - Haz clic en **Create API Key**. El tier gratuito incluye miles de peticiones al día de Gemini 2.5 Flash.
3. **Cloudflare R2** *(Opcional)*:
   - En [Cloudflare Dashboard](https://dash.cloudflare.com/), ve a **R2 Object Storage**.
   - Crea un bucket (tienes 10 GB de almacenamiento y descargas ilimitadas gratis).

---

## 🛡️ Solución al bloqueo de bots de YouTube

Si despliegas en la nube (Render o Hugging Face) y YouTube bloquea la descarga con el error *"Sign in to confirm you're not a bot"*:
1. **Solución 1 (Más rápida)**: Usa la pestaña **Subir Video (MP4 / MOV)** en la web y sube el video o fragmento directamente.
2. **Solución 2 (Cookies)**:
   - Instala en tu navegador Chrome la extensión `Get cookies.txt LOCALLY`.
   - Entra a YouTube y exporta tus cookies.
   - En la web de ClipForge, ve a **Configurar APIs** y pega el texto de las cookies en el campo correspondiente.

---

## 📄 Estructura del Proyecto

```
clipping/
├── Dockerfile                 # Contenedor optimizado con FFmpeg y fuentes
├── docker-compose.yml         # Orquestación local en un comando
├── requirements.txt           # Dependencias Python
├── .env.example               # Plantilla de variables de entorno
├── README.md                  # Documentación completa
├── app/
│   ├── main.py                # Servidor FastAPI y endpoints REST
│   ├── core/
│   │   ├── config.py          # Configuración y autodescubrimiento de FFmpeg
│   │   └── models.py          # Esquemas Pydantic
│   ├── services/
│   │   ├── downloader.py      # yt-dlp con descarga por secciones y cookies
│   │   ├── transcriber.py     # Groq Whisper (con marcas de palabra) + Gemini
│   │   ├── ai_analyzer.py     # Gemini Flash y Groq Llama para ganchos virales
│   │   ├── subtitle_generator.py # Generador ASS con palabras animadas
│   │   ├── video_editor.py    # FFmpeg 9:16 con fondo desenfocado y subtítulos
│   │   ├── storage.py         # Subida a Cloudflare R2 / almacenamiento local
│   │   └── pipeline.py        # Orquestador del flujo con progreso en vivo
│   ├── static/
│   │   ├── css/styles.css     # Estilos y animaciones
│   │   └── js/app.js          # Lógica frontend interactiva
│   └── templates/
│       └── index.html         # Interfaz web moderna estilo OpusClip
```
