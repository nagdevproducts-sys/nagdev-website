// /api/enquiry.js - Vercel Serverless Function for Nagdev Website Enquiries
const crypto = require('crypto');
const querystring = require('querystring');

// In-memory rate limiting map: ip -> array of timestamps
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000; // 10 minutes
const MAX_REQUESTS_PER_WINDOW = 5;

// Clean in-memory map periodically
setInterval(() => {
  const now = Date.now();
  for (const [ip, timestamps] of rateLimitMap.entries()) {
    const valid = timestamps.filter(ts => now - ts < RATE_LIMIT_WINDOW_MS);
    if (valid.length === 0) rateLimitMap.delete(ip);
    else rateLimitMap.set(ip, valid);
  }
}, RATE_LIMIT_WINDOW_MS).unref();

function sanitize(str, maxLen = 500) {
  if (typeof str !== 'string') return '';
  return str.replace(/<[^>]*>/g, '').trim().slice(0, maxLen);
}

function generateRef() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const rand = Math.floor(1000 + Math.random() * 9000);
  return `NP-${year}${month}${day}-${rand}`;
}

function getClientIp(req) {
  const xForwardedFor = req.headers['x-forwarded-for'];
  if (xForwardedFor) return xForwardedFor.split(',')[0].trim();
  return req.headers['x-real-ip'] || req.socket?.remoteAddress || '127.0.0.1';
}

function isOriginAllowed(originOrReferer) {
  if (!originOrReferer) return false;
  try {
    const u = new URL(originOrReferer);
    const host = u.hostname.toLowerCase();
    if (host === 'www.nagdevproducts.com' || host === 'nagdevproducts.com') return true;
    if (host.endsWith('.vercel.app')) return true;
    if (host === 'localhost' || host === '127.0.0.1') return true;
    return false;
  } catch {
    return false;
  }
}

// Google Service Account OAuth2 JWT Token generation
async function getGoogleAccessToken(saJsonString) {
  const sa = JSON.parse(saJsonString);
  const now = Math.floor(Date.now() / 1000);
  const header = Buffer.from(JSON.stringify({ alg: 'RS256', typ: 'JWT' })).toString('base64url');
  const claim = Buffer.from(JSON.stringify({
    iss: sa.client_email,
    scope: 'https://www.googleapis.com/auth/spreadsheets',
    aud: 'https://oauth2.googleapis.com/token',
    exp: now + 3600,
    iat: now
  })).toString('base64url');

  const unsignedToken = `${header}.${claim}`;
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(unsignedToken);
  signer.end();
  const signature = signer.sign(sa.private_key, 'base64url');
  const jwt = `${unsignedToken}.${signature}`;

  const tokenResp = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: querystring.stringify({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: jwt
    })
  });

  if (!tokenResp.ok) {
    const errText = await tokenResp.text();
    throw new Error(`Google OAuth error ${tokenResp.status}: ${errText}`);
  }

  const tokenData = await tokenResp.json();
  return tokenData.access_token;
}

// Append row to Google Sheet
async function appendToGoogleSheet(sheetId, saJsonString, rowValues) {
  const accessToken = await getGoogleAccessToken(saJsonString);
  const range = 'A1';
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(range)}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS`;

  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      values: [rowValues]
    })
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Sheets API error ${resp.status}: ${errText}`);
  }
  return await resp.json();
}

