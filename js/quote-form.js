/**
 * NAGDEV PRODUCTS PRIVATE LIMITED - QUOTE & INQUIRY CONTROLLER
 * Handles RFQ modal, form validation, copy-to-clipboard, and toast alerts.
 */

class QuoteController {
  constructor() {
    this.modalBackdrop = document.getElementById('rfq-modal');
    this.modalForm = document.getElementById('modal-rfq-form');
    this.contactForm = document.getElementById('contact-rfq-form');
    this.toastContainer = document.getElementById('toast-container');
    this.init();
  }

  init() {
    this.bindModalTriggers();
    this.bindForms();
    this.bindCopyButtons();
  }

  bindModalTriggers() {
    // Open Modal
    document.querySelectorAll('[data-action="open-rfq"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const productName = btn.getAttribute('data-product-name') || '';
        this.openModal(productName);
      });
    });

    // Close Modal Button
    const closeBtn = document.getElementById('modal-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.closeModal());
    }

    // Click outside to close
    if (this.modalBackdrop) {
      this.modalBackdrop.addEventListener('click', (e) => {
        if (e.target === this.modalBackdrop) {
          this.closeModal();
        }
      });
    }

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.modalBackdrop && this.modalBackdrop.classList.contains('open')) {
        this.closeModal();
      }
    });
  }

  openModal(productName = '') {
    if (!this.modalBackdrop) return;
    
    if (productName) {
      const select = this.modalBackdrop.querySelector('select[name="product"]');
      if (select) {
        // Try to match option
        for (let i = 0; i < select.options.length; i++) {
          if (select.options[i].text.toLowerCase().includes(productName.toLowerCase()) || 
              select.options[i].value.toLowerCase().includes(productName.toLowerCase())) {
            select.selectedIndex = i;
            break;
          }
        }
      }
    }

    this.modalBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    document.body.classList.add('modal-open');
  }

  closeModal() {
    if (this.modalBackdrop) {
      this.modalBackdrop.classList.remove('open');
    }
    document.body.style.removeProperty('overflow');
    document.body.style.overflow = '';
    document.documentElement.style.removeProperty('overflow');
    document.documentElement.style.overflow = '';
    document.body.classList.remove('modal-open', 'no-scroll');
  }

  bindForms() {
    [this.modalForm, this.contactForm].forEach(form => {
      if (!form) return;
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleFormSubmit(form);
      });
    });
  }

  handleFormSubmit(form) {
    const formData = new FormData(form);
    const name = formData.get('name') || 'Valued Partner';
    const product = formData.get('product') || 'Castor Products';
    const country = formData.get('country') || 'International';

    // Disable button during simulated submission
    const submitBtn = form.querySelector('button[type="submit"]');
    const origText = submitBtn ? submitBtn.innerHTML : 'Send RFQ';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <svg class="btn-icon animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10" stroke-width="3" stroke-dasharray="32" stroke-linecap="round"></circle>
        </svg>
        Processing Export Request...
      `;
    }

    setTimeout(() => {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
      }

      form.reset();
      this.closeModal();

      this.showToast(
        `Quotation Request Received!`,
        `Thank you ${name}. Our export desk will dispatch technical specifications and FOB/CIF pricing for ${product} (${country}) within 24 business hours.`
      );
    }, 900);
  }

  bindCopyButtons() {
    // Copy Address Button
    const copyAddrBtn = document.getElementById('btn-copy-address');
    if (copyAddrBtn) {
      copyAddrBtn.addEventListener('click', () => {
        const address = "Survey No. 301 P-2, Jada-Kotarwada Rd, Village – Sardarpura, Post – Ravel, Taluka – Deodar, Dist. – Banaskantha – 385330, Gujarat, India";
        navigator.clipboard.writeText(address).then(() => {
          this.showToast("Address Copied", "Registered Gujarat factory & office address copied to clipboard.");
        }).catch(() => {
          this.showToast("Address Selected", address);
        });
      });
    }
  }

  showToast(title, message) {
    if (!this.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.innerHTML = `
      <div class="toast-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
      </div>
      <div class="toast-body">
        <div style="font-weight: 600; color: var(--gold-light); margin-bottom: 2px;">${title}</div>
        <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">${message}</div>
      </div>
    `;

    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }
}

// Global quick copy helper for spec tables
window.copyProductSpec = function(productId) {
  const prod = PRODUCTS_DATABASE.find(p => p.id === productId);
  if (!prod) return;

  let specText = `NAGDEV PRODUCTS PRIVATE LIMITED - SPECIFICATION SHEET\n`;
  specText += `Product: ${prod.name} (${prod.gradeType})\n`;
  specText += `Application: ${prod.description}\n`;
  specText += `------------------------------------------------------------\n`;
  
  if (prod.tableType === 'single') {
    prod.specs.forEach(s => {
      specText += `${s.parameter.padEnd(45)} | ${s.spec.padEnd(20)} | ${s.method}\n`;
    });
  } else if (prod.tableType === 'dual-spec') {
    specText += `${'Test Parameter'.padEnd(40)} | ${'Spec I'.padEnd(15)} | ${'Spec II'.padEnd(15)} | Test Method\n`;
    prod.specs.forEach(s => {
      specText += `${s.parameter.padEnd(40)} | ${s.spec1.padEnd(15)} | ${s.spec2.padEnd(15)} | ${s.method}\n`;
    });
  } else if (prod.tableType === 'multi-grade') {
    specText += prod.headers.join(' | ') + '\n';
    prod.specs.forEach(s => {
      specText += Object.values(s).join(' | ') + '\n';
    });
  }
  
  navigator.clipboard.writeText(specText).then(() => {
    if (window.quoteApp) {
      window.quoteApp.showToast("Spec Sheet Copied", `Full lab specification matrix for ${prod.shortName} copied to clipboard.`);
    } else {
      alert(`Copied specification for ${prod.name}`);
    }
  });
};
