/**
 * NAGDEV PRODUCTS PRIVATE LIMITED - SPECIFICATION POPUP WINDOW CONTROLLER
 * Manages the modal popup for viewing, copying, and printing product specifications.
 */

class SpecModalController {
  constructor() {
    this.modalBackdrop = document.getElementById('spec-modal');
    this.modalTitle = document.getElementById('spec-modal-title');
    this.modalSubtitle = document.getElementById('spec-modal-subtitle');
    this.modalBadge = document.getElementById('spec-modal-badge');
    this.modalTableWrap = document.getElementById('spec-modal-table-wrap');
    this.modalCopyBtn = document.getElementById('spec-modal-copy-btn');
    this.modalPrintBtn = document.getElementById('spec-modal-print-btn');
    this.modalInquireBtn = document.getElementById('spec-modal-inquire-btn');
    this.closeBtn = document.getElementById('spec-modal-close-btn');

    this.currentProductId = null;
    this.init();
  }

  init() {
    this.bindEvents();
  }

  bindEvents() {
    // Close button
    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => this.close());
    }

    // Backdrop click
    if (this.modalBackdrop) {
      this.modalBackdrop.addEventListener('click', (e) => {
        if (e.target === this.modalBackdrop) this.close();
      });
    }

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen()) this.close();
    });

    // Copy Specs Button
    if (this.modalCopyBtn) {
      this.modalCopyBtn.addEventListener('click', () => {
        if (this.currentProductId) {
          window.copyProductSpec(this.currentProductId);
        }
      });
    }

    // Print / Save TDS Button
    if (this.modalPrintBtn) {
      this.modalPrintBtn.addEventListener('click', () => {
        if (this.currentProductId && typeof downloadProductTDS === 'function') {
          downloadProductTDS(this.currentProductId);
        } else {
          window.print();
        }
      });
    }

    // Inquire Button inside Spec Modal
    if (this.modalInquireBtn) {
      this.modalInquireBtn.addEventListener('click', () => {
        const prod = PRODUCTS_DATABASE.find(p => p.id === this.currentProductId);
        const name = prod ? prod.name : '';
        this.close();
        if (window.quoteApp) {
          window.quoteApp.openModal(name);
        } else {
          window.location.href = `contact.html?product=${encodeURIComponent(name)}`;
        }
      });
    }

    // Delegate "View Specification" button clicks across entire document
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="view-spec"]');
      if (btn) {
        e.preventDefault();
        const productId = btn.getAttribute('data-product-id');
        if (productId) {
          this.open(productId);
        }
      }
    });
  }

  isOpen() {
    return this.modalBackdrop && this.modalBackdrop.classList.contains('open');
  }

  open(productId) {
    const product = PRODUCTS_DATABASE.find(p => p.id === productId);
    if (!product || !this.modalBackdrop) return;

    this.currentProductId = productId;

    // Set title and details
    if (this.modalTitle) this.modalTitle.textContent = product.name;
    if (this.modalSubtitle) this.modalSubtitle.textContent = product.description;
    
    if (this.modalBadge) {
      this.modalBadge.textContent = product.gradeType;
      this.modalBadge.className = `badge ${product.badgeClass}`;
    }

    // Build Table HTML
    if (this.modalTableWrap) {
      this.modalTableWrap.innerHTML = this.buildTableHTML(product);
    }

    this.modalBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    document.body.classList.add('modal-open');
  }

  close() {
    if (this.modalBackdrop) {
      this.modalBackdrop.classList.remove('open');
    }
    this.currentProductId = null;
    
    // Explicitly restore background scrolling on both body and html
    document.body.style.removeProperty('overflow');
    document.body.style.overflow = '';
    document.documentElement.style.removeProperty('overflow');
    document.documentElement.style.overflow = '';
    document.body.classList.remove('modal-open', 'no-scroll');
  }

  buildTableHTML(product) {
    if (!product || !product.specs || !product.specs.length) {
      return '<p style="padding:20px;text-align:center;color:#666;">Detailed specification parameters available upon technical inquiry.</p>';
    }

    // Modern Array of Arrays format (Standard across PRODUCTS_DATABASE)
    if (Array.isArray(product.specs[0])) {
      const headers = product.headers || ["Sr No", "Test Parameter", "Specification"];
      const rows = product.specs.map((row, rIdx) => `
        <tr style="background:${rIdx % 2 === 0 ? 'rgba(250,247,242,0.65)' : 'rgba(255,255,255,0.7)'};">
          ${row.map((col, cIdx) => `
            <td class="${cIdx === 0 ? 'text-center font-bold' : (cIdx === 1 ? 'spec-param-name' : 'spec-val')}" style="${cIdx === 0 ? 'text-align:center;font-weight:700;width:55px;' : ''}">
              ${cIdx === row.length - 1 && (col.startsWith('AOCS') || col.startsWith('ASTM') || col.startsWith('IS') || col.includes('Method') || col.includes('Oven') || col.includes('Bomb') || col.includes('Kjeldahl') || col.includes('Flame')) ? `<span class="modal-method-tag">${col}</span>` : col}
            </td>
          `).join('')}
        </tr>
      `).join('');

      return `
        <table class="modal-spec-table" style="width:100%;border-collapse:collapse;">
          <thead>
            <tr>
              ${headers.map(h => `<th>${h}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    }

    if (product.tableType === 'single') {
      const rows = product.specs.map(row => `
        <tr>
          <td class="spec-param-name">${row.parameter}</td>
          <td class="spec-val">${row.spec}</td>
          <td><span class="modal-method-tag">${row.method}</span></td>
        </tr>
      `).join('');

      return `
        <table class="modal-spec-table">
          <thead>
            <tr>
              <th>Test Parameter</th>
              <th>Specification</th>
              <th>Test Method</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    }

    if (product.tableType === 'dual-spec') {
      const headers = product.headers || ["Test Parameter", "Spec I", "Spec II", "Test Method"];
      const rows = product.specs.map(row => `
        <tr>
          <td class="spec-param-name">${row.parameter}</td>
          <td class="spec-val">${row.spec1 || '—'}</td>
          <td class="spec-val">${row.spec2 || '—'}</td>
          <td><span class="modal-method-tag">${row.method}</span></td>
        </tr>
      `).join('');

      return `
        <table class="modal-spec-table">
          <thead>
            <tr>
              <th>${headers[0]}</th>
              <th>${headers[1]}</th>
              <th>${headers[2]}</th>
              <th>${headers[3]}</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    }

    if (product.tableType === 'multi-grade') {
      const headers = product.headers;
      let rows = '';

      if (product.id === 'hydrogenated-castor-oil') {
        rows = product.specs.map(row => `
          <tr>
            <td class="spec-param-name">${row.parameter}</td>
            <td class="spec-val">${row.standard}</td>
            <td class="spec-val">${row.special}</td>
            <td class="spec-val">${row.supreme}</td>
            <td class="spec-val">${row.mp80}</td>
            <td><span class="modal-method-tag">${row.method}</span></td>
          </tr>
        `).join('');
      } else if (product.id === '12-hydroxy-stearic-acid') {
        rows = product.specs.map(row => `
          <tr>
            <td class="spec-param-name">${row.parameter}</td>
            <td class="spec-val">${row.standard}</td>
            <td class="spec-val">${row.special}</td>
            <td class="spec-val">${row.supreme}</td>
            <td class="spec-val">${row.bleach}</td>
            <td><span class="modal-method-tag">${row.method}</span></td>
          </tr>
        `).join('');
      }

      return `
        <table class="modal-spec-table">
          <thead>
            <tr>
              ${headers.map(h => `<th>${h}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    }

    return '';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.specModal = new SpecModalController();
});
