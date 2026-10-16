import { chromium } from "playwright";

async function main() {
  console.log("Launching chromium...");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: "pt-BR"
  });

  const page = await context.newPage();
  page.on("console", msg => console.log("[BROWSER CONSOLE]", msg.type(), msg.text()));
  page.on("pageerror", err => console.log("[BROWSER ERROR]", err.message));

  console.log("Navigating to login...");
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
  
  // Wait for input to be visible and interactive
  await page.waitForSelector('input[name="email"], #email', { state: "visible" });
  await page.waitForTimeout(1000); // Allow react hydration

  console.log("Filling credentials...");
  await page.fill("#email", "borgesma63@gmail.com");
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(500);

  console.log("Clicking submit...");
  await page.click('button[type="submit"]');

  // Wait for response or navigation
  console.log("Waiting for navigation / auth response...");
  await page.waitForTimeout(5000);

  console.log("Current URL:", page.url());

  // Check if there is an error message on screen
  const errorText = await page.evaluate(() => {
    const alerts = document.querySelectorAll('[role="alert"], .text-destructive, [data-sonner-toast]');
    return Array.from(alerts).map(a => a.textContent?.trim()).filter(Boolean);
  });
  if (errorText.length > 0) {
    console.log("Screen alerts/toasts:", errorText);
  }

  // If redirected to dashboard or select-tenant
  if (page.url().includes("/dashboard") || page.url().includes("/selecionar-tenant")) {
    console.log("SUCCESS! Logged in to:", page.url());
  }

  const screenshotPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/00-navegacao/01-tela-inicial-dashboard.png";
  await page.screenshot({ path: screenshotPath });
  console.log("Screenshot captured at:", screenshotPath);

  await browser.close();
}

main().catch(err => {
  console.error("Script failed:", err);
  process.exit(1);
});