// Send Email via Resend
async function sendResendEmail({ apiKey, from, to, replyTo, subject, html }) {
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      from,
      to: Array.isArray(to) ? to : [to],
      reply_to: replyTo,
      subject,
      html
    })
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Resend API error ${resp.status}: ${errText}`);
  }
  return await resp.json();
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'Method Not Allowed' });
  }

  // Health check header bypass
  const healthSecret = process.env.HEALTH_CHECK_SECRET;
  const reqHealthHeader = req.headers['x-health-check'];
  if (healthSecret && reqHealthHeader === healthSecret) {
    return res.status(200).json({ ok: true, health: 'pass' });
  }

  // Origin / Referer validation
  const origin = req.headers.origin || '';
  const referer = req.headers.referer || '';
  if (!isOriginAllowed(origin) && !isOriginAllowed(referer)) {
    return res.status(403).json({ ok: false, error: 'Forbidden origin' });
  }

  // Parse body
  let body = req.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body);
    } catch {
      body = querystring.parse(body);
    }
  }
  body = body || {};

  // Rate Limiting by IP
  const clientIp = getClientIp(req);
  const now = Date.now();
  const timestamps = (rateLimitMap.get(clientIp) || []).filter(ts => now - ts < RATE_LIMIT_WINDOW_MS);
  if (timestamps.length >= MAX_REQUESTS_PER_WINDOW) {
    return res.status(429).json({ ok: false, error: 'Rate limit exceeded. Please try again later.' });
  }
  timestamps.push(now);
  rateLimitMap.set(clientIp, timestamps);

  // Spam Protection: Honeypot field
  if (body._honey && String(body._honey).trim().length > 0) {
    return res.status(200).json({ ok: true, ref: 'SPAM-DROP' });
  }

  // Spam Protection: Minimum fill time (3 seconds)
  if (body._timestamp) {
    const formTs = Number(body._timestamp) || new Date(body._timestamp).getTime();
    if (!isNaN(formTs) && formTs > 0) {
      const elapsed = now - formTs;
      if (elapsed > 0 && elapsed < 3000) {
        return res.status(200).json({ ok: true, ref: 'SPAM-DROP' });
      }
    }
  }

  // Sanitize fields
  const name = sanitize(body.name, 100);
  const company = sanitize(body.company, 100);
  const email = sanitize(body.email, 100);
  const phone = sanitize(body.phone, 50);
  const country = sanitize(body.country, 50);
  const enquiryType = sanitize(body.enquiry_type, 100);
  const product = sanitize(body.product || body.sample_products, 200);
  const quantity = sanitize(body.quantity, 100);
  const packing = sanitize(body.packing, 100);
  const message = sanitize(body.message, 3000);
  const pageUrl = sanitize(body.page_url || referer, 300);
  const utmSource = sanitize(body.utm_source, 100);

  // Validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!name || !email || !emailRegex.test(email) || !enquiryType || (!message && !product)) {
    return res.status(400).json({ ok: false, error: 'Invalid or missing required fields' });
  }

  // Spam Protection: Max 5 URLs in message
  const urlMatches = message.match(/https?:\/\/|www\./gi) || [];
  if (urlMatches.length > 5) {
    return res.status(400).json({ ok: false, error: 'Message contains excessive links' });
  }

  const ref = generateRef();
  const receivedAtIST = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

  // Prepare dual delivery tasks
  const tasks = [];

  // 1. Google Sheets Task
  const sheetId = process.env.ENQUIRY_SHEET_ID;
  const saJson = process.env.GOOGLE_SA_JSON;
  if (sheetId && saJson) {
    const rowValues = [
      receivedAtIST,
      ref,
      enquiryType,
      product || 'N/A',
      name,
      company || 'N/A',
      email,
      phone || 'N/A',
      country || 'N/A',
      quantity || 'N/A',
      packing || 'N/A',
      message || 'N/A',
      pageUrl || 'N/A',
      utmSource || 'N/A',
      'New'
    ];
    tasks.push(
      appendToGoogleSheet(sheetId, saJson, rowValues)
        .then(() => ({ channel: 'sheet', success: true }))
        .catch(err => ({ channel: 'sheet', success: false, error: err.message }))
    );
  } else {
    tasks.push(Promise.resolve({ channel: 'sheet', success: false, skipped: true }));
  }

  // 2. Resend Email Task
  const resendApiKey = process.env.RESEND_API_KEY;
  if (resendApiKey) {
    const fromEmail = process.env.RESEND_FROM || process.env.RESEND_FROM_EMAIL || 'Nagdev Products Website <enquiries@nagdevproducts.com>';
    const emailSubject = `[Website enquiry] ${enquiryType} – ${product || 'General'} – ${company || name} – ${ref}`;
    const emailHtml = `
      <h2>New Website Commercial Enquiry</h2>
      <p><strong>Reference:</strong> ${ref}</p>
      <p><strong>Received (IST):</strong> ${receivedAtIST}</p>
      <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;max-width:650px;">
        <tr><td style="background:#f4f6f2;width:35%;"><strong>Enquiry Type</strong></td><td>${enquiryType}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Product(s)</strong></td><td>${product || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Contact Name</strong></td><td>${name}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Company Name</strong></td><td>${company || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Email Address</strong></td><td><a href="mailto:${email}">${email}</a></td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Phone / WhatsApp</strong></td><td>${phone || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Country / Region</strong></td><td>${country || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Quantity Required</strong></td><td>${quantity || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Packing Preference</strong></td><td>${packing || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Message / Notes</strong></td><td>${message.replace(/\n/g, '<br>') || 'N/A'}</td></tr>
        <tr><td style="background:#f4f6f2;"><strong>Page URL</strong></td><td>${pageUrl || 'N/A'}</td></tr>
      </table>
    `;

    tasks.push(
      sendResendEmail({
        apiKey: resendApiKey,
        from: fromEmail,
        to: 'nagdevproducts@gmail.com',
        replyTo: email,
        subject: emailSubject,
        html: emailHtml
      })
      .then(async () => {
        // Optional Buyer Auto-Acknowledgement
        try {
          await sendResendEmail({
            apiKey: resendApiKey,
            from: fromEmail,
            to: email,
            replyTo: 'nagdevproducts@gmail.com',
            subject: `Enquiry Confirmation [${ref}] – Nagdev Products Private Limited`,
            html: `<p>We received your enquiry ${ref}; our team will respond within 1 working day.</p>`
          });
        } catch (e) {
          console.warn('Auto-ack email failed:', e.message);
        }
        return { channel: 'email', success: true };
      })
      .catch(err => ({ channel: 'email', success: false, error: err.message }))
    );
  } else {
    tasks.push(Promise.resolve({ channel: 'email', success: false, skipped: true }));
  }

  const results = await Promise.all(tasks);
  const sheetResult = results.find(r => r.channel === 'sheet');
  const emailResult = results.find(r => r.channel === 'email');

  const atLeastOneSuccess = (sheetResult && sheetResult.success) || (emailResult && emailResult.success);

  // Log outcome to Vercel logs (zero personal data beyond ref and status)
  console.log(JSON.stringify({
    ref,
    sheet: sheetResult?.success ? 'OK' : (sheetResult?.skipped ? 'SKIPPED' : 'FAIL'),
    email: emailResult?.success ? 'OK' : (emailResult?.skipped ? 'SKIPPED' : 'FAIL')
  }));

  if (atLeastOneSuccess) {
    return res.status(200).json({ ok: true, ref });
  }

  // Step 5: Log error class and ref explicitly for Vercel logs monitoring
  console.error(JSON.stringify({
    level: 'ERROR',
    ref,
    error_class: 'DeliveryFailure',
    sheet_status: sheetResult?.skipped ? 'SKIPPED_UNCONFIGURED' : (sheetResult?.success ? 'OK' : 'FAILED'),
    email_status: emailResult?.skipped ? 'SKIPPED_UNCONFIGURED' : (emailResult?.success ? 'OK' : 'FAILED'),
    sheet_error: sheetResult?.error || null,
    email_error: emailResult?.error || null
  }));

  // If both failed or unconfigured
  return res.status(502).json({ ok: false, error: 'Delivery failed' });
};

// Export helper functions for unit testing
module.exports._testHelpers = {
  sanitize,
  generateRef,
  isOriginAllowed
};
