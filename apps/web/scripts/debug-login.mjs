import { chromium } from "playwright";

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "pt-BR" });
  const page = await context.newPage();

  page.on("console", msg => console.log("[BROWSER CONSOLE]", msg.type(), msg.text()));
  page.on("response", async res => {
    if (res.url().includes("/auth/")) {
      console.log("[AUTH RESPONSE]", res.status(), res.url());
      try {
        console.log("BODY:", await res.text());
      } catch {}
    }
  });

  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  console.log("Filling login fields...");
  await page.fill("#email", "borgesma63@gmail.com");
  await page.waitForTimeout(500);
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(500);

  console.log("Submitting form...");
  await page.click('button[type="submit"]');

  await page.waitForTimeout(6000);
  console.log("Current URL:", page.url());

  const errEl = await page.$('.text-destructive, [role="alert"], .text-red-500');
  if (errEl) {
    console.log("Page Error Text:", await errEl.textContent());
  }

  await page.screenshot({ path: "/tmp/login-debug.png" });
  await browser.close();
}

main().catch(console.error);
