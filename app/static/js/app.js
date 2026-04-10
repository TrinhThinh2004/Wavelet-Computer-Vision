/**
 * Wavelet Image Search Engine - Client-side JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // ── Elements ──────────────────────────────────────────
    const dropZone = document.getElementById('dropZone');
    const dropContent = document.getElementById('dropContent');
    const previewContainer = document.getElementById('previewContainer');
    const previewImage = document.getElementById('previewImage');
    const clearPreview = document.getElementById('clearPreview');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    const searchBtn = document.getElementById('searchBtn');
    const loading = document.getElementById('loading');
    const resultsSection = document.getElementById('resultsSection');
    const resultsGrid = document.getElementById('resultsGrid');
    const resultsCount = document.getElementById('resultsCount');
    const waveletCard = document.getElementById('waveletCard');
    const waveletImage = document.getElementById('waveletImage');
    const hashInfo = document.getElementById('hashInfo');
    const dbCount = document.getElementById('dbCount');
    const dbGrid = document.getElementById('dbGrid');
    const uploadToDbBtn = document.getElementById('uploadToDbBtn');
    const dbFileInput = document.getElementById('dbFileInput');
    const tabSearch = document.getElementById('tabSearch');
    const tabDatabase = document.getElementById('tabDatabase');
    const searchTab = document.getElementById('searchTab');
    const databaseTab = document.getElementById('databaseTab');

    const levelSelect = document.getElementById('levelSelect');
    const thresholdRange = document.getElementById('thresholdRange');
    const thresholdValue = document.getElementById('thresholdValue');

    let selectedFile = null;

    // ── Threshold slider live update ──────────────────────
    thresholdRange.addEventListener('input', () => {
        thresholdValue.textContent = thresholdRange.value;
    });

    // ── Tab Navigation ────────────────────────────────────
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            if (target === 'search') {
                searchTab.classList.add('active');
            } else {
                databaseTab.classList.add('active');
                loadDatabase();
            }
        });
    });

    // ── Drag & Drop ───────────────────────────────────────
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFile(files[0]);
    });

    // ── File Selection ────────────────────────────────────
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    dropZone.addEventListener('click', () => {
        if (!selectedFile) fileInput.click();
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    // ── Clear Preview ─────────────────────────────────────
    clearPreview.addEventListener('click', (e) => {
        e.stopPropagation();
        resetSearch();
    });

    function resetSearch() {
        selectedFile = null;
        previewContainer.style.display = 'none';
        dropContent.style.display = 'flex';
        searchBtn.disabled = true;
        waveletCard.style.display = 'none';
        resultsSection.style.display = 'none';
        fileInput.value = '';
    }

    function handleFile(file) {
        if (!file.type.startsWith('image/')) return;
        selectedFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            dropContent.style.display = 'none';
            previewContainer.style.display = 'flex';
            searchBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // ── Search ────────────────────────────────────────────
    searchBtn.addEventListener('click', performSearch);

    async function performSearch() {
        if (!selectedFile) return;

        loading.style.display = 'flex';
        resultsSection.style.display = 'none';
        waveletCard.style.display = 'none';
        searchBtn.disabled = true;

        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('top_k', 20);
        formData.append('level', levelSelect.value);
        formData.append('min_similarity', thresholdRange.value);

        try {
            const res = await fetch('/api/search', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.error) {
                alert('Lỗi: ' + data.error);
                return;
            }

            // Show wavelet visualization
            if (data.query && data.query.wavelet_viz) {
                waveletImage.src = 'data:image/png;base64,' + data.query.wavelet_viz;
                hashInfo.textContent = `Hash size: ${data.query.hash_size} bits  |  Wavelet: Haar  |  DWT Level: ${data.query.level}  |  Ngưỡng: ≥${thresholdRange.value}%`;
                waveletCard.style.display = 'block';
            }

            // Update DB count
            if (data.total_db !== undefined) {
                dbCount.textContent = data.total_db;
            }

            // Render results
            renderResults(data.results);

        } catch (err) {
            alert('Lỗi kết nối: ' + err.message);
        } finally {
            loading.style.display = 'none';
            searchBtn.disabled = false;
        }
    }

    function renderResults(results) {
        resultsGrid.innerHTML = '';
        resultsCount.textContent = `${results.length} kết quả`;

        if (results.length === 0) {
            resultsGrid.innerHTML = '<p style="color:var(--text-muted);padding:20px;grid-column:1/-1;text-align:center;">Không tìm thấy ảnh tương tự trong cơ sở dữ liệu.</p>';
            resultsSection.style.display = 'block';
            return;
        }

        results.forEach((r, idx) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.animationDelay = `${idx * 0.05}s`;

            const simClass = r.similarity >= 80 ? 'high' : r.similarity >= 50 ? 'medium' : 'low';
            const rankClass = idx < 3 ? 'top' : '';

            card.innerHTML = `
                <div class="img-wrapper">
                    <img src="${r.url}" alt="${r.filename}" loading="lazy">
                    <div class="rank-badge ${rankClass}">${idx + 1}</div>
                    <div class="similarity-bar">
                        <div class="similarity-fill" style="width:${r.similarity}%"></div>
                    </div>
                </div>
                <div class="info">
                    <div class="filename" title="${r.filename}">${r.filename}</div>
                    <div class="meta">
                        <span class="similarity ${simClass}">${r.similarity}%</span>
                        <span class="distance">HD: ${r.distance}</span>
                    </div>
                    <span class="category">${r.category}</span>
                </div>
            `;

            resultsGrid.appendChild(card);
        });

        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ── Database Tab ──────────────────────────────────────
    async function loadDatabase() {
        try {
            const res = await fetch('/api/images');
            const data = await res.json();

            dbCount.textContent = data.total;
            dbGrid.innerHTML = '';

            if (data.images.length === 0) {
                dbGrid.innerHTML = '<p style="color:var(--text-muted);padding:20px;grid-column:1/-1;text-align:center;">Chưa có ảnh nào trong cơ sở dữ liệu.</p>';
                return;
            }

            data.images.forEach((img, idx) => {
                const item = document.createElement('div');
                item.className = 'db-item';
                item.style.animationDelay = `${idx * 0.03}s`;

                item.innerHTML = `
                    <div class="img-wrapper">
                        <img src="${img.url}" alt="${img.filename}" loading="lazy">
                    </div>
                    <div class="db-info">
                        <div class="name" title="${img.filename}">${img.filename}</div>
                        <div class="cat">${img.category}</div>
                    </div>
                `;

                dbGrid.appendChild(item);
            });
        } catch (err) {
            console.error('Error loading database:', err);
        }
    }

    // ── Upload to DB ──────────────────────────────────────
    uploadToDbBtn.addEventListener('click', () => dbFileInput.click());
    dbFileInput.addEventListener('change', async () => {
        const files = dbFileInput.files;
        if (files.length === 0) return;

        for (const file of files) {
            if (!file.type.startsWith('image/')) continue;

            const formData = new FormData();
            formData.append('image', file);

            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.error) {
                    console.error('Upload error:', data.error);
                } else {
                    dbCount.textContent = data.total_db;
                }
            } catch (err) {
                console.error('Upload failed:', err);
            }
        }

        dbFileInput.value = '';
        loadDatabase();
    });

    // ── Initial Load ──────────────────────────────────────
    fetch('/api/images')
        .then(res => res.json())
        .then(data => { dbCount.textContent = data.total; })
        .catch(() => { });
});
