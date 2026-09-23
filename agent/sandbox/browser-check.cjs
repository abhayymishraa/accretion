const { chromium } = require('/opt/webbuilder-checks/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const errors = [];
  const pages = [];
  const inspectAt = process.argv.indexOf('--inspect');
  const inspecting = inspectAt !== -1;
  const requestedViewport = process.argv[inspectAt + 1];
  const path = inspecting ? process.argv[inspectAt + 2] || '/' : '/';
  const screenshotArg = inspecting ? process.argv[inspectAt + 3] : undefined;
  const screenshotPath = screenshotArg && !screenshotArg.startsWith('--') ? screenshotArg : undefined;
  const checksAt = process.argv.indexOf('--checks');
  const checks = checksAt === -1 ? {} : JSON.parse(process.argv[checksAt + 1]);
  const origin = 'http://127.0.0.1:5173';
  const addError = message => {
    if (errors.length < 10) errors.push(String(message).slice(0, 500));
  };
  try {
    if (process.argv.includes('--preflight')) {
      console.log(JSON.stringify({ ok: true, checks: ['browser tooling'] }));
      return;
    }
    const viewports = { desktop: { width: 1280, height: 800 }, mobile: { width: 390, height: 844 } };
    for (const [name, viewport] of Object.entries(viewports)) {
      if (inspecting && name !== requestedViewport) continue;
      const plan = checks[name];
      const context = await browser.newContext({ viewport, deviceScaleFactor: 1,
        serviceWorkers: 'block' });
      const page = await context.newPage();
      page.setDefaultTimeout(5000);
      if (inspecting || plan) {
        // Keep navigation local, including redirects. Assets can still load from CDNs.
        await context.route('**/*', route => {
          const request = route.request();
          if ((request.isNavigationRequest() && new URL(request.url()).origin !== origin) ||
              (plan && !['GET', 'HEAD', 'OPTIONS'].includes(request.method()))) {
            if (plan) addError('Blocked a network write or external navigation; only local UI flows can be verified');
            return route.abort();
          }
          return route.continue();
        });
      }
      if (plan) {
        // Mock sockets without an upstream connection. Closing them immediately
        // makes Vite's HMR client report a false connection failure.
        await context.routeWebSocket('**/*', socket => socket.onMessage(() => {}));
        context.on('page', popup => {
          addError('Popup actions are not supported by local acceptance checks');
          void popup.close();
        });
        page.on('download', download => {
          addError('Download actions are not supported by local acceptance checks');
          void download.cancel();
        });
      }
      page.on('pageerror', error => addError(error.message));
      page.on('console', message => {
        if (message.type() === 'error') addError(message.text());
      });
      const observation = { viewport: name, width: viewport.width, height: viewport.height };
      // Closing the context cancels a hung navigation/action, not just its caller.
      const deadline = setTimeout(() => {
        addError(name + ' browser deadline exceeded');
        void context.close();
      }, 35000);
      try {
        const url = new URL(plan?.path || path, origin);
        if (url.origin !== origin) throw Error('Only local preview paths are allowed');
        const response = await page.goto(url.href, { waitUntil: 'networkidle', timeout: 20000 });
        if (new URL(page.url()).origin !== url.origin) throw Error('Preview navigated outside the local app');
        observation.http_status = response?.status() ?? null;
        if (!response || !response.ok()) addError('Preview HTTP failure');
        if (await page.locator('vite-error-overlay').count()) addError('Vite error overlay');
        observation.steps = [];
        for (const step of plan?.steps || []) {
          const record = { action: step.action, selector: step.selector, ok: false };
          observation.steps.push(record);
          try {
            const target = page.locator(step.selector);
            switch (step.action) {
              case 'click': await target.click(); break;
              case 'fill': await target.fill(step.value); break;
              case 'check': await target.setChecked(true); break;
              case 'press': await target.press(step.value); break;
              // Assertions pass on any visible match; actions stay strict.
              case 'expect_visible': await target.filter({ visible: true }).first().waitFor({ state: 'visible' }); break;
              case 'expect_hidden': await target.filter({ visible: true }).first().waitFor({ state: 'hidden' }); break;
              case 'expect_text': {
                // innerText, not hasText: textContent reads "a<br>b" as "ab".
                const expected = step.value.replace(/\s+/g, ' ').trim().toLowerCase();
                const until = Date.now() + 5000;
                let seen;
                while (!(seen = await target.filter({ visible: true }).evaluateAll(elements =>
                  elements.map(el => el.innerText.replace(/\s+/g, ' ').trim()))).some(text =>
                  text.toLowerCase().includes(expected))) {
                  if (Date.now() >= until) {
                    throw Error('Expected text not found; visible matches read ' +
                      JSON.stringify(seen.slice(0, 3).map(text => text.slice(0, 120))));
                  }
                  await page.waitForTimeout(100);
                }
                break;
              }
              case 'expect_checked': {
                await target.waitFor({ state: 'visible' });
                const until = Date.now() + 5000;
                while (!await target.isChecked()) {
                  if (Date.now() >= until) throw Error('Expected checked control');
                  await page.waitForTimeout(100);
                }
                break;
              }
              default: throw Error('Unknown acceptance action');
            }
            record.ok = true;
          } catch (error) {
            addError(name + ' step ' + observation.steps.length + ' (' + step.action + '): ' + error.message);
            break;
          }
        }
        if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) {
          addError(name + ' page has horizontal overflow');
        }
        const content = await page.locator('#root').evaluate(el => {
          // Collect visible text with a bounded DOM walk; never send full HTML.
          const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
          let text = '', node, visited = 0;
          while (text.length < 2000 && visited++ < 5000 && (node = walker.nextNode())) {
            const parent = node.parentElement;
            if (!parent || parent.closest('script,style') ||
                !parent.checkVisibility({ checkVisibilityCSS: true, checkOpacity: true })) continue;
            text += ' ' + node.textContent.slice(0, 2000 - text.length);
          }
          return { rendered: el.childElementCount > 0 && el.getBoundingClientRect().height > 0,
            text: text.trim().replace(/\s+/g, ' ').slice(0, 2000) };
        });
        if (!content.rendered) addError('React root did not render');
        if (content.text === 'Ready to build') addError('Preview still shows the untouched starter page');
        if (inspecting) Object.assign(observation, content, { title: (await page.title()).slice(0, 200) });
        if (screenshotPath) {
          // Viewport only: full-page images can grow with arbitrary generated content.
          const image = await page.screenshot({ type: 'jpeg', quality: 60, fullPage: false,
            scale: 'css', animations: 'disabled', caret: 'hide',
            mask: [page.locator('input[type="password"]')] });
          if (image.length > 200000) throw Error('Screenshot exceeds the 200 KB limit');
          require('fs').writeFileSync(screenshotPath, image, { mode: 0o600 });
        }
      } catch (error) {
        addError(error.message);
      } finally {
        clearTimeout(deadline);
        pages.push(observation);
        await context.close();
      }
    }
    if (inspecting && !pages.length) addError('Unknown viewport');
    console.log(JSON.stringify({ ok: errors.length === 0, errors, checked: true, pages,
      ...(!inspecting && { checks: ['desktop render', 'mobile render', 'browser errors', 'horizontal overflow',
        ...(checksAt !== -1 ? ['selected desktop/mobile acceptance sequences'] : [])] }) }));
    process.exitCode = errors.length ? 1 : 0;
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
