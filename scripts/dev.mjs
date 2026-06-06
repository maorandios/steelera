/**
 * Start Steelera dev servers via PowerShell (stable on Windows).
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ps1 = path.join(root, "scripts", "dev.ps1");

const result = spawnSync(
  "powershell",
  ["-ExecutionPolicy", "Bypass", "-File", ps1],
  { cwd: root, stdio: "inherit" },
);

process.exit(result.status ?? 1);
