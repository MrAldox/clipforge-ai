document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentUploadedFilename = null;
    let activeJobId = null;
    let pollInterval = null;

    // Elements - Tabs
    const tabYoutube = document.getElementById("tabYoutube");
    const tabUpload = document.getElementById("tabUpload");
    const youtubePanel = document.getElementById("youtubePanel");
    const uploadPanel = document.getElementById("uploadPanel");

    // Elements - YouTube
    const youtubeUrlInput = document.getElementById("youtubeUrl");
    const fetchInfoBtn = document.getElementById("fetchInfoBtn");
    const videoPreviewCard = document.getElementById("videoPreviewCard");
    const previewThumbnail = document.getElementById("previewThumbnail");
    const previewTitle = document.getElementById("previewTitle");
    const previewDuration = document.getElementById("previewDuration");
    const previewChannel = document.getElementById("previewChannel");

    // Elements - Upload
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const uploadedFileStatus = document.getElementById("uploadedFileStatus");
    const uploadedFileName = document.getElementById("uploadedFileName");
    const uploadedFileSize = document.getElementById("uploadedFileSize");
    const removeFileBtn = document.getElementById("removeFileBtn");

    // Elements - Options
    const layoutSelect = document.getElementById("layoutSelect");
    const durationSelect = document.getElementById("durationSelect");
    const subtitleSelect = document.getElementById("subtitleSelect");
    const clipsCountSelect = document.getElementById("clipsCountSelect");
    const startClippingBtn = document.getElementById("startClippingBtn");

    // Elements - Progress
    const processingSection = document.getElementById("processingSection");
    const processingStepTitle = document.getElementById("processingStepTitle");
    const progressPercent = document.getElementById("progressPercent");
    const progressBar = document.getElementById("progressBar");
    const stepAudio = document.getElementById("stepAudio");
    const stepTranscript = document.getElementById("stepTranscript");
    const stepViral = document.getElementById("stepViral");
    const stepRender = document.getElementById("stepRender");

    // Elements - Results
    const resultsSection = document.getElementById("resultsSection");
    const clipsGrid = document.getElementById("clipsGrid");
    const resetBtn = document.getElementById("resetBtn");

    // Elements - Settings Modal
    const openSettingsBtn = document.getElementById("openSettingsBtn");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    const settingsModal = document.getElementById("settingsModal");
    const inputGroqKey = document.getElementById("inputGroqKey");
    const inputGeminiKey = document.getElementById("inputGeminiKey");
    const inputCookies = document.getElementById("inputCookies");

    // Elements - Toast
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toastMsg");

    // Helper: Toast
    function showToast(message) {
        toastMsg.textContent = message;
        toast.classList.remove("translate-y-24", "opacity-0");
        setTimeout(() => {
            toast.classList.add("translate-y-24", "opacity-0");
        }, 3000);
    }

    // Load stored settings
    inputGroqKey.value = localStorage.getItem("clipforge_groq_key") || "";
    inputGeminiKey.value = localStorage.getItem("clipforge_gemini_key") || "";
    inputCookies.value = localStorage.getItem("clipforge_cookies") || "";

    // Settings Modal handlers
    openSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("hidden"));
    const closeSettings = () => settingsModal.classList.add("hidden");
    closeSettingsBtn.addEventListener("click", closeSettings);
    cancelSettingsBtn.addEventListener("click", closeSettings);

    saveSettingsBtn.addEventListener("click", () => {
        localStorage.setItem("clipforge_groq_key", inputGroqKey.value.trim());
        localStorage.setItem("clipforge_gemini_key", inputGeminiKey.value.trim());
        localStorage.setItem("clipforge_cookies", inputCookies.value.trim());
        closeSettings();
        showToast("Configuración guardada correctamente");
    });

    // Tab switching
    tabYoutube.addEventListener("click", () => {
        tabYoutube.classList.add("border-indigo-500", "text-white");
        tabYoutube.classList.remove("border-transparent", "text-slate-400");
        tabUpload.classList.remove("border-indigo-500", "text-white");
        tabUpload.classList.add("border-transparent", "text-slate-400");
        youtubePanel.classList.remove("hidden");
        uploadPanel.classList.add("hidden");
    });

    tabUpload.addEventListener("click", () => {
        tabUpload.classList.add("border-indigo-500", "text-white");
        tabUpload.classList.remove("border-transparent", "text-slate-400");
        tabYoutube.classList.remove("border-indigo-500", "text-white");
        tabYoutube.classList.add("border-transparent", "text-slate-400");
        uploadPanel.classList.remove("hidden");
        youtubePanel.classList.add("hidden");
    });

    // YouTube Info Preview
    fetchInfoBtn.addEventListener("click", async () => {
        const url = youtubeUrlInput.value.trim();
        if (!url) {
            showToast("Por favor ingresa una URL de YouTube");
            return;
        }

        fetchInfoBtn.disabled = true;
        fetchInfoBtn.innerHTML = `<span class="animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full mr-2"></span> Cargando...`;

        try {
            const res = await fetch(`/api/video-info?url=${encodeURIComponent(url)}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error al obtener video");

            previewThumbnail.src = data.thumbnail;
            previewTitle.textContent = data.title;
            const minutes = Math.floor(data.duration / 60);
            const seconds = data.duration % 60;
            previewDuration.querySelector("span").textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            previewChannel.querySelector("span").textContent = data.channel;
            videoPreviewCard.classList.remove("hidden");
            lucide.createIcons();
        } catch (err) {
            showToast(err.message);
        } finally {
            fetchInfoBtn.disabled = false;
            fetchInfoBtn.innerHTML = `<i data-lucide="search" class="w-4 h-4"></i><span>Vista previa</span>`;
            lucide.createIcons();
        }
    });

    // File Upload Handlers
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("border-indigo-500");
    });
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-indigo-500");
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-indigo-500");
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            handleFileUpload(e.target.files[0]);
        }
    });

    removeFileBtn.addEventListener("click", () => {
        currentUploadedFilename = null;
        uploadedFileStatus.classList.add("hidden");
        dropZone.classList.remove("hidden");
        fileInput.value = "";
    });

    async function handleFileUpload(file) {
        dropZone.classList.add("opacity-50", "pointer-events-none");
        showToast("Subiendo video al servidor...");

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error subiendo video");

            currentUploadedFilename = data.filename;
            uploadedFileName.textContent = data.original_name;
            uploadedFileSize.textContent = `(${data.size_mb} MB)`;
            dropZone.classList.add("hidden");
            uploadedFileStatus.classList.remove("hidden");
            showToast("Video cargado con éxito");
            lucide.createIcons();
        } catch (err) {
            showToast(err.message);
        } finally {
            dropZone.classList.remove("opacity-50", "pointer-events-none");
        }
    }

    // Start Clipping Job
    startClippingBtn.addEventListener("click", async () => {
        const isYoutube = !youtubePanel.classList.contains("hidden");
        const videoUrl = youtubeUrlInput.value.trim();

        if (isYoutube && !videoUrl) {
            showToast("Ingresa un enlace de YouTube válido");
            return;
        }
        if (!isYoutube && !currentUploadedFilename) {
            showToast("Sube un archivo de video primero");
            return;
        }

        const groqKey = localStorage.getItem("clipforge_groq_key") || "";
        const geminiKey = localStorage.getItem("clipforge_gemini_key") || "";
        const cookies = localStorage.getItem("clipforge_cookies") || "";

        const payload = {
            video_url: isYoutube ? videoUrl : null,
            uploaded_filename: !isYoutube ? currentUploadedFilename : null,
            layout: layoutSelect.value,
            target_duration: durationSelect.value,
            subtitles_style: subtitleSelect.value,
            num_clips: parseInt(clipsCountSelect.value),
            groq_api_key: groqKey || null,
            gemini_api_key: geminiKey || null,
            cookies_content: cookies || null
        };

        startClippingBtn.disabled = true;
        startClippingBtn.classList.add("opacity-60", "cursor-not-allowed");

        try {
            const res = await fetch("/api/clips/create", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Error al iniciar proceso");

            activeJobId = data.job_id;
            resultsSection.classList.add("hidden");
            processingSection.classList.remove("hidden");
            processingSection.scrollIntoView({ behavior: "smooth" });

            // Start polling
            pollInterval = setInterval(pollJobStatus, 2000);
        } catch (err) {
            showToast(err.message);
            startClippingBtn.disabled = false;
            startClippingBtn.classList.remove("opacity-60", "cursor-not-allowed");
        }
    });

    // Poll status
    async function pollJobStatus() {
        if (!activeJobId) return;

        try {
            const res = await fetch(`/api/clips/status/${activeJobId}`);
            const job = await res.json();
            if (!res.ok) throw new Error(job.detail || "Error de estado");

            // Update UI
            progressPercent.textContent = `${job.progress}%`;
            progressBar.style.width = `${job.progress}%`;
            processingStepTitle.textContent = job.step_message;

            // Highlight stepper icons
            highlightSteps(job.status);

            if (job.status === "completed") {
                clearInterval(pollInterval);
                processingSection.classList.add("hidden");
                renderClips(job.clips);
                resultsSection.classList.remove("hidden");
                resultsSection.scrollIntoView({ behavior: "smooth" });
                startClippingBtn.disabled = false;
                startClippingBtn.classList.remove("opacity-60", "cursor-not-allowed");
                showToast("¡Tus clips virales están listos!");
            } else if (job.status === "failed") {
                clearInterval(pollInterval);
                processingSection.classList.add("hidden");
                startClippingBtn.disabled = false;
                startClippingBtn.classList.remove("opacity-60", "cursor-not-allowed");
                alert(`Error en el proceso: ${job.error || job.step_message}`);
            }
        } catch (err) {
            console.error("Poll error:", err);
        }
    }

    function highlightSteps(status) {
        const steps = [
            { el: stepAudio, active: ["downloading", "transcribing", "analyzing", "clipping", "completed"] },
            { el: stepTranscript, active: ["transcribing", "analyzing", "clipping", "completed"] },
            { el: stepViral, active: ["analyzing", "clipping", "completed"] },
            { el: stepRender, active: ["clipping", "completed"] }
        ];

        steps.forEach(s => {
            const icon = s.el.querySelector("i");
            if (s.active.includes(status)) {
                s.el.classList.add("border-indigo-500/50", "bg-indigo-950/20");
                if (icon) icon.classList.remove("text-slate-500");
                if (icon) icon.classList.add("text-indigo-400");
            }
        });
    }

    // Render Clips
    function renderClips(clips) {
        clipsGrid.innerHTML = "";
        if (!clips || !clips.length) {
            clipsGrid.innerHTML = `<p class="text-slate-400 text-center col-span-full py-8">No se generaron clips.</p>`;
            return;
        }

        clips.forEach((clip, index) => {
            const m = clip.moment;
            const scoreColor = m.virality_score >= 90 ? "from-amber-500 to-red-500 text-white" : "from-emerald-500 to-teal-500 text-white";

            const card = document.createElement("div");
            card.className = "clip-card bg-dark-800 border border-dark-700 rounded-2xl overflow-hidden flex flex-col";

            card.innerHTML = `
                <!-- Video Container -->
                <div class="relative w-full aspect-9-16 bg-black flex items-center justify-center">
                    <video src="${clip.video_url}" controls playsinline preload="metadata" class="w-full h-full object-cover"></video>
                    <!-- Score Badge -->
                    <div class="absolute top-3 right-3 px-3 py-1 rounded-full bg-gradient-to-r ${scoreColor} shadow-lg font-black text-xs flex items-center space-x-1">
                        <i data-lucide="flame" class="w-3.5 h-3.5"></i>
                        <span>${m.virality_score}/100</span>
                    </div>
                </div>

                <!-- Info Body -->
                <div class="p-5 flex-1 flex flex-col justify-between space-y-4">
                    <div>
                        <div class="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-mono">
                            <span>Clip #${index + 1}</span>
                            <span>${m.duration}s</span>
                        </div>
                        <h3 class="font-bold text-white text-base line-clamp-2">${m.title}</h3>
                        
                        <div class="mt-2.5 p-2.5 rounded-lg bg-dark-900/60 border border-dark-700/60 text-xs text-indigo-300">
                            <span class="font-bold text-indigo-400 uppercase tracking-wider text-[10px] block mb-0.5">Gancho Inicial:</span>
                            "${m.hook}"
                        </div>

                        <p class="mt-2 text-xs text-slate-400 line-clamp-2">${m.virality_reason}</p>
                    </div>

                    <!-- Action Buttons -->
                    <div class="pt-3 border-t border-dark-700/80 flex flex-col gap-2">
                        <a href="${clip.video_url}" download="${clip.video_filename}" class="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold text-center transition flex items-center justify-center space-x-2 shadow-md shadow-indigo-600/20">
                            <i data-lucide="download" class="w-4 h-4"></i>
                            <span>Descargar Clip (${clip.file_size_mb} MB)</span>
                        </a>
                        <button class="copy-meta-btn w-full py-2 px-4 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-200 text-xs font-semibold text-center transition flex items-center justify-center space-x-1.5 border border-dark-600">
                            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                            <span>Copiar Título y Hashtags</span>
                        </button>
                    </div>
                </div>
            `;

            // Copy metadata handler
            const copyBtn = card.querySelector(".copy-meta-btn");
            copyBtn.addEventListener("click", () => {
                const hashtagsText = (m.hashtags || []).join(" ");
                const textToCopy = `${m.title}\n\n${m.suggested_caption}\n\n${hashtagsText}`;
                navigator.clipboard.writeText(textToCopy);
                showToast("¡Título y hashtags copiados!");
            });

            clipsGrid.appendChild(card);
        });

        lucide.createIcons();
    }

    resetBtn.addEventListener("click", () => {
        resultsSection.classList.add("hidden");
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
});
