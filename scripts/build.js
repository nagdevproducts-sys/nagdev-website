const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const token = process.env.GOOGLE_SITE_VERIFICATION || '';

function getAllHtmlFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    if (file === 'node_modules' || file === '.git' || file === 'scratch' || file === '.vercel') {
      continue;
    }
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      getAllHtmlFiles(fullPath, fileList);
    } else if (file.endsWith('.html')) {
      fileList.push(fullPath);
    }
  }
  return fileList;
}

const htmlFiles = getAllHtmlFiles(ROOT_DIR);
console.log(`Processing ${htmlFiles.length} HTML files for GSC verification tag...`);

for (const filePath of htmlFiles) {
  let content = fs.readFileSync(filePath, 'utf8');
  const metaRegex = /<meta\s+name=["']google-site-verification["']\s+content=["'][^"']*["']\s*\/?>\s*/gi;

  if (token) {
    const metaTag = `<meta name="google-site-verification" content="${token}">\n`;
    if (metaRegex.test(content)) {
      content = content.replace(metaRegex, metaTag);
    } else if (/<head[^>]*>/i.test(content)) {
      content = content.replace(/(<head[^>]*>)/i, `$1\n  ${metaTag.trim()}`);
    }
  } else {
    // If token is empty, remove any existing verification tag
    content = content.replace(metaRegex, '');
  }

  fs.writeFileSync(filePath, content, 'utf8');
}

console.log(token ? `GSC verification tag injected (token length: ${token.length}).` : 'No GOOGLE_SITE_VERIFICATION env var set, cleaned any verification tags.');

// --- UPDATE PRICE VALID UNTIL (Build Date + 365 Days on all 15 priced products) ---
function updatePriceValidUntil() {
  const targetDate = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000);
  const yyyy = targetDate.getUTCFullYear();
  const mm = String(targetDate.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(targetDate.getUTCDate()).padStart(2, '0');
  const validUntilStr = `${yyyy}-${mm}-${dd}`;

  const productsDir = path.join(ROOT_DIR, 'products');
  if (!fs.existsSync(productsDir)) return;
  const files = fs.readdirSync(productsDir);
  let count = 0;
  for (const file of files) {
    if (!file.endsWith('.html')) continue;
    const filePath = path.join(productsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    if (content.includes('"priceValidUntil":')) {
      const updated = content.replace(/"priceValidUntil":\s*"[^"]+"/, `"priceValidUntil": "${validUntilStr}"`);
      if (updated !== content) {
        fs.writeFileSync(filePath, updated, 'utf8');
        count++;
      }
    }
  }
  console.log(`Updated priceValidUntil to ${validUntilStr} in ${count} product files at build.`);
}

updatePriceValidUntil();

// --- SITEMAP 200 & CANONICAL BUILD CHECK ---
function checkSitemapIntegrity() {
  const sitemapPath = path.join(ROOT_DIR, 'sitemap.xml');
  if (!fs.existsSync(sitemapPath)) return;
  const sitemapXml = fs.readFileSync(sitemapPath, 'utf8');
  
  const vercelPath = path.join(ROOT_DIR, 'vercel.json');
  let redirectSources = new Set();
  if (fs.existsSync(vercelPath)) {
    try {
      const v = JSON.parse(fs.readFileSync(vercelPath, 'utf8'));
      for (const r of (v.redirects || [])) {
        if (r.source) redirectSources.add(r.source);
      }
    } catch (e) {}
  }

  const locMatches = [...sitemapXml.matchAll(/<loc>(https:\/\/www\.nagdevproducts\.com[^<]*)<\/loc>/g)];
  console.log(`Checking sitemap integrity for ${locMatches.length} URLs...`);
  
  for (const match of locMatches) {
    const url = match[1];
    const relPath = url.replace('https://www.nagdevproducts.com', '') || '/';
    if (redirectSources.has(relPath)) {
      throw new Error(`[SITEMAP BUILD CHECK FAILED] Sitemap URL redirects in vercel.json: ${url} -> ${relPath}`);
    }
    
    let filePath;
    if (relPath === '/') {
      filePath = path.join(ROOT_DIR, 'index.html');
    } else {
      const clean = relPath.replace(/^\/|\/$/g, '');
      const directHtml = path.join(ROOT_DIR, `${clean}.html`);
      const dirIndexHtml = path.join(ROOT_DIR, clean, 'index.html');
      filePath = fs.existsSync(directHtml) ? directHtml : dirIndexHtml;
    }
    
    if (!fs.existsSync(filePath)) {
      throw new Error(`[SITEMAP BUILD CHECK FAILED] Sitemap URL has no local HTML file: ${url} (looked for ${filePath})`);
    }
    
    const fileHtml = fs.readFileSync(filePath, 'utf8');
    const canMatch = fileHtml.match(/<link\s+[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i) ||
                     fileHtml.match(/<link\s+[^>]*href=["']([^"']+)["'][^>]*rel=["']canonical["'][^>]*>/i);
    if (!canMatch) {
      throw new Error(`[SITEMAP BUILD CHECK FAILED] Missing canonical link in ${filePath} for sitemap URL ${url}`);
    }
    if (canMatch[1].trim() !== url) {
      throw new Error(`[SITEMAP BUILD CHECK FAILED] Canonical mismatch in ${filePath}: sitemap has ${url}, but file has ${canMatch[1].trim()}`);
    }
  }
  console.log(`[PASSED] All ${locMatches.length} sitemap URLs return 200 directly with matching self-canonical.`);
}

checkSitemapIntegrity();


