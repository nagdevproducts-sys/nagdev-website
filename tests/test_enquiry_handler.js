// tests/test_enquiry_handler.js - Unit tests for /api/enquiry
const assert = require('assert');
const handler = require('../api/enquiry.js');
const { sanitize, generateRef, isOriginAllowed } = handler._testHelpers;

function createMockReqRes({ method = 'POST', headers = {}, body = {} }) {
  const defaultHeaders = {
    'origin': 'https://www.nagdevproducts.com',
    'x-forwarded-for': '127.0.0.1',
    ...headers
  };

  const req = {
    method,
    headers: defaultHeaders,
    body
  };

  const res = {
    statusCode: 200,
    headers: {},
    bodyData: null,
    setHeader(k, v) {
      this.headers[k.toLowerCase()] = v;
      return this;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(data) {
      this.bodyData = data;
      return this;
    }
  };

  return { req, res };
}

async function runTests() {
  console.log('--- Running /api/enquiry Unit Tests ---');
  let passed = 0;

  // 1. Ref format
  const ref = generateRef();
  assert.match(ref, /^NP-\d{8}-\d{4}$/, 'Ref format must match NP-YYYYMMDD-XXXX');
  console.log('✔ Test 1 Passed: Ref format NP-YYYYMMDD-XXXX');
  passed++;

  // 2. Origin check
  assert.strictEqual(isOriginAllowed('https://www.nagdevproducts.com'), true);
  assert.strictEqual(isOriginAllowed('https://nagdevproducts.com'), true);
  assert.strictEqual(isOriginAllowed('https://nagdev-preview-123.vercel.app'), true);
  assert.strictEqual(isOriginAllowed('http://localhost:3000'), true);
  assert.strictEqual(isOriginAllowed('https://evil-site.com'), false);
  console.log('✔ Test 2 Passed: Origin check whitelist');
  passed++;

  // 3. Method check
  {
    const { req, res } = createMockReqRes({ method: 'GET' });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 405);
    console.log('✔ Test 3 Passed: Rejects GET with 405');
    passed++;
  }

  // 4. Forbidden Origin
  {
    const { req, res } = createMockReqRes({ headers: { origin: 'https://attacker.com' } });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 403);
    console.log('✔ Test 4 Passed: Rejects unauthorized origin with 403');
    passed++;
  }

  // 5. Validation - missing name
  {
    const { req, res } = createMockReqRes({
      body: {
        email: 'test@example.com',
        enquiry_type: 'Quote',
        message: 'Hello'
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 400);
    console.log('✔ Test 5 Passed: Rejects missing name with 400');
    passed++;
  }

  // 6. Validation - invalid email
  {
    const { req, res } = createMockReqRes({
      body: {
        name: 'John Doe',
        email: 'not-an-email',
        enquiry_type: 'Quote',
        message: 'Hello'
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 400);
    console.log('✔ Test 6 Passed: Rejects invalid email with 400');
    passed++;
  }

  // 7. Spam protection: Honeypot
  {
    const { req, res } = createMockReqRes({
      body: {
        name: 'Spam Bot',
        email: 'bot@spam.com',
        enquiry_type: 'Quote',
        message: 'Buy cheap watches',
        _honey: 'http://spamlink.com'
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.bodyData.ref, 'SPAM-DROP');
    console.log('✔ Test 7 Passed: Honeypot silently drops spam with 200');
    passed++;
  }

  // 8. Spam protection: Timing (< 3 seconds)
  {
    const { req, res } = createMockReqRes({
      body: {
        name: 'Fast Bot',
        email: 'fast@bot.com',
        enquiry_type: 'Quote',
        message: 'Too fast',
        _timestamp: Date.now() - 500 // filled in 500ms
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.bodyData.ref, 'SPAM-DROP');
    console.log('✔ Test 8 Passed: Sub-3-second submissions dropped');
    passed++;
  }

  // 9. Spam protection: > 5 URLs in message
  {
    const { req, res } = createMockReqRes({
      body: {
        name: 'Link Spammer',
        email: 'spammer@links.com',
        enquiry_type: 'Quote',
        message: 'Check http://link1.com http://link2.com http://link3.com http://link4.com http://link5.com http://link6.com'
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 400);
    assert.match(res.bodyData.error, /excessive links/i);
    console.log('✔ Test 9 Passed: Rejects messages with >5 links');
    passed++;
  }

  // 10. Health check header
  {
    process.env.HEALTH_CHECK_SECRET = 'super-secret-token-123';
    const { req, res } = createMockReqRes({
      headers: {
        'x-health-check': 'super-secret-token-123'
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.bodyData.health, 'pass');
    console.log('✔ Test 10 Passed: Synthetic health check returns 200 pass');
    passed++;
  }

  // 11. Rate limiting (5 per 10 min window)
  {
    const testIp = '198.51.100.42';
    for (let i = 0; i < 5; i++) {
      const { req, res } = createMockReqRes({
        headers: { 'x-forwarded-for': testIp },
        body: {
          name: `User ${i}`,
          email: `user${i}@example.com`,
          enquiry_type: 'Quote',
          message: 'Hello'
        }
      });
      await handler(req, res);
      // Status will be 400 or 502 (no backend configured), but not 429
      assert.notStrictEqual(res.statusCode, 429);
    }
    // 6th request from same IP must be 429
    const { req, res } = createMockReqRes({
      headers: { 'x-forwarded-for': testIp },
      body: {
        name: 'User 6',
        email: 'user6@example.com',
        enquiry_type: 'Quote',
        message: 'Hello'
      }
    });
    await handler(req, res);
    assert.strictEqual(res.statusCode, 429);
    assert.match(res.bodyData.error, /rate limit/i);
    console.log('✔ Test 11 Passed: Rate limiting triggers 429 on 6th request');
    passed++;
  }

  console.log(`\nAll ${passed} /api/enquiry unit tests passed cleanly!`);
}

runTests().catch(err => {
  console.error('Test failure:', err);
  process.exit(1);
});
