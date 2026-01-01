require("dotenv/config");
const { chromium } = require("playwright-core");
const cheerio = require("cheerio");
const axios = require("axios");
const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_CGV;
const CGV_NOW_SHOWING_URL =
  process.env.CGV_NOW_SHOWING_URL ||
  "https://www.cgv.vn/default/movies/now-showing.html";
const CGV_COMING_SOON_URL =
  process.env.CGV_COMING_SOON_URL ||
  "https://www.cgv.vn/default/movies/coming-soon-1.html";
const URLS = {
  "Now Showing": CGV_NOW_SHOWING_URL,
  "Coming Soon": CGV_COMING_SOON_URL,
};
const PAGE_LOAD_TIMEOUT = parseInt(
  process.env.PAGE_LOAD_TIMEOUT_MS || "200000"
);
const SELECTOR_TIMEOUT = parseInt(process.env.SELECTOR_TIMEOUT_MS || "45000");
const RENDER_DELAY = parseInt(process.env.RENDER_DELAY_MS || "5000");
const HTTP_TIMEOUT = parseInt(process.env.HTTP_TIMEOUT_SECONDS || "30");
async function getMovies(url) {
  console.log(`Scraping ${url}`);
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH,
    headless: true,
    args: ["--no-sandbox", "--disable-gpu"],
  });
  const page = await browser.newPage();
  let htmlContent = "";
  try {
    await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: PAGE_LOAD_TIMEOUT,
    });
    await page.waitForSelector(".products-grid .item", {
      timeout: SELECTOR_TIMEOUT,
    });
    await page.waitForTimeout(RENDER_DELAY);
    htmlContent = await page.content();
    console.log(
      `Successfully retrieved content (Length: ${htmlContent.length})`
    );
  } catch (e) {
    console.error(`Playwright error: ${e}`);
  } finally {
    await browser.close();
  } // Parse with Cheerio  const $ = cheerio.load(htmlContent);  const movies = [];  const items = $('.products-grid .item');
  if (items.length === 0) {
    console.warn("No items found.");
    return [];
  }
  items.each((i, item) => {
    const titleElement = $(item).find(".product-name a");
    if (titleElement.length === 0) return;
    const title = titleElement.text().trim();
    const link = titleElement.attr("href");
    let imageUrl = null;
    const imgElement = $(item).find("img");
    if (imgElement.length > 0) {
      imageUrl =
        imgElement.attr("data-original") ||
        imgElement.attr("data-src") ||
        imgElement.attr("src");
      if (imageUrl) {
        imageUrl = imageUrl.replace(/\/resize\/\d+x\d+\//g, "/");
        imageUrl = imageUrl.split("?")[0];
      }
    }
    let releaseDate = "N/A";
    // Find the .cgv-movie-info that contains "Khởi chiếu:"
    $(item)
      .find(".cgv-movie-info")
      .each((_, infoDiv) => {
        const label = $(infoDiv).find(".cgv-info-bold").text();
        if (label.includes("Khởi chiếu")) {
          releaseDate = $(infoDiv).find(".cgv-info-normal").text().trim();
        }
      });
    if (releaseDate === "N/A") {
      const itemText = $(item).text();
      const datePatterns = [
        /Khởi chiếu:\s*([\d\-\/]+)/,
        /(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})/,
        /(\d{1,2}[\-\/]\d{1,2})/,
      ];
      for (const pattern of datePatterns) {
        const match = itemText.match(pattern);
        if (match) {
          releaseDate = match[1];
          break;
        }
      }
    }
    // Normalize date format (convert dashes to slashes)
    releaseDate = releaseDate.replace(/-/g, "/");
    movies.push({ title, link, release_date: releaseDate, image: imageUrl });
  });
  return movies;
}
function formatDate(releaseDate, today) {
  if (releaseDate === "N/A" || !releaseDate.match(/^\d+$/)) {
    return releaseDate;
  }
  const day = parseInt(releaseDate);
  let month = today.getMonth() + 1;
  if (day < today.getDate()) {
    month = month < 12 ? month + 1 : 1;
  }
  return `${day.toString().padStart(2, "0")}/${month
    .toString()
    .padStart(2, "0")}`;
}
async function sendDiscordMessage(sectionName, movies) {
  if (!DISCORD_WEBHOOK_URL) {
    console.warn("DISCORD_WEBHOOK_CGV not set, skipping Discord send.");
    return;
  }
  if (movies.length === 0) return;
  const today = new Date();
  const sectionColor = sectionName.includes("Now") ? 0x00d166 : 0xffa500;
  const headerEmbed = {
    title: ` ${sectionName}`,
    color: sectionColor,
    description: `${movies.length} movies`,
  };
  await axios.post(
    DISCORD_WEBHOOK_URL,
    { embeds: [headerEmbed] },
    { timeout: HTTP_TIMEOUT * 1000 }
  );
  const embeds = movies.map((movie) => {
    let formattedDate = formatDate(movie.release_date, today);
    const embed = { title: movie.title, url: movie.link, color: sectionColor };
    if (formattedDate !== "N/A") {
      embed.footer = { text: ` ${formattedDate}` };
    }
    if (movie.image) {
      embed.thumbnail = { url: movie.image };
    }
    return embed;
  });
  for (let i = 0; i < embeds.length; i += 10) {
    const batch = embeds.slice(i, i + 10);
    await axios.post(
      DISCORD_WEBHOOK_URL,
      { embeds: batch },
      { timeout: HTTP_TIMEOUT * 1000 }
    );
  }
}
async function main() {
  for (const [name, url] of Object.entries(URLS)) {
    console.log(`Scraping ${name}...`);
    try {
      const movies = await getMovies(url);
      console.log(`Found ${movies.length} movies.`);
      await sendDiscordMessage(name, movies);
    } catch (e) {
      console.error(`Error scraping ${name}: ${e.message}`);
    }
  }
}
main().catch(console.error);
