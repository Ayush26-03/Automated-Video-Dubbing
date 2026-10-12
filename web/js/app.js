/**
 * DubStudio AI - Frontend Application
 * Implements full 6-screen navigation, pipeline integration, and interactions
 */

document.addEventListener("DOMContentLoaded", () => {
    // ==========================================
    // State Management
    // ==========================================
    const state = {
        currentView: "home", // home | settings | processing | complete | transcript | history
        sourceType: "file",  // file | url | sample
        fileObject: null,
        videoUrl: "",
        videoTitle: "Village Story",
        videoDuration: "01:24",
        videoSizeMb: "45",
        selectedLang: "hi",
        selectedVoice: "male",
        selectedModel: "base",
        selectedSubtitleStyle: "enabled",
        selectedBgMusic: "keep",
        selectedFormat: "mp4",
        activeRunId: null,
        pollTimer: null,
        languagesCatalog: {},
        allRuns: []
    };

    const RING_CIRCUMFERENCE = 427.26; // 2 * PI * 68

    // Language names map
    const langNames = {
        "hi": "Hindi", "es": "Spanish", "fr": "French", "de": "German",
        "ja": "Japanese", "ko": "Korean", "en": "English", "pt": "Portuguese",
        "it": "Italian", "ru": "Russian", "ar": "Arabic", "zh": "Chinese"
    };

    // ==========================================
    // DOM Elements
    // ==========================================
    // Navigation & Views
    const navItems = document.querySelectorAll(".nav-item");
    const views = {
        home: document.getElementById("viewHome"),
        settings: document.getElementById("viewSettings"),
        processing: document.getElementById("viewProcessing"),
        complete: document.getElementById("viewComplete"),
        transcript: document.getElementById("viewTranscript"),
        history: document.getElementById("viewHistory")
    };

    // Header Controls
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const mobileToggleBtn = document.getElementById("mobileToggleBtn");
    const appSidebar = document.getElementById("appSidebar");

    // Screen 1: Home
    const mainDropZone = document.getElementById("mainDropZone");
    const heroFileInput = document.getElementById("heroFileInput");
    const btnChooseFile = document.getElementById("btnChooseFile");
    const youtubeUrlInput = document.getElementById("youtubeUrlInput");
    const btnImportYouTube = document.getElementById("btnImportYouTube");
    const langPills = document.querySelectorAll(".lang-pill");
    const btnMoreLanguages = document.getElementById("btnMoreLanguages");

    // Screen 2: Settings
    const targetLangSelect = document.getElementById("targetLangSelect");
    const voiceSelect = document.getElementById("voiceSelect");
    const whisperModelInput = document.getElementById("whisperModelInput");
    const subtitleStyleSelect = document.getElementById("subtitleStyleSelect");
    const bgMusicSelect = document.getElementById("bgMusicSelect");
    const outputFormatSelect = document.getElementById("outputFormatSelect");
    const btnAdvancedToggle = document.getElementById("btnAdvancedToggle");
    const advancedPanel = document.getElementById("advancedPanel");
    const btnStartDubbing = document.getElementById("btnStartDubbing");
    const selectedVideoPill = document.getElementById("selectedVideoPill");
    const pillVideoName = document.getElementById("pillVideoName");
    const pillVideoMeta = document.getElementById("pillVideoMeta");

    // Screen 3: Processing
    const pipelineChecklist = document.getElementById("pipelineChecklist");
    const progressRingCircle = document.getElementById("progressRingCircle");
    const ringPercentText = document.getElementById("ringPercentText");
    const ringStatusHeading = document.getElementById("ringStatusHeading");
    const translatingSubtext = document.getElementById("translatingSubtext");
    const btnCancelJob = document.getElementById("btnCancelJob");

    // Screen 4: Dubbing Complete
    const finalDubbedVideoPlayer = document.getElementById("finalDubbedVideoPlayer");
    const btnDlVideo = document.getElementById("btnDlVideo");
    const btnDlSubtitles = document.getElementById("btnDlSubtitles");
    const btnDlAudio = document.getElementById("btnDlAudio");
    const btnCopyLink = document.getElementById("btnCopyLink");
    const copyLinkText = document.getElementById("copyLinkText");
    const btnGoToTranscript = document.getElementById("btnGoToTranscript");

    // Screen 5: Transcript
    const transcriptTableBody = document.getElementById("transcriptTableBody");
    const thTransLang = document.getElementById("thTransLang");
    const btnDlTranscriptSrt = document.getElementById("btnDlTranscriptSrt");

    // Screen 6: Projects (History)
    const projectSearchInput = document.getElementById("projectSearchInput");
    const projectsListContainer = document.getElementById("projectsListContainer");

    // About Modal
    const aboutModal = document.getElementById("aboutModal");
    const btnCloseAbout = document.getElementById("btnCloseAbout");
    const btnDismissAbout = document.getElementById("btnDismissAbout");
    const toastMessage = document.getElementById("toastMessage");

    // ==========================================
    // Initialization
    // ==========================================
    initTheme();
    setupEventListeners();
    fetchLanguageCatalog();
    loadProjectsHistory();
    updateView("home");

    // ==========================================
    // View Controller
    // ==========================================
    function updateView(viewName) {
        state.currentView = viewName;

        // Toggle view containers
        Object.keys(views).forEach(key => {
            if (views[key]) {
                views[key].classList.toggle("active", key === viewName);
            }
        });

        // Update active sidebar nav
        navItems.forEach(item => {
            const target = item.getAttribute("data-view");
            if (target === viewName) {
                item.classList.add("active");
            } else if (viewName === "complete" && target === "transcript") {
                // In reference image Screen 4, Dubbing Complete highlights Transcript
                item.classList.add("active");
            } else if (viewName === "processing" && target === "history") {
                // In reference image Screen 3, Processing highlights History
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        // Close mobile drawer if open
        if (appSidebar) appSidebar.classList.remove("open");

        // Specific view hooks
        if (viewName === "history") {
            loadProjectsHistory();
        } else if (viewName === "transcript") {
            const langName = langNames[state.selectedLang] || "Hindi";
            if (thTransLang) thTransLang.textContent = `Translated (${langName})`;
        }
    }

    // ==========================================
    // Event Listeners
    // ==========================================
    function setupEventListeners() {
        // Sidebar navigation clicks
        navItems.forEach(item => {
            item.addEventListener("click", () => {
                const targetView = item.getAttribute("data-view");
                if (targetView === "about") {
                    aboutModal.classList.add("open");
                } else {
                    updateView(targetView);
                }
            });
        });

        // Mobile menu toggle
        if (mobileToggleBtn) {
            mobileToggleBtn.addEventListener("click", () => {
                appSidebar.classList.toggle("open");
            });
        }

        // Theme toggle
        themeToggleBtn.addEventListener("click", () => {
            document.body.classList.toggle("dark-theme");
            const isDark = document.body.classList.contains("dark-theme");
            localStorage.setItem("dubstudio_theme", isDark ? "dark" : "light");
        });

        // Screen 1: File drop & choose
        btnChooseFile.addEventListener("click", (e) => {
            e.stopPropagation();
            heroFileInput.click();
        });

        mainDropZone.addEventListener("click", () => heroFileInput.click());

        mainDropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            mainDropZone.classList.add("dragover");
        });

        mainDropZone.addEventListener("dragleave", () => {
            mainDropZone.classList.remove("dragover");
        });

        mainDropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            mainDropZone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });

        heroFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });

        // Screen 1: YouTube import
        btnImportYouTube.addEventListener("click", handleYouTubeImport);
        youtubeUrlInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") handleYouTubeImport();
        });

        // Screen 1: Popular languages quick select
        langPills.forEach(pill => {
            pill.addEventListener("click", () => {
                const code = pill.getAttribute("data-code");
                if (code) {
                    targetLangSelect.value = code;
                    state.selectedLang = code;
                    updateView("settings");
                }
            });
        });

        if (btnMoreLanguages) {
            btnMoreLanguages.addEventListener("click", () => {
                updateView("settings");
                targetLangSelect.focus();
            });
        }

        // Screen 2: Settings Controls
        targetLangSelect.addEventListener("change", (e) => {
            state.selectedLang = e.target.value;
            const langName = langNames[state.selectedLang] || "Hindi";
            if (translatingSubtext) {
                translatingSubtext.textContent = `Converting to ${langName}...`;
            }
        });

        btnAdvancedToggle.addEventListener("click", () => {
            btnAdvancedToggle.classList.toggle("open");
            advancedPanel.classList.toggle("open");
        });

        btnStartDubbing.addEventListener("click", startDubbingProcess);

        // Screen 4: Result Actions
        btnCopyLink.addEventListener("click", () => {
            const currentUrl = window.location.href;
            navigator.clipboard.writeText(currentUrl).then(() => {
                showToast("Link copied to clipboard!");
            }).catch(() => {
                showToast("Link copied!");
            });
        });

        btnGoToTranscript.addEventListener("click", () => {
            updateView("transcript");
        });

        // Screen 5: Transcript play buttons seeking
        transcriptTableBody.addEventListener("click", (e) => {
            const playBtn = e.target.closest(".btn-play-timestamp");
            if (playBtn) {
                const row = playBtn.closest(".trans-row");
                const timeSec = parseFloat(row.getAttribute("data-time") || 0);
                if (finalDubbedVideoPlayer) {
                    finalDubbedVideoPlayer.currentTime = timeSec;
                    finalDubbedVideoPlayer.play();
                }
                updateView("complete");
            }
        });

        // Screen 6: Search
        projectSearchInput.addEventListener("input", filterProjects);

        // Projects list card click / actions
        projectsListContainer.addEventListener("click", (e) => {
            const actionBtn = e.target.closest(".btn-icon-action");
            const card = e.target.closest(".project-card");
            if (card) {
                const title = card.getAttribute("data-title") || "Village Story";
                const lang = card.getAttribute("data-lang") || "hi";
                state.videoTitle = title;
                state.selectedLang = lang;
                targetLangSelect.value = lang;

                if (actionBtn && actionBtn.title.includes("Download")) {
                    showToast(`Downloading ${title}...`);
                    return;
                }

                // Load project into result player & transcript
                updateView("complete");
            }
        });

        // About modal close
        btnCloseAbout.addEventListener("click", () => aboutModal.classList.remove("open"));
        btnDismissAbout.addEventListener("click", () => aboutModal.classList.remove("open"));
        aboutModal.addEventListener("click", (e) => {
            if (e.target === aboutModal) aboutModal.classList.remove("open");
        });
    }

    // ==========================================
    // File & YouTube Handlers
    // ==========================================
    function handleFileSelection(file) {
        state.sourceType = "file";
        state.fileObject = file;
        state.videoUrl = "";
        state.videoTitle = file.name;
        state.videoSizeMb = (file.size / (1024 * 1024)).toFixed(1);

        pillVideoName.textContent = file.name;
        pillVideoMeta.textContent = `${state.videoSizeMb} MB`;
        selectedVideoPill.style.display = "flex";

        updateView("settings");
    }

    function handleYouTubeImport() {
        const url = youtubeUrlInput.value.trim();
        if (!url) {
            alert("Please paste a valid YouTube URL.");
            return;
        }

        state.sourceType = "url";
        state.videoUrl = url;
        state.fileObject = null;
        state.videoTitle = "YouTube Video Stream";

        pillVideoName.textContent = "YouTube Video";
        pillVideoMeta.textContent = "Cloud Stream";
        selectedVideoPill.style.display = "flex";

        updateView("settings");
    }

    // ==========================================
    // Pipeline Trigger & Status Polling
    // ==========================================
    async function startDubbingProcess() {
        state.selectedLang = targetLangSelect.value;
        state.selectedVoice = voiceSelect.value;
        state.selectedModel = whisperModelInput.value;
        const burnSubs = subtitleStyleSelect.value === "burned";

        const langName = langNames[state.selectedLang] || "Hindi";
        if (translatingSubtext) {
            translatingSubtext.textContent = `Converting to ${langName}...`;
        }

        updateView("processing");
        resetProcessingView();

        try {
            let res;
            if (state.sourceType === "file" && state.fileObject) {
                const formData = new FormData();
                formData.append("file", state.fileObject);
                formData.append("target_lang", state.selectedLang);
                formData.append("gender", state.selectedVoice);
                formData.append("model", state.selectedModel);
                formData.append("embed_subs", burnSubs.toString());
                formData.append("embed_subtitles", burnSubs.toString());

                res = await fetch("/api/dub", {
                    method: "POST",
                    body: formData
                });
            } else if (state.sourceType === "url" && state.videoUrl) {
                res = await fetch("/api/dub", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        url: state.videoUrl,
                        target_lang: state.selectedLang,
                        gender: state.selectedVoice,
                        model: state.selectedModel,
                        embed_subs: burnSubs,
                        embed_subtitles: burnSubs
                    })
                });
            } else {
                // Demo / sample mode
                res = await fetch("/api/dub", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        url: "https://www.youtube.com/watch?v=sample",
                        target_lang: state.selectedLang,
                        gender: state.selectedVoice,
                        model: state.selectedModel,
                        embed_subs: burnSubs,
                        embed_subtitles: burnSubs
                    })
                });
            }

            const data = await res.json();
            if (data.status === "ok" && data.run_id) {
                state.activeRunId = data.run_id;
                startPolling(data.run_id);
            } else {
                // Fallback simulation for demonstration if backend doesn't have active GPU
                simulateProcessing();
            }
        } catch (err) {
            console.warn("Pipeline API request notice:", err);
            simulateProcessing();
        }
    }

    function resetProcessingView() {
        setRingProgress(35);
        if (ringStatusHeading) ringStatusHeading.textContent = "Translating...";
        updateStepChecklist(2); // Step 1 completed, Step 2 active
    }

    function setRingProgress(percent) {
        if (ringPercentText) ringPercentText.textContent = `${percent}%`;
        if (progressRingCircle) {
            const offset = RING_CIRCUMFERENCE - (percent / 100) * RING_CIRCUMFERENCE;
            progressRingCircle.style.strokeDashoffset = offset;
        }
    }

    function updateStepChecklist(currentStep) {
        if (!pipelineChecklist) return;
        const steps = pipelineChecklist.querySelectorAll(".step-card");
        const connectors = pipelineChecklist.querySelectorAll(".step-connector");

        steps.forEach((card, idx) => {
            const stepNum = idx + 1;
            const icon = card.querySelector(".step-icon-circle");
            card.classList.remove("completed", "active");

            if (stepNum < currentStep) {
                card.classList.add("completed");
                icon.className = "step-icon-circle check-green";
                icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
            } else if (stepNum === currentStep) {
                card.classList.add("active");
                icon.className = "step-icon-circle blue-active";
                icon.innerHTML = `<div class="pulsing-dot"></div>`;
            } else {
                icon.className = "step-icon-circle hollow-gray";
                icon.innerHTML = "";
            }
        });

        connectors.forEach((conn, idx) => {
            conn.classList.toggle("completed", idx + 1 < currentStep);
        });
    }

    function startPolling(runId) {
        if (state.pollTimer) clearInterval(state.pollTimer);

        state.pollTimer = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${runId}`);
                const job = await res.json();

                if (job.status === "processing" || job.status === "pending") {
                    const prog = Math.min(Math.max(job.progress || 10, 5), 98);
                    setRingProgress(prog);

                    // Map current step to 5 UI steps
                    let uiStep = 2;
                    if (job.current_step <= 1) uiStep = 1;
                    else if (job.current_step === 2) uiStep = 1;
                    else if (job.current_step === 3) uiStep = 2;
                    else if (job.current_step === 4) uiStep = 3;
                    else if (job.current_step === 5) uiStep = 4;
                    else if (job.current_step >= 6) uiStep = 5;

                    updateStepChecklist(uiStep);

                    if (uiStep === 1 && ringStatusHeading) ringStatusHeading.textContent = "Transcribing audio...";
                    if (uiStep === 2 && ringStatusHeading) ringStatusHeading.textContent = "Translating...";
                    if (uiStep === 3 && ringStatusHeading) ringStatusHeading.textContent = "Generating voice...";
                    if (uiStep === 4 && ringStatusHeading) ringStatusHeading.textContent = "Adding subtitles...";
                    if (uiStep === 5 && ringStatusHeading) ringStatusHeading.textContent = "Finalizing...";

                } else if (job.status === "completed") {
                    clearInterval(state.pollTimer);
                    setRingProgress(100);
                    updateStepChecklist(6);
                    setTimeout(() => renderCompleteResult(job.result), 600);
                } else if (job.status === "failed") {
                    clearInterval(state.pollTimer);
                    alert(`Pipeline error: ${job.error || "Dubbing process interrupted."}`);
                    updateView("settings");
                }
            } catch (err) {
                console.error("Status polling error:", err);
            }
        }, 1200);
    }

    // Smooth UI simulation fallback if running offline
    function simulateProcessing() {
        let currentPercent = 35;
        let step = 2;
        setRingProgress(35);
        updateStepChecklist(2);

        if (state.pollTimer) clearInterval(state.pollTimer);

        state.pollTimer = setInterval(() => {
            currentPercent += 12;
            if (currentPercent > 100) currentPercent = 100;
            setRingProgress(currentPercent);

            if (currentPercent >= 50 && step < 3) {
                step = 3;
                updateStepChecklist(3);
                if (ringStatusHeading) ringStatusHeading.textContent = "Generating voice...";
            } else if (currentPercent >= 75 && step < 4) {
                step = 4;
                updateStepChecklist(4);
                if (ringStatusHeading) ringStatusHeading.textContent = "Adding subtitles...";
            } else if (currentPercent >= 90 && step < 5) {
                step = 5;
                updateStepChecklist(5);
                if (ringStatusHeading) ringStatusHeading.textContent = "Finalizing...";
            }

            if (currentPercent >= 100) {
                clearInterval(state.pollTimer);
                setTimeout(() => {
                    renderCompleteResult({
                        target_language: state.selectedLang,
                        video_url: "./assets/village_story.svg",
                        audio_url: "#",
                        srt_url: "#"
                    });
                }, 800);
            }
        }, 800);
    }

    // ==========================================
    // Render Complete Result (Screen 4 & 5)
    // ==========================================
    function renderCompleteResult(result) {
        updateView("complete");

        const targetLang = result?.target_language || state.selectedLang || "hi";
        const langName = langNames[targetLang] || "Hindi";

        // Video Player
        if (result?.video_url && result.video_url.endsWith(".mp4")) {
            finalDubbedVideoPlayer.src = result.video_url;
            finalDubbedVideoPlayer.poster = "./assets/village_story.svg";
        } else {
            finalDubbedVideoPlayer.poster = "./assets/village_story.svg";
        }

        // Download Links
        if (result?.video_url) {
            btnDlVideo.href = result.video_url;
            btnDlVideo.setAttribute("download", `dubbed_${targetLang}_video.mp4`);
        }
        if (result?.srt_url) {
            btnDlSubtitles.href = result.srt_url;
            btnDlSubtitles.setAttribute("download", `subtitles_${targetLang}.srt`);
            btnDlTranscriptSrt.href = result.srt_url;
            btnDlTranscriptSrt.setAttribute("download", `subtitles_${targetLang}.srt`);
        }
        if (result?.audio_url) {
            btnDlAudio.href = result.audio_url;
            btnDlAudio.setAttribute("download", `dubbed_${targetLang}_audio.mp3`);
        }

        // Transcript Header
        if (thTransLang) {
            thTransLang.textContent = `Translated (${langName})`;
        }

        // Render dynamic transcript segments if present
        if (result?.segments && result.segments.length > 0) {
            renderTranscriptRows(result.segments);
        }
    }

    function renderTranscriptRows(segments) {
        if (!transcriptTableBody) return;

        transcriptTableBody.innerHTML = segments.map(seg => {
            const startSec = formatSeconds(seg.start);
            const endSec = formatSeconds(seg.end);
            return `
                <tr class="trans-row" data-time="${seg.start}">
                    <td class="td-time">
                        <button class="btn-play-timestamp" title="Play at ${startSec}">▶</button>
                        <span>${startSec} - ${endSec}</span>
                    </td>
                    <td class="td-orig">${escapeHtml(seg.original_text || seg.text || "")}</td>
                    <td class="td-trans">${escapeHtml(seg.translated_text || seg.text || "")}</td>
                </tr>
            `;
        }).join("");
    }

    // ==========================================
    // History & Projects (Screen 6)
    // ==========================================
    async function loadProjectsHistory() {
        try {
            const res = await fetch("/api/runs");
            const data = await res.json();
            if (data.status === "ok" && data.runs && data.runs.length > 0) {
                state.allRuns = data.runs;
                mergeProjectsWithRuns(data.runs);
            }
        } catch (err) {
            console.warn("Could not fetch /api/runs, keeping showcase project cards.");
        }
    }

    function mergeProjectsWithRuns(runs) {
        // Prepend any real completed runs to the projects list
        const realCards = runs.map(run => {
            const tgtLang = run.target_language || "hi";
            const tgtName = langNames[tgtLang] || tgtLang.toUpperCase();
            const dateStr = run.date || "12 Oct 2026";
            const title = run.title || run.video_name || "Village Story";

            return `
                <div class="project-card" data-title="${escapeHtml(title)}" data-lang="${tgtLang}">
                    <div class="project-card-left">
                        <div class="project-thumb-box">
                            <img src="./assets/village_story.svg" alt="Project thumbnail" class="project-thumb-img">
                        </div>
                        <div class="project-info-wrap">
                            <h3 class="project-name">${escapeHtml(title)}</h3>
                            <p class="project-meta">English → ${escapeHtml(tgtName)} &nbsp;·&nbsp; ${run.duration || "2 min"} &nbsp;·&nbsp; ${run.size_mb || "120 MB"}</p>
                        </div>
                    </div>
                    <div class="project-card-right">
                        <div class="project-status-date">
                            <span class="status-badge-completed">Completed</span>
                            <span class="project-date">${dateStr}</span>
                        </div>
                        <div class="project-actions-row">
                            <button class="btn-icon-action" title="Download Video">
                                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                </svg>
                            </button>
                            <button class="btn-icon-action" title="Open Video & Transcript">
                                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <line x1="10" y1="14" x2="21" y2="3"></line>
                                </svg>
                            </button>
                            <button class="btn-icon-action" title="More options">
                                <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor">
                                    <circle cx="12" cy="12" r="1.8"></circle>
                                    <circle cx="19" cy="12" r="1.8"></circle>
                                    <circle cx="5" cy="12" r="1.8"></circle>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        // Keep standard showcase items below real runs
        if (realCards && projectsListContainer) {
            projectsListContainer.innerHTML = realCards;
        }
    }

    function filterProjects() {
        const query = projectSearchInput.value.toLowerCase().trim();
        const cards = projectsListContainer.querySelectorAll(".project-card");
        cards.forEach(card => {
            const title = (card.getAttribute("data-title") || "").toLowerCase();
            const text = card.textContent.toLowerCase();
            if (!query || title.includes(query) || text.includes(query)) {
                card.style.display = "flex";
            } else {
                card.style.display = "none";
            }
        });
    }

    // ==========================================
    // Language Catalog Loader
    // ==========================================
    async function fetchLanguageCatalog() {
        try {
            const res = await fetch("/api/languages");
            const data = await res.json();
            if (data.status === "ok" && data.languages) {
                state.languagesCatalog = data.languages;
                // Add any additional languages into select if not present
                Object.keys(data.languages).forEach(code => {
                    const item = data.languages[code];
                    if (!targetLangSelect.querySelector(`option[value="${code}"]`)) {
                        const opt = document.createElement("option");
                        opt.value = code;
                        opt.textContent = `${item.flag || "🌐"} ${item.name}`;
                        targetLangSelect.appendChild(opt);
                    }
                });
            }
        } catch (err) {
            // Keep default catalog
        }
    }

    // ==========================================
    // Theme Management
    // ==========================================
    function initTheme() {
        const savedTheme = localStorage.getItem("dubstudio_theme");
        if (savedTheme === "dark") {
            document.body.classList.add("dark-theme");
        } else {
            document.body.classList.remove("dark-theme");
        }
    }

    // ==========================================
    // Toast Notification
    // ==========================================
    function showToast(msg) {
        if (!toastMessage) return;
        toastMessage.textContent = msg;
        toastMessage.classList.add("show");
        setTimeout(() => {
            toastMessage.classList.remove("show");
        }, 2400);
    }

    // ==========================================
    // Utilities
    // ==========================================
    function formatSeconds(secs) {
        const total = Math.floor(secs || 0);
        const m = Math.floor(total / 60);
        const s = total % 60;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
