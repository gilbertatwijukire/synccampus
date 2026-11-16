import { cp, mkdir, readdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(root, "dist");
const apiBase = (process.env.SAAGI_API_BASE || "").trim().replace(/\/$/, "");

if (apiBase && !/^https:\/\//i.test(apiBase)) {
  throw new Error("SAAGI_API_BASE must be an HTTPS URL, such as https://your-api.onrender.com");
}

await mkdir(output, { recursive: true });
for (const entry of await readdir(root, { withFileTypes: true })) {
  if (entry.name === "dist") continue;
  await cp(path.join(root, entry.name), path.join(output, entry.name), { recursive: true });
}
await writeFile(path.join(output, "config.js"), `window.SAAGI_API_BASE = ${JSON.stringify(apiBase)};\n`);
console.log(`Built static frontend in ${output}; API base: ${apiBase || "same origin"}`);
