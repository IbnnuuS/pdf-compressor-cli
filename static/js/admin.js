/* ═══════════════════════════════════════════════════════════════
   PDFKu — Admin JavaScript
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Sidebar Toggle (Mobile) ────────────────────────────────────
  const sidebarToggle  = document.getElementById('sidebarToggle');
  const adminSidebar   = document.getElementById('adminSidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  function openSidebar() {
    adminSidebar?.classList.add('open');
    sidebarOverlay?.classList.add('visible');
  }

  function closeSidebar() {
    adminSidebar?.classList.remove('open');
    sidebarOverlay?.classList.remove('visible');
  }

  sidebarToggle?.addEventListener('click', openSidebar);
  sidebarOverlay?.addEventListener('click', closeSidebar);

  // ── Navbar Mobile Toggle ───────────────────────────────────────
  const navToggle = document.getElementById('navToggle');
  const mobileNav = document.getElementById('mobileNav');

  navToggle?.addEventListener('click', () => {
    navToggle.classList.toggle('active');
    mobileNav?.classList.toggle('open');
  });

  // ── Flash alerts auto-dismiss ──────────────────────────────────
  document.querySelectorAll('.alert').forEach((alert) => {
    const closeBtn = alert.querySelector('.alert-close');
    closeBtn?.addEventListener('click', () => dismissAlert(alert));
    setTimeout(() => dismissAlert(alert), 5000);
  });

  function dismissAlert(alert) {
    if (!alert.parentElement) return;
    alert.style.animation = 'slideOutRight 0.3s ease forwards';
    setTimeout(() => alert.remove(), 300);
  }

  // ── Generic Toast ──────────────────────────────────────────────
  function showToast(message, type = 'info') {
    const wrapper = document.getElementById('alertsWrapper');
    if (!wrapper) return;

    // Premium design: High-quality SVG icons
    const el = document.createElement('div');
    el.className = `alert alert-${type}`;
    
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
    closeBtn.addEventListener('click', () => dismissAlert(el));
    
    el.appendChild(iconContainer);
    el.appendChild(bodyDiv);
    el.appendChild(closeBtn);
    wrapper.appendChild(el);
    setTimeout(() => dismissAlert(el), 5000);
  }

  // ── Confirm Modal ──────────────────────────────────────────────
  let confirmCallback = null;
  let cancelCallback = null;
  const confirmModal   = document.getElementById('confirmModal');
  const confirmMessage = document.getElementById('confirmMessage');
  const confirmOk      = document.getElementById('confirmOk');
  const confirmCancel  = document.getElementById('confirmCancel');

  function showConfirm(message, onConfirm, danger = true, onCancel = null) {
    if (!confirmModal) {
      if (window.confirm(message)) {
        onConfirm();
      } else {
        onCancel?.();
      }
      return;
    }
    if (confirmMessage) confirmMessage.textContent = message;
    if (confirmOk) {
      confirmOk.className = danger ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm';
    }
    confirmCallback = onConfirm;
    cancelCallback = onCancel;
    confirmModal.classList.add('open');
  }

  confirmOk?.addEventListener('click', () => {
    confirmModal.classList.remove('open');
    confirmCallback?.();
    confirmCallback = null;
    cancelCallback = null;
  });

  confirmCancel?.addEventListener('click', () => {
    confirmModal.classList.remove('open');
    cancelCallback?.();
    confirmCallback = null;
    cancelCallback = null;
  });

  // ── Helper CSRF Token ────────────────────────────────────────
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  // ── Toggle Premium ─────────────────────────────────────────────
  document.querySelectorAll('input[data-action="toggle-premium"]').forEach((toggle) => {
    toggle.addEventListener('change', async () => {
      const userId = toggle.dataset.userId;
      const originalState = !toggle.checked;

      try {
        toggle.disabled = true;
        const res = await fetch(`/admin/toggle-premium/${userId}`, { 
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
          }
        });
        const data = await res.json();

        if (data.success) {
          const newState = data.is_premium;
          toggle.checked = newState;

          // Update badge in the row
          const row = toggle.closest('tr');
          const premiumBadge = row?.querySelector('[data-badge="premium"]');
          if (premiumBadge) {
            premiumBadge.className = newState
              ? 'badge badge-warning-pill'
              : 'badge badge-neutral-pill';
            premiumBadge.textContent = newState ? '⭐ Premium' : 'Free';
          }

          // Update title of parent label
          const label = toggle.closest('label');
          if (label) {
            label.title = newState ? 'Cabut Premium' : 'Aktifkan Premium';
          }

          showToast(data.message, 'success');
        } else {
          toggle.checked = originalState; // revert
          showToast(data.error || 'Gagal mengubah status premium.', 'error');
        }
      } catch {
        toggle.checked = originalState; // revert
        showToast('Gagal terhubung ke server. Periksa koneksi internet Anda.', 'error');
      } finally {
        toggle.disabled = false;
      }
    });
  });

  // ── Toggle Admin ───────────────────────────────────────────────
  document.querySelectorAll('input[data-action="toggle-admin"]').forEach((toggle) => {
    toggle.addEventListener('change', async () => {
      const userId = toggle.dataset.userId;
      const originalState = !toggle.checked;
      const wantToBeAdmin = toggle.checked;

      showConfirm(
        wantToBeAdmin
          ? 'Apakah Anda yakin ingin menjadikan user ini sebagai Admin?'
          : 'Apakah Anda yakin ingin mencabut hak Admin dari user ini?',
        async () => {
          try {
            toggle.disabled = true;
            const res = await fetch(`/admin/toggle-admin/${userId}`, { 
              method: 'POST',
              headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
              }
            });
            const data = await res.json();

            if (data.success) {
              const newState = data.is_admin;
              toggle.checked = newState;

              const row = toggle.closest('tr');
              const adminBadge = row?.querySelector('[data-badge="admin"]');
              if (adminBadge) {
                adminBadge.style.display = newState ? 'inline-flex' : 'none';
              }

              // Update title of parent label
              const label = toggle.closest('label');
              if (label) {
                label.title = newState ? 'Cabut Admin' : 'Jadikan Admin';
              }

              showToast(data.message, 'success');
            } else {
              toggle.checked = originalState; // revert
              showToast(data.error || 'Gagal mengubah status admin.', 'error');
            }
          } catch {
            toggle.checked = originalState; // revert
            showToast('Gagal terhubung ke server. Periksa koneksi internet Anda.', 'error');
          } finally {
            toggle.disabled = false;
          }
        },
        false, // Not danger
        () => {
          toggle.checked = originalState; // revert if cancelled
        }
      );
    });
  });

  // ── Delete User ────────────────────────────────────────────────
  document.querySelectorAll('[data-action="delete-user"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const userId   = btn.dataset.userId;
      const username = btn.dataset.username;

      showConfirm(
        `Hapus user "${username}" secara permanen? Semua log kompresi juga akan terhapus.`,
        async () => {
          try {
            btn.disabled = true;
            const res = await fetch(`/admin/delete-user/${userId}`, { 
              method: 'POST',
              headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
              }
            });
            const data = await res.json();

            if (data.success) {
              const row = btn.closest('tr');
              row?.style.setProperty('transition', 'opacity 0.4s');
              if (row) row.style.opacity = '0';
              setTimeout(() => row?.remove(), 400);
              showToast(data.message, 'success');
            } else {
              showToast(data.error || 'Gagal menghapus user.', 'error');
            }
          } catch {
            showToast('Gagal terhubung ke server. Periksa koneksi internet Anda.', 'error');
          } finally {
            btn.disabled = false;
          }
        }
      );
    });
  });

  // ── Chart.js Dashboard ─────────────────────────────────────────
  const chartCanvas = document.getElementById('uploadChart');
  if (chartCanvas && window.Chart) {
    const labels = JSON.parse(chartCanvas.dataset.labels || '[]');
    const values = JSON.parse(chartCanvas.dataset.values || '[]');

    new window.Chart(chartCanvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Upload Harian',
          data: values,
          borderColor: '#0d6efd',
          backgroundColor: 'rgba(13, 110, 253, 0.05)',
          borderWidth: 2,
          pointBackgroundColor: '#0d6efd',
          pointBorderColor: '#0d6efd',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#212529',
            titleColor: '#ffffff',
            bodyColor: '#dee2e6',
            borderColor: 'rgba(0,0,0,0.05)',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => ` ${ctx.parsed.y} upload`
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(0, 0, 0, 0.04)' },
            ticks: { color: '#495057', font: { size: 11 } }
          },
          y: {
            grid: { color: 'rgba(0, 0, 0, 0.04)' },
            ticks: {
              color: '#495057',
              font: { size: 11 },
              stepSize: 1,
              precision: 0
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ── Chart.js Revenue Dashboard ─────────────────────────────────
  const revCanvas = document.getElementById('revenueChart');
  if (revCanvas && window.Chart) {
    const labels = JSON.parse(revCanvas.dataset.labels || '[]');
    const values = JSON.parse(revCanvas.dataset.values || '[]');

    new window.Chart(revCanvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Pendapatan',
          data: values,
          borderColor: '#198754',
          backgroundColor: 'rgba(25, 135, 84, 0.05)',
          borderWidth: 2.5,
          pointBackgroundColor: '#198754',
          pointBorderColor: '#198754',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#212529',
            titleColor: '#ffffff',
            bodyColor: '#dee2e6',
            borderColor: 'rgba(0,0,0,0.05)',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => ` Rp ${ctx.parsed.y.toLocaleString('id-ID')}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(0, 0, 0, 0.04)' },
            ticks: { color: '#495057', font: { size: 11 } }
          },
          y: {
            grid: { color: 'rgba(0, 0, 0, 0.04)' },
            ticks: {
              color: '#495057',
              font: { size: 11 },
              callback: (val) => `Rp ${val.toLocaleString('id-ID')}`
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ── Subscription Page: Midtrans ────────────────────────────────
  const subscribeBtn = document.getElementById('subscribeMidtransBtn');
  const subscribeMockBtn = document.getElementById('subscribeMockBtn');

  if (subscribeBtn) {
    subscribeBtn.addEventListener('click', async () => {
      subscribeBtn.disabled = true;
      subscribeBtn.innerHTML = '<span class="spinner"></span> Memproses...';

      try {
        const res = await fetch('/api/subscribe/midtrans/token', { 
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
          }
        });
        const data = await res.json();

        if (data.success && data.token) {
          window.snap.pay(data.token, {
            onSuccess: async () => {
              await fetch('/api/subscribe/midtrans/success', { method: 'POST' });
              showToast('Pembayaran berhasil! Akun Anda telah ditingkatkan ke Premium 🎉', 'success');
              setTimeout(() => location.reload(), 2000);
            },
            onPending: () => {
              showToast('Menunggu pembayaran. Akun akan diupgrade setelah konfirmasi.', 'warning');
            },
            onError: (result) => {
              showToast('Pembayaran gagal: ' + (result.status_message || 'Error tidak diketahui'), 'error');
            },
            onClose: () => {
              showToast('Pembayaran dibatalkan.', 'info');
            }
          });
        } else {
          showToast(data.error || 'Gagal membuat token pembayaran.', 'error');
        }
      } catch {
        showToast('Koneksi bermasalah. Periksa jaringan internet Anda dan coba lagi.', 'error');
      } finally {
        subscribeBtn.disabled = false;
        subscribeBtn.innerHTML = 'Tingkatkan Sekarang';
      }
    });
  }

  if (subscribeMockBtn) {
    subscribeMockBtn.addEventListener('click', async () => {
      subscribeMockBtn.disabled = true;
      subscribeMockBtn.innerHTML = '<span class="spinner"></span> Memproses...';

      try {
        const res = await fetch('/api/subscribe/mock', { 
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
          }
        });
        const data = await res.json();

        if (data.success) {
          showToast('Akun Anda berhasil ditingkatkan ke Premium! 🎉', 'success');
          setTimeout(() => location.reload(), 2000);
        } else {
          showToast(data.error || 'Gagal upgrade akun.', 'error');
        }
      } catch {
        showToast('Gagal terhubung ke server. Periksa koneksi internet Anda.', 'error');
      } finally {
        subscribeMockBtn.disabled = false;
        subscribeMockBtn.innerHTML = '🧪 Demo (Sandbox)';
      }
    });
  }

  function changePerPage(value) {
    const url = new URL(window.location.href);
    url.searchParams.set('per_page', value);
    url.searchParams.set('page', 1);
    window.location.href = url.toString();
  }

  // ── Global showToast export ────────────────────────────────────
  window.showToast = showToast;
  window.changePerPage = changePerPage;

})();
