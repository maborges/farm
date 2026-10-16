import { chromium } from "playwright";

async function main() {
  console.log("Launching chromium...");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });
  console.log("Chromium launched successfully!");
  const page = await browser.newPage();
  await page.goto("http://localhost:3000/login", { waitUntil: "commit" });
  console.log("Navigated to:", page.url());
  console.log("Title:", await page.title());
  await browser.close();
  console.log("Done!");
}

main().catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
