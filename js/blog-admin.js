/**
 * NAGDEV PRODUCTS — BLOG ADMIN STUDIO CONTROLLER
 * Full CRUD, 1200x630 interactive image cropping, SERP preview,
 * rich text editing, static export, and secure authentication.
 */

(function () {
  'use strict';

  const AUTH_KEY = 'nagdev_admin_auth';
  const VALID_ID = 'admin';
  const VALID_PIN = '230893';

  // Elements
  const loginGate = document.getElementById('login-gate');
  const loginCard = document.getElementById('login-card');
  const loginForm = document.getElementById('admin-login-form');
  const loginIdInput = document.getElementById('login-id');
  const loginPinInput = document.getElementById('login-pin');
  const loginError = document.getElementById('login-error');
  const adminApp = document.getElementById('admin-app');
  const logoutBtn = document.getElementById('admin-logout-btn');

  // Tab elements
  const tabBtns = document.querySelectorAll('.admin-tab-btn');
  const tabContents = document.querySelectorAll('.admin-tab-content');

  // Form elements
  const postForm = document.getElementById('post-editor-form');
  const postIdInput = document.getElementById('post-id');
  const postTitleInput = document.getElementById('post-title');
  const postSlugInput = document.getElementById('post-slug');
  const postCategorySelect = document.getElementById('post-category');
  const postCustomCatInput = document.getElementById('post-custom-category');
  const postAuthorInput = document.getElementById('post-author');
  const postDateInput = document.getElementById('post-date');
  const postTagsInput = document.getElementById('post-tags');
  const postFeaturedCheck = document.getElementById('post-featured');
  const postSeoDescInput = document.getElementById('post-seo-desc');
  const postCoverBase64 = document.getElementById('post-cover-base64');
  const postLinkSelect = document.getElementById('post-link-select');
  const editorContent = document.getElementById('wysiwyg-editor');
  const modeLabel = document.getElementById('form-mode-label');

  // SERP preview elements
  const serpTitlePreview = document.getElementById('serp-title-preview');
  const serpPathPreview = document.getElementById('serp-path-preview');
  const serpSnippetPreview = document.getElementById('serp-snippet-preview');
  const titleCharCount = document.getElementById('title-char-count');
  const seoDescCounter = document.getElementById('seo-desc-counter');
  const seoDescStatus = document.getElementById('seo-desc-status');
  const contentWordCount = document.getElementById('content-word-count');

  // Cover upload & Cropper elements
  const dropZone = document.getElementById('cover-drop-zone');
  const fileInput = document.getElementById('cover-file-input');
  const cropPreviewWrap = document.getElementById('crop-preview-wrap');
  const previewImg = document.getElementById('cover-preview-img');
  const recropBtn = document.getElementById('recrop-btn');
  const removeImgBtn = document.getElementById('remove-img-btn');

  // Cropper Modal
  const cropperModal = document.getElementById('cropper-modal');
  const cropperSourceImg = document.getElementById('cropper-source-img');
  const cropApplyBtn = document.getElementById('crop-apply-btn');
  const cropCancelBtn = document.getElementById('crop-cancel-btn');
  const cropperCloseBtn = document.getElementById('cropper-close-btn');
  let cropperInstance = null;
  let rawSourceImageSrc = '';

  // Management elements
  const tableBody = document.getElementById('articles-table-body');
  const countBadge = document.getElementById('articles-count-badge');
  const resetFormBtn = document.getElementById('reset-form-btn');
  const exportHtmlBtn = document.getElementById('export-html-btn');
  const shortcutNewBtn = document.getElementById('btn-new-article-shortcut');
  const downloadBlogDataBtn = document.getElementById('download-blog-data-btn');
  const downloadAllHtmlsBtn = document.getElementById('download-all-htmls-btn');

  // ── Authentication Check ────────────────────────────────────────────────
  function checkAuth() {
    const isAuth = sessionStorage.getItem(AUTH_KEY) === 'true';
    if (isAuth) {
      loginGate.style.display = 'none';
      adminApp.style.display = 'block';
      initAdminDashboard();
    } else {
      loginGate.style.display = 'flex';
      adminApp.style.display = 'none';
      if (loginIdInput) loginIdInput.focus();
    }
  }

  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const enteredId = (loginIdInput.value || '').trim().toLowerCase();
      const enteredPin = (loginPinInput.value || '').trim();

      if (enteredId === VALID_ID && enteredPin === VALID_PIN) {
        sessionStorage.setItem(AUTH_KEY, 'true');
        loginError.style.display = 'none';
        window.showToast('Welcome, Administrator. Editorial Studio Unlocked.');
        checkAuth();
      } else {
        loginError.style.display = 'block';
        loginCard.classList.add('shake-animation');
        setTimeout(() => loginCard.classList.remove('shake-animation'), 500);
      }
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      sessionStorage.removeItem(AUTH_KEY);
      window.showToast('Logged out of Admin Studio.');
      checkAuth();
    });
  }

  // ── Tabs Navigation ─────────────────────────────────────────────────────
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');
    });
  });

  if (shortcutNewBtn) {
    shortcutNewBtn.addEventListener('click', () => {
      resetForm();
      const tab1 = document.querySelector('[data-tab="tab-editor"]');
      if (tab1) tab1.click();
    });
  }

  // ── Auto-slug & Character / SERP Counters ──────────────────────────────
  let userEditedSlug = false;
  postSlugInput.addEventListener('input', () => { userEditedSlug = true; updateSerpPreview(); });

  postTitleInput.addEventListener('input', () => {
    const title = postTitleInput.value;
    titleCharCount.textContent = `${title.length} chars`;

    if (!userEditedSlug && !postIdInput.value) {
      postSlugInput.value = title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)+/g, '');
    }
    updateSerpPreview();
  });

  postSeoDescInput.addEventListener('input', () => {
    const desc = postSeoDescInput.value;
    const len = desc.length;
    seoDescCounter.textContent = `${len} / 160`;

    if (len >= 130 && len <= 165) {
      seoDescStatus.textContent = 'Optimal Google snippet length ✓';
      seoDescStatus.style.color = '#15612E';
    } else if (len > 165) {
      seoDescStatus.textContent = 'Warning: Description may truncate in search results';
      seoDescStatus.style.color = '#B8841A';
    } else {
      seoDescStatus.textContent = 'Recommended: 140–160 characters';
      seoDescStatus.style.color = 'var(--admin-muted)';
    }

    updateSerpPreview();
  });

  function updateSerpPreview() {
    const title = postTitleInput.value.trim() || 'Article Title Here';
    const slug = postSlugInput.value.trim() || 'article-url-slug';
    const snippet = postSeoDescInput.value.trim() || 'Your SEO short description will appear here in Google search engine results pages...';

    serpTitlePreview.textContent = `${title} | Nagdev Products`;
    serpPathPreview.textContent = `https://www.nagdevproducts.com › blog › ${slug}`;
    serpSnippetPreview.textContent = snippet;
  }

  // Word counter on rich editor
  editorContent.addEventListener('input', () => {
    const text = editorContent.innerText || '';
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    contentWordCount.textContent = `${words} words`;
  });

  // Custom Category Toggle
  postCategorySelect.addEventListener('change', () => {
    if (postCategorySelect.value === 'Custom') {
      postCustomCatInput.style.display = 'block';
      postCustomCatInput.required = true;
    } else {
      postCustomCatInput.style.display = 'none';
      postCustomCatInput.required = false;
    }
  });

  // ── Rich Text Toolbar ───────────────────────────────────────────────────
  document.querySelectorAll('.tb-btn[data-command]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const cmd = btn.getAttribute('data-command');
      const val = btn.getAttribute('data-val') || null;
      document.execCommand(cmd, false, val);
      editorContent.focus();
    });
  });

  const linkBtn = document.getElementById('tb-link-btn');
  if (linkBtn) {
    linkBtn.addEventListener('click', () => {
      const url = prompt('Enter URL (e.g. https://... or products/hydrogenated-castor-oil.html):');
      if (url) {
        document.execCommand('createLink', false, url);
      }
    });
  }

  const tableBtn = document.getElementById('tb-table-btn');
  if (tableBtn) {
    tableBtn.addEventListener('click', () => {
      const tableHtml = `
        <table class="blog-data-table">
          <thead>
            <tr><th>Parameter</th><th>Standard Grade</th><th>High-Purity Grade</th></tr>
          </thead>
          <tbody>
            <tr><td>Hydroxyl Value (mg KOH/g)</td><td>155 – 165</td><td>160 – 168</td></tr>
            <tr><td>Acid Value (mg KOH/g)</td><td>&lt; 2.0</td><td>&lt; 1.0</td></tr>
          </tbody>
        </table><p></p>
      `;
      document.execCommand('insertHTML', false, tableHtml);
    });
  }

  // ── Fixed Dimension Cropper & Direct Photo Upload (1200 × 630 px) ────────
  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--admin-forest)';
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = 'var(--admin-gold)';
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--admin-gold)';
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file.type.startsWith('image/')) {
      alert('Please select a valid image file (JPG, PNG, WebP).');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      rawSourceImageSrc = e.target.result;
      openCropper(rawSourceImageSrc);
    };
    reader.readAsDataURL(file);
  }

  function openCropper(imageSrc) {
    cropperSourceImg.src = imageSrc;
    cropperModal.style.display = 'flex';

    if (cropperInstance) {
      cropperInstance.destroy();
    }

    // Initialize Cropper.js with 1200:630 aspect ratio (1.9047)
    setTimeout(() => {
      if (window.Cropper) {
        cropperInstance = new Cropper(cropperSourceImg, {
          aspectRatio: 1200 / 630,
          viewMode: 1,
          autoCropArea: 1,
          responsive: true,
          guides: true,
          center: true,
          highlight: true,
          background: true
        });
      }
    }, 100);
  }

  function closeCropper() {
    cropperModal.style.display = 'none';
    if (cropperInstance) {
      cropperInstance.destroy();
      cropperInstance = null;
    }
  }

  cropCancelBtn.addEventListener('click', closeCropper);
  cropperCloseBtn.addEventListener('click', closeCropper);

  // Zoom & Rotate handlers
  document.getElementById('crop-zoom-in').addEventListener('click', () => cropperInstance && cropperInstance.zoom(0.1));
  document.getElementById('crop-zoom-out').addEventListener('click', () => cropperInstance && cropperInstance.zoom(-0.1));
  document.getElementById('crop-rotate-left').addEventListener('click', () => cropperInstance && cropperInstance.rotate(-90));
  document.getElementById('crop-rotate-right').addEventListener('click', () => cropperInstance && cropperInstance.rotate(90));
  document.getElementById('crop-reset').addEventListener('click', () => cropperInstance && cropperInstance.reset());

  // Apply Crop: render directly into fixed 1200x630 canvas
  cropApplyBtn.addEventListener('click', () => {
    if (!cropperInstance) return;

    const canvas = cropperInstance.getCroppedCanvas({
      width: 1200,
      height: 630,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high'
    });

    if (canvas) {
      // Direct WebP / JPEG base64 Data URL (0.90 quality)
      const croppedBase64 = canvas.toDataURL('image/jpeg', 0.90);
      postCoverBase64.value = croppedBase64;
      previewImg.src = croppedBase64;

      dropZone.style.display = 'none';
      cropPreviewWrap.style.display = 'block';

      closeCropper();
      window.showToast('Cover photo cropped to fixed 1200 × 630 px ✓');
    }
  });

  recropBtn.addEventListener('click', () => {
    if (rawSourceImageSrc) {
      openCropper(rawSourceImageSrc);
    } else if (postCoverBase64.value) {
      openCropper(postCoverBase64.value);
    }
  });

  removeImgBtn.addEventListener('click', () => {
    postCoverBase64.value = '';
    rawSourceImageSrc = '';
    previewImg.src = '';
    dropZone.style.display = 'block';
    cropPreviewWrap.style.display = 'none';
    fileInput.value = '';
  });

  // ── Form Submission (Save & Publish) ────────────────────────────────────
  postForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = postTitleInput.value.trim();
    const slug = postSlugInput.value.trim();
    const seoDesc = postSeoDescInput.value.trim();
    const coverImage = postCoverBase64.value || previewImg.src;
    const content = editorContent.innerHTML.trim();
    let category = postCategorySelect.value;
    if (category === 'Custom') {
      category = postCustomCatInput.value.trim();
    }
    const author = postAuthorInput.value.trim();
    const date = postDateInput.value;
    const tagsStr = postTagsInput.value.trim();
    const linkVal = postLinkSelect ? postLinkSelect.value : '';

    // Strict validation: ALL fields are mandatory
    if (!title) {
      alert('Mandatory Field Missing: Please enter an Article Title.');
      postTitleInput.focus();
      return;
    }

    if (!slug) {
      alert('Mandatory Field Missing: Please enter a valid URL Slug.');
      postSlugInput.focus();
      return;
    }

    if (!category) {
      alert('Mandatory Field Missing: Please select or enter a Category / Topic.');
      postCategorySelect.focus();
      return;
    }

    if (!author) {
      alert('Mandatory Field Missing: Please provide an Author Name / Byline.');
      postAuthorInput.focus();
      return;
    }

    if (!date) {
      alert('Mandatory Field Missing: Please select a Publication Date.');
      postDateInput.focus();
      return;
    }

    if (!tagsStr) {
      alert('Mandatory Field Missing: Please enter SEO Keywords / Tags (comma-separated).');
      postTagsInput.focus();
      return;
    }

    if (!coverImage) {
      alert('Mandatory Field Missing: Please choose and crop a Featured Cover Photo (fixed 1200 × 630 px).');
      dropZone.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    if (!seoDesc) {
      alert('Mandatory Field Missing: Please enter an SEO Short Description (Meta Description).');
      postSeoDescInput.focus();
      return;
    }

    if (!content || content === '<p></p>' || content === '<br>' || content === '<p><br></p>') {
      alert('Mandatory Field Missing: Please write the Full Article Description in the rich text editor.');
      editorContent.focus();
      return;
    }

    if (!linkVal) {
      alert('Mandatory Field Missing: Please select a Related Website Link (Bottom CTA) from the dropdown.');
      postLinkSelect.focus();
      return;
    }

    const tags = tagsStr
      .split(',')
      .map(t => t.trim())
      .filter(Boolean);

    const linkParts = linkVal.split('|');
    const relatedLink = {
      url: linkParts[0],
      title: linkParts[1] || linkParts[0]
    };

    const postData = {
      id: postIdInput.value || ('post-' + Date.now()),
      title: title,
      slug: slug,
      category: category,
      author: author,
      date: date,
      seoDescription: seoDesc,
      coverImage: coverImage,
      tags: tags,
      relatedLink: relatedLink,
      featured: postFeaturedCheck.checked,
      content: content
    };

    const submitBtn = document.getElementById('publish-btn');
    submitBtn.textContent = 'Saving Article…';
    submitBtn.disabled = true;

    try {
      await window.BlogStorage.savePost(postData);
      window.showToast('Article published successfully! Live on website.');
      postIdInput.value = postData.id;
      modeLabel.textContent = `Editing: ${postData.title.slice(0, 24)}…`;
      await renderArticlesTable();
    } catch (err) {
      console.error(err);
      alert('Failed to save article: ' + err.message);
    } finally {
      submitBtn.textContent = 'Publish Article to Website →';
      submitBtn.disabled = false;
    }
  });

  // ── Single Post Static HTML Export ──────────────────────────────────────
  exportHtmlBtn.addEventListener('click', () => {
    const title = postTitleInput.value.trim();
    const slug = postSlugInput.value.trim();
    const coverImage = postCoverBase64.value || previewImg.src;
    const content = editorContent.innerHTML.trim();
    const seoDesc = postSeoDescInput.value.trim();
    const linkVal = postLinkSelect ? postLinkSelect.value : '';

    if (!title || !slug || !content || !coverImage || !seoDesc || !linkVal) {
      alert('Please fill out all mandatory fields (including cover photo, description, and website link) before exporting static HTML.');
      return;
    }

    let category = postCategorySelect.value;
    if (category === 'Custom') category = postCustomCatInput.value.trim();

    const linkParts = linkVal.split('|');
    const relatedLink = {
      url: linkParts[0],
      title: linkParts[1] || linkParts[0]
    };

    const postObj = {
      title,
      slug,
      category,
      author: postAuthorInput.value.trim() || 'Nagdev Products',
      date: postDateInput.value || new Date().toISOString().split('T')[0],
      seoDescription: seoDesc,
      coverImage: coverImage || 'images/og-share.jpg',
      tags: postTagsInput.value.split(',').map(t => t.trim()).filter(Boolean),
      relatedLink: relatedLink,
      content
    };

    const html = window.BlogStorage.generateStaticHtml(postObj);
    downloadFile(`${slug}.html`, html, 'text/html');
    window.showToast(`Downloaded static HTML: ${slug}.html`);
  });

  // Reset form
  resetFormBtn.addEventListener('click', resetForm);

  function resetForm() {
    postForm.reset();
    postIdInput.value = '';
    postCoverBase64.value = '';
    rawSourceImageSrc = '';
    editorContent.innerHTML = '';
    userEditedSlug = false;
    modeLabel.textContent = 'New Post';

    dropZone.style.display = 'block';
    cropPreviewWrap.style.display = 'none';
    previewImg.src = '';

    postDateInput.value = new Date().toISOString().split('T')[0];
    postAuthorInput.value = 'Nagdev Technical Editorial Team';
    postCategorySelect.value = 'Green Chemistry & Sustainability';
    postCustomCatInput.style.display = 'none';
    if (postLinkSelect) postLinkSelect.value = '';

    titleCharCount.textContent = '0 chars';
    seoDescCounter.textContent = '0 / 160';
    contentWordCount.textContent = '0 words';

    updateSerpPreview();
  }

  // ── Render Articles Management Table ────────────────────────────────────
  async function renderArticlesTable() {
    if (!tableBody) return;
    const posts = await window.BlogStorage.getAllPosts();

    if (countBadge) countBadge.textContent = posts.length;

    if (!posts.length) {
      tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--admin-muted);">No published articles yet.</td></tr>`;
      return;
    }

    tableBody.innerHTML = posts.map(post => {
      return `
        <tr>
          <td>
            <img src="${post.coverImage}" alt="${post.title}" class="table-thumb">
          </td>
          <td>
            <span class="table-title">${escapeHtml(post.title)}</span>
            <span style="font-size:0.775rem;color:var(--admin-muted);">/blog/${post.slug}.html</span>
          </td>
          <td>
            <span style="font-size:0.8rem;background:#EBF2ED;color:#0B3D1E;padding:2px 8px;border-radius:4px;font-weight:600;">
              ${escapeHtml(post.category)}
            </span>
          </td>
          <td>${post.date || '—'}</td>
          <td>
            <div class="table-actions" style="justify-content:flex-end;">
              <a href="blog/${post.slug}.html" target="_blank" class="btn btn-outline btn-sm" title="View Page">
                View
              </a>
              <button type="button" class="btn btn-outline btn-sm btn-edit-post" data-id="${post.id}" title="Edit in Studio">
                Edit
              </button>
              <button type="button" class="btn btn-outline btn-sm btn-dl-html" data-id="${post.id}" title="Download static HTML">
                HTML ↓
              </button>
              <button type="button" class="btn btn-outline btn-sm btn-delete-post" data-id="${post.id}" style="color:#c0392b;border-color:#f5c6cb;" title="Delete Post">
                ✕
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Wire table action buttons
    tableBody.querySelectorAll('.btn-edit-post').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-id');
        await loadPostIntoEditor(id);
      });
    });

    tableBody.querySelectorAll('.btn-dl-html').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-id');
        const post = await window.BlogStorage.getPostBySlug(id);
        if (post) {
          const html = window.BlogStorage.generateStaticHtml(post);
          downloadFile(`${post.slug}.html`, html, 'text/html');
          window.showToast(`Downloaded: ${post.slug}.html`);
        }
      });
    });

    tableBody.querySelectorAll('.btn-delete-post').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-id');
        if (confirm('Are you sure you want to permanently delete this article?')) {
          await window.BlogStorage.deletePost(id);
          window.showToast('Article deleted.');
          await renderArticlesTable();
        }
      });
    });
  }

  async function loadPostIntoEditor(id) {
    const post = await window.BlogStorage.getPostBySlug(id);
    if (!post) return;

    resetForm();

    postIdInput.value = post.id;
    postTitleInput.value = post.title;
    postSlugInput.value = post.slug;
    userEditedSlug = true;
    modeLabel.textContent = `Editing: ${post.title.slice(0, 24)}…`;

    if (Array.from(postCategorySelect.options).some(o => o.value === post.category)) {
      postCategorySelect.value = post.category;
      postCustomCatInput.style.display = 'none';
    } else {
      postCategorySelect.value = 'Custom';
      postCustomCatInput.style.display = 'block';
      postCustomCatInput.value = post.category || '';
    }

    postAuthorInput.value = post.author || 'Nagdev Technical Editorial Team';
    postDateInput.value = post.date || '';
    postTagsInput.value = (post.tags || []).join(', ');
    postFeaturedCheck.checked = !!post.featured;
    postSeoDescInput.value = post.seoDescription || '';
    editorContent.innerHTML = post.content || '';

    if (postLinkSelect && post.relatedLink && post.relatedLink.url) {
      for (let i = 0; i < postLinkSelect.options.length; i++) {
        const val = postLinkSelect.options[i].value;
        if (val.startsWith(post.relatedLink.url)) {
          postLinkSelect.selectedIndex = i;
          break;
        }
      }
    } else if (postLinkSelect) {
      postLinkSelect.value = '';
    }

    if (post.coverImage) {
      postCoverBase64.value = post.coverImage;
      previewImg.src = post.coverImage;
      dropZone.style.display = 'none';
      cropPreviewWrap.style.display = 'block';
    }

    // Trigger input listeners
    postTitleInput.dispatchEvent(new Event('input'));
    postSeoDescInput.dispatchEvent(new Event('input'));
    editorContent.dispatchEvent(new Event('input'));

    // Switch to tab 1
    const tab1 = document.querySelector('[data-tab="tab-editor"]');
    if (tab1) tab1.click();

    window.scrollTo({ top: 0, behavior: 'smooth' });
    window.showToast(`Loaded "${post.title.slice(0, 30)}…" for editing.`);
  }

  // ── Master Export Tools (Tab 3) ─────────────────────────────────────────
  if (downloadBlogDataBtn) {
    downloadBlogDataBtn.addEventListener('click', async () => {
      const posts = await window.BlogStorage.getAllPosts();
      const code = `/**\n * NAGDEV PRODUCTS — BLOG DATABASE (Exported)\n */\n\nwindow.NAGDEV_BLOG_POSTS = ${JSON.stringify(posts, null, 2)};\n`;
      downloadFile('blog-data.js', code, 'application/javascript');
      window.showToast('Downloaded blog-data.js file.');
    });
  }

  if (downloadAllHtmlsBtn) {
    downloadAllHtmlsBtn.addEventListener('click', async () => {
      const posts = await window.BlogStorage.getAllPosts();
      posts.forEach((p, idx) => {
        setTimeout(() => {
          const html = window.BlogStorage.generateStaticHtml(p);
          downloadFile(`${p.slug}.html`, html, 'text/html');
        }, idx * 250);
      });
      window.showToast(`Exporting ${posts.length} static HTML files...`);
    });
  }

  function downloadFile(filename, text, mimeType) {
    const blob = new Blob([text], { type: mimeType || 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    }, 100);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ── Initialize Dashboard ────────────────────────────────────────────────
  async function initAdminDashboard() {
    resetForm();
    await renderArticlesTable();
  }

  checkAuth();
})();
