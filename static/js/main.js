/* ═══════════════════════════════════════════════════════════════
   PDFKu — Main JavaScript (index page)
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── DOM References ────────────────────────────────────────────
  const uploadZone     = document.getElementById('uploadZone');
  const fileInput      = document.getElementById('fileInput');
  const uploadFileInfo = document.getElementById('uploadFileInfo');
  const fileName       = document.getElementById('fileName');
  const fileSize       = document.getElementById('fileSize');
  const uploadBrowse   = document.getElementById('uploadBrowse');
  const compressBtn    = document.getElementById('compressBtn');
  const progressWrap   = document.getElementById('progressWrap');
  const progressFill   = document.getElementById('progressFill');
  const progressStatus = document.getElementById('progressStatus');
  const resultPanel    = document.getElementById('resultPanel');
  const resetBtn       = document.getElementById('resetBtn');
  const alertsWrapper  = document.getElementById('alertsWrapper');

  let selectedFiles = [];

  // ── Flash Alert System ─────────────────────────────────────────
  function showAlert(message, type = 'info', duration = 5000) {
    if (!alertsWrapper) return;

    // Premium design: High-quality SVG icons
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    
    const svgIcons = {
      success: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="alert-icon-svg" style="color:#6ee7b7; flex-shrink:0;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
      error: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="alert-icon-svg" style="color:#fca5a5; flex-shrink:0;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`,
      warning: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="alert-icon-svg" style="color:#fcd34d; flex-shrink:0;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
      info: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="alert-icon-svg" style="color:#a5b4fc; flex-shrink:0;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`
    };
    
    const iconContainer = document.createElement('span');
    iconContainer.className = 'alert-icon';
    iconContainer.innerHTML = svgIcons[type] || svgIcons.info;
    
    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'alert-body';
    bodyDiv.style.paddingLeft = '4px';
    bodyDiv.textContent = message;  // textContent is safe from XSS
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'alert-close';
    closeBtn.textContent = '✕';
    closeBtn.onclick = () => {
      alert.style.animation = 'slideOutRight 0.3s ease forwards';
      setTimeout(() => alert.remove(), 300);
    };
    
    alert.appendChild(iconContainer);
    alert.appendChild(bodyDiv);
    alert.appendChild(closeBtn);
    alertsWrapper.appendChild(alert);

    if (duration > 0) {
      setTimeout(() => {
        if (alert.parentElement) {
          alert.style.animation = 'slideOutRight 0.3s ease forwards';
          setTimeout(() => alert.remove(), 300);
        }
      }, duration);
    }
  }

  // Auto-dismiss existing flash alerts from Flask
  document.querySelectorAll('.alert').forEach((alert) => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        alert.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => alert.remove(), 300);
      });
    }
    setTimeout(() => {
      if (alert.parentElement) {
        alert.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => alert.remove(), 300);
      }
    }, 5000);
  });

  // ── File Helpers ───────────────────────────────────────────────
  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }

  function setSelectedFiles(files) {
    const isPremium = window.isPremium || false;
    const fileList = Array.from(files).filter(file => file.name.toLowerCase().endsWith('.pdf'));

    if (fileList.length === 0) {
      showAlert('Hanya file PDF yang didukung!', 'error');
      return false;
    }

    if (fileList.length > 1 && !isPremium) {
      showAlert('Kompresi massal (banyak file) hanya tersedia untuk member Premium! Silakan upgrade akun Anda.', 'warning');
      selectedFiles = [fileList[0]]; // fallback to first file
    } else {
      selectedFiles = fileList;
    }

    if (uploadFileInfo) {
      uploadFileInfo.classList.add('visible');
      if (selectedFiles.length === 1) {
        fileName.textContent = selectedFiles[0].name;
        fileSize.textContent = formatBytes(selectedFiles[0].size);
      } else {
        fileName.textContent = `${selectedFiles.length} File PDF Terpilih`;
        const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
        fileSize.textContent = `Total Ukuran: ${formatBytes(totalBytes)}`;
      }
    }

    if (compressBtn) compressBtn.disabled = false;

    // Update upload zone appearance
    if (uploadZone) {
      uploadZone.style.borderColor = 'rgba(99, 102, 241, 0.5)';
    }

    return true;
  }

  // ── Drag & Drop ────────────────────────────────────────────────
  if (uploadZone) {
    uploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
      uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadZone.classList.remove('drag-over');
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        setSelectedFiles(files);
      }
    });

    uploadZone.addEventListener('click', (e) => {
      if (e.target !== uploadBrowse) {
        fileInput && fileInput.click();
      }
    });
  }

  if (uploadBrowse) {
    uploadBrowse.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput && fileInput.click();
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        setSelectedFiles(fileInput.files);
      }
    });
  }

  // ── Advanced Settings Toggle & Synced Controls ─────────────────
  const advancedToggle = document.getElementById('advancedToggle');
  const advancedPanel  = document.getElementById('advancedPanel');

  // Shared update functions (visible to resetUpload via closure)
  let updateDPI = () => {};
  let updateQuality = () => {};

  if (advancedToggle && advancedPanel) {
    advancedToggle.addEventListener('click', () => {
      advancedToggle.classList.toggle('open');
      advancedPanel.classList.toggle('open');
    });

    const dpiSlider = document.getElementById('dpiSlider');
    const dpiInput = document.getElementById('dpiInput');
    const dpiValue = document.getElementById('dpiValue');
    const btnClearDpi = document.getElementById('btnClearDpi');

    const qualitySlider = document.getElementById('qualitySlider');
    const qualityInput = document.getElementById('qualityInput');
    const qualityValue = document.getElementById('qualityValue');
    const btnClearQuality = document.getElementById('btnClearQuality');

    // Function to update DPI
    updateDPI = function (val, fromSource) {
      if (val === '') {
        if (dpiValue) dpiValue.textContent = 'Default';
        if (dpiInput) dpiInput.value = '';
        if (dpiSlider) {
          dpiSlider.value = 150;
          dpiSlider.style.opacity = '0.5';
        }
      } else {
        const num = Math.max(72, Math.min(300, parseInt(val) || 150));
        if (dpiValue) dpiValue.textContent = num;
        if (dpiSlider) {
          dpiSlider.style.opacity = '1';
          if (fromSource !== 'slider') dpiSlider.value = num;
        }
        if (dpiInput && fromSource !== 'input') dpiInput.value = num;
      }
    };

    // Function to update Quality
    updateQuality = function (val, fromSource) {
      if (val === '') {
        if (qualityValue) qualityValue.textContent = 'Default';
        if (qualityInput) qualityInput.value = '';
        if (qualitySlider) {
          qualitySlider.value = 75;
          qualitySlider.style.opacity = '0.5';
        }
      } else {
        const num = Math.max(10, Math.min(100, parseInt(val) || 75));
        if (qualityValue) qualityValue.textContent = num;
        if (qualitySlider) {
          qualitySlider.style.opacity = '1';
          if (fromSource !== 'slider') qualitySlider.value = num;
        }
        if (qualityInput && fromSource !== 'input') qualityInput.value = num;
      }
    };

    // Initialize as Default (inputs are empty)
    updateDPI('', 'init');
    updateQuality('', 'init');

    // Slider inputs
    if (dpiSlider) {
      dpiSlider.addEventListener('input', (e) => {
        updateDPI(e.target.value, 'slider');
      });
    }
    if (qualitySlider) {
      qualitySlider.addEventListener('input', (e) => {
        updateQuality(e.target.value, 'slider');
      });
    }

    // Direct typed inputs
    if (dpiInput) {
      dpiInput.addEventListener('input', (e) => {
        updateDPI(e.target.value, 'input');
      });
      dpiInput.addEventListener('blur', () => {
        if (dpiInput.value !== '') {
          updateDPI(dpiInput.value, 'blur');
        }
      });
    }
    if (qualityInput) {
      qualityInput.addEventListener('input', (e) => {
        updateQuality(e.target.value, 'input');
      });
      qualityInput.addEventListener('blur', () => {
        if (qualityInput.value !== '') {
          updateQuality(qualityInput.value, 'blur');
        }
      });
    }

    // Clear triggers
    if (btnClearDpi) {
      btnClearDpi.addEventListener('click', () => {
        updateDPI('', 'clear');
      });
    }
    if (btnClearQuality) {
      btnClearQuality.addEventListener('click', () => {
        updateQuality('', 'clear');
      });
    }
  }

  // ── Compress Handler ───────────────────────────────────────────
  if (compressBtn) {
    compressBtn.addEventListener('click', handleCompress);
  }

  function animateProgress(targetPct, label, fill, statusEl) {
    return new Promise((resolve) => {
      let current = parseInt(fill.style.width) || 0;
      const step = () => {
        if (current < targetPct) {
          current = Math.min(current + 1, targetPct);
          fill.style.width = current + '%';
          if (statusEl) statusEl.textContent = label;
          requestAnimationFrame(step);
        } else {
          resolve();
        }
      };
      requestAnimationFrame(step);
    });
  }

  async function handleCompress() {
    if (selectedFiles.length === 0) {
      showAlert('Pilih file PDF terlebih dahulu.', 'warning');
      return;
    }

    // Get settings
    const preset   = document.querySelector('input[name="preset"]:checked')?.value || 'medium';
    const dpiInput = document.getElementById('dpiInput');
    const qualInput = document.getElementById('qualityInput');
    const dpi     = dpiInput?.value || '';
    const quality = qualInput?.value || '';

    // Show progress
    compressBtn.disabled = true;
    compressBtn.innerHTML = '<span class="spinner"></span> Memproses...';
    if (progressWrap) progressWrap.classList.add('visible');
    if (resultPanel) resultPanel.classList.remove('visible', 'error');
    if (progressFill) progressFill.style.width = '0%';

    if (selectedFiles.length === 1) {
      // ── Single File Compression ───────────────────────────────
      const file = selectedFiles[0];
      await animateProgress(25, 'Mengunggah file...', progressFill, progressStatus);

      const formData = new FormData();
      formData.append('pdf_file', file);
      formData.append('preset', preset);
      if (dpi) formData.append('dpi', dpi);
      if (quality) formData.append('quality', quality);

      try {
        await animateProgress(50, 'Menganalisis dokumen...', progressFill, progressStatus);

        const response = await fetch('/api/compress', {
          method: 'POST',
          body: formData
        });

        await animateProgress(80, 'Mengompresi PDF...', progressFill, progressStatus);

        let data;
        try {
          data = await response.json();
        } catch (jsonErr) {
          // Server returned non-JSON response (e.g. HTML error page)
          if (response.status === 413) {
            showError('File terlalu besar. Silakan gunakan file yang lebih kecil.');
          } else if (response.status === 429) {
            showError('Terlalu banyak permintaan. Silakan coba lagi nanti.');
          } else {
            showError(`Server error (${response.status}). Silakan coba lagi.`);
          }
          return;
        }

        await animateProgress(100, 'Selesai!', progressFill, progressStatus);

        if (data.success) {
          showResult(data);
        } else {
          showError(data.error || 'Terjadi kesalahan saat kompresi.');
        }
      } catch (err) {
        console.error('Compress error:', err);
        showError('Gagal menghubungkan ke server. Silakan periksa koneksi internet Anda dan coba lagi.');
      } finally {
        compressBtn.disabled = false;
        compressBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Kompres PDF';
      }
    } else {
      // ── Batch (Multiple) Files Compression ────────────────────
      const totalFiles = selectedFiles.length;
      const batchResults = [];
      let successCount = 0;

      for (let i = 0; i < totalFiles; i++) {
        const file = selectedFiles[i];
        const displayIndex = i + 1;
        const basePct = Math.round((i / totalFiles) * 100);
        
        const displayName = file.name.length > 20 ? file.name.substring(0, 20) + '...' : file.name;
        await animateProgress(basePct + 2, `[${displayIndex}/${totalFiles}] Mengompresi: ${displayName}`, progressFill, progressStatus);

        const formData = new FormData();
        formData.append('pdf_file', file);
        formData.append('preset', preset);
        if (dpi) formData.append('dpi', dpi);
        if (quality) formData.append('quality', quality);

        try {
          const response = await fetch('/api/compress', {
            method: 'POST',
            body: formData
          });
          const data = await response.json();

          if (data.success) {
            batchResults.push({
              name: file.name,
              original_size: data.original_size,
              compressed_size: data.compressed_size,
              reduction_percent: data.reduction_percent,
              download_url: data.download_url,
              success: true
            });
            successCount++;
          } else {
            batchResults.push({
              name: file.name,
              error: data.error || 'Gagal dikompresi.',
              success: false
            });
          }
        } catch {
          batchResults.push({
            name: file.name,
            error: 'Koneksi bermasalah.',
            success: false
          });
        }
        
        const endPct = Math.round(((i + 1) / totalFiles) * 100);
        await animateProgress(endPct, `[${displayIndex}/${totalFiles}] Selesai diproses`, progressFill, progressStatus);
      }

      // Display batch results
      compressBtn.disabled = false;
      compressBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Kompres PDF';

      showBatchResults(batchResults, successCount);
    }
  }

  function showResult(data) {
    if (!resultPanel) return;

    // SECURITY FIX: Sanitize and validate data before display
    const reduction = data.reduction_percent ? parseFloat(data.reduction_percent).toFixed(1) : '0.0';
    const origFmt  = formatBytes(parseInt(data.original_size) || 0);
    const compFmt  = formatBytes(parseInt(data.compressed_size) || 0);
    const elapsed  = data.elapsed_seconds ? parseFloat(data.elapsed_seconds).toFixed(1) : '-';
    
    // Sanitize download URL (ensure it's a relative path)
    const downloadUrl = (data.download_url || '').replace(/[<>"']/g, '');
    if (!downloadUrl.startsWith('/download/')) {
      showError('Invalid download URL');
      return;
    }

    resultPanel.classList.remove('error');
    resultPanel.classList.add('visible');
    resultPanel.innerHTML = `
      <div class="result-header">
        <div class="result-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:white;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
        </div>
        <div>
          <div class="result-title">Kompresi Berhasil!</div>
          <div class="result-subtitle">File PDF berhasil diperkecil ukurannya</div>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value text-secondary" style="font-size:1.1rem">${origFmt}</div>
          <div class="stat-label">Ukuran Awal</div>
        </div>
        <div class="stat-card">
          <div class="stat-value gradient-text" style="font-size:1.1rem">${compFmt}</div>
          <div class="stat-label">Ukuran Akhir</div>
        </div>
        <div class="stat-card">
          <div class="stat-value gradient-text-cyan" style="font-size:1.4rem">${reduction}%</div>
          <div class="stat-label">Penghematan</div>
        </div>
      </div>

      <div class="result-actions" style="display:flex; gap:10px; flex-wrap:wrap">
        <a href="${data.download_url}" class="btn btn-success" id="downloadBtn" download>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Download PDF
        </a>
        <button class="btn btn-secondary" onclick="resetUpload()">
          Kompres File Lain
        </button>
      </div>

      ${data.quota_tier !== 'Premium' ? `
      <div style="margin-top:16px; padding:12px 16px; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); border-radius:10px; font-size:0.82rem; color:#fcd34d;">
        Sisa kuota Anda: <strong>${data.quota_limit - data.quota_used} upload</strong> — 
        <a href="/subscription" style="color:#fbbf24; font-weight:600;">Upgrade ke Premium</a> untuk upload tanpa batas
      </div>` : ''}
    `;

    // Scroll to result
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showBatchResults(results, successCount) {
    if (!resultPanel) return;

    resultPanel.classList.remove('error');
    resultPanel.classList.add('visible');

    const totalFiles = results.length;
    const isSuccess = successCount > 0;
    
    // Calculate total savings
    let totalOrig = 0;
    let totalComp = 0;
    results.forEach(r => {
      if (r.success) {
        totalOrig += r.original_size;
        totalComp += r.compressed_size;
      }
    });
    const totalReduction = totalOrig > 0 ? (((totalOrig - totalComp) / totalOrig) * 100).toFixed(1) : '0.0';

    let html = `
      <div class="result-header">
        <div class="result-icon ${isSuccess ? '' : 'error-icon'}">
          ${isSuccess 
            ? '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:white;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
            : '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:white;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
          }
        </div>
        <div>
          <div class="result-title">${isSuccess ? 'Kompresi Massal Selesai!' : 'Kompresi Massal Gagal'}</div>
          <div class="result-subtitle">${successCount} dari ${totalFiles} file berhasil dikompresi</div>
        </div>
      </div>
    `;

    if (isSuccess) {
      html += `
        <div class="stats-grid mb-4">
          <div class="stat-card">
            <div class="stat-value text-secondary" style="font-size:1.1rem">${formatBytes(totalOrig)}</div>
            <div class="stat-label">Total Awal</div>
          </div>
          <div class="stat-card">
            <div class="stat-value gradient-text" style="font-size:1.1rem">${formatBytes(totalComp)}</div>
            <div class="stat-label">Total Akhir</div>
          </div>
          <div class="stat-card">
            <div class="stat-value gradient-text-cyan" style="font-size:1.4rem">${totalReduction}%</div>
            <div class="stat-label">Total Penghematan</div>
          </div>
        </div>
      `;
    }

    html += `
      <div class="card border shadow-sm p-3 mb-4 bg-white" style="border-radius:var(--radius-md);">
        <div class="fw-bold text-dark mb-2" style="font-size:0.9rem;">Daftar File Diproses:</div>
        <div class="d-flex flex-column gap-2" style="max-height:220px; overflow-y:auto; padding-right:4px;">
    `;

    results.forEach((r) => {
      const isOk = r.success;
      const fileIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
      
      html += `
        <div class="d-flex align-items-center justify-content-between p-2 rounded border border-light" style="background:#f8f9fa; font-size:0.82rem;">
          <div class="d-flex align-items-center gap-2 overflow-hidden" style="flex:1; padding-right:10px;">
            <span class="${isOk ? 'text-primary' : 'text-danger'}">${fileIcon}</span>
            <span class="fw-semibold text-dark text-truncate" title="${r.name}">${r.name}</span>
          </div>
          
          <div class="d-flex align-items-center gap-3">
            ${isOk 
              ? `<div class="text-end">
                   <span class="text-success fw-bold">-${parseFloat(r.reduction_percent).toFixed(1)}%</span>
                   <div class="text-secondary" style="font-size:0.72rem;">${formatBytes(r.compressed_size)}</div>
                 </div>
                 <a href="${r.download_url}" class="btn btn-sm btn-outline-success p-1 px-2 rounded-pill" download style="font-size:0.75rem; font-weight:600; display:inline-flex; align-items:center; gap:4px;">
                   <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                   Download
                 </a>`
              : `<span class="text-danger fw-semibold" title="${r.error}">${r.error.length > 15 ? r.error.substring(0, 15) + '...' : r.error}</span>`
            }
          </div>
        </div>
      `;
    });

    html += `
        </div>
      </div>
      
      <div class="result-actions" style="display:flex; gap:10px; flex-wrap:wrap">
        ${isSuccess 
          ? `<button class="btn btn-success" onclick="downloadAllBatch()">
               <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
               Download Semua File
             </button>`
          : ''
        }
        <button class="btn btn-secondary" onclick="resetUpload()">
          Kompres File Lain
        </button>
      </div>
    `;

    resultPanel.innerHTML = html;

    // Define temporary global function for batch download
    window.downloadAllBatch = () => {
      results.forEach(r => {
        if (r.success) {
          const a = document.createElement('a');
          a.href = r.download_url;
          a.download = r.name;
          document.body.appendChild(a);
          a.click();
          a.remove();
        }
      });
    };

    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showError(message) {
    if (!resultPanel) return;

    // SECURITY FIX: Use DOM methods to prevent XSS
    resultPanel.classList.add('visible', 'error');
    resultPanel.innerHTML = '';
    
    const header = document.createElement('div');
    header.className = 'result-header';
    
    const icon = document.createElement('div');
    icon.className = 'result-icon error-icon';
    icon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:white;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    
    const textDiv = document.createElement('div');
    
    const title = document.createElement('div');
    title.className = 'result-title';
    title.textContent = 'Kompresi Gagal';
    
    const subtitle = document.createElement('div');
    subtitle.className = 'result-subtitle';
    subtitle.textContent = message;  // Safe from XSS
    
    textDiv.appendChild(title);
    textDiv.appendChild(subtitle);
    header.appendChild(icon);
    header.appendChild(textDiv);
    
    const retryBtn = document.createElement('button');
    retryBtn.className = 'btn btn-secondary btn-sm';
    retryBtn.textContent = 'Coba Lagi';
    retryBtn.onclick = resetUpload;
    
    resultPanel.appendChild(header);
    resultPanel.appendChild(retryBtn);

    showAlert(message, 'error');
  }

  // ── Reset ──────────────────────────────────────────────────────
  window.resetUpload = function () {
    selectedFiles = [];
    if (fileInput) fileInput.value = '';
    if (uploadFileInfo) uploadFileInfo.classList.remove('visible');
    if (progressWrap) progressWrap.classList.remove('visible');
    if (resultPanel) { resultPanel.classList.remove('visible', 'error'); resultPanel.innerHTML = ''; }
    if (compressBtn) {
      compressBtn.disabled = true;
      compressBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Kompres PDF';
    }
    if (uploadZone) uploadZone.style.borderColor = '';
    if (progressFill) progressFill.style.width = '0%';
    
    // Reset advanced settings to default
    updateDPI('', 'reset');
    updateQuality('', 'reset');
  };

  if (resetBtn) {
    resetBtn.addEventListener('click', resetUpload);
  }

  // ── Navbar Mobile Toggle ───────────────────────────────────────
  const navToggle  = document.getElementById('navToggle');
  const mobileNav  = document.getElementById('mobileNav');

  if (navToggle && mobileNav) {
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('active');
      mobileNav.classList.toggle('open');
    });
  }

})();
