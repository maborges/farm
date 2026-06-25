const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  try {
    await page.goto('http://localhost:3002/pin', { waitUntil: 'networkidle0' });
    console.log('Loaded /pin');
    
    // Attempt to enter pin or just navigate to /home
    await page.goto('http://localhost:3002/home', { waitUntil: 'networkidle0' });
    console.log('Loaded /home');
    
    const content = await page.content();
    if (content.includes('Algo deu errado')) {
      console.log('Found ErrorBoundary fallback!');
    }
    
  } catch (err) {
    console.error('SCRIPT ERROR:', err);
  }
  
  await browser.close();
})();
