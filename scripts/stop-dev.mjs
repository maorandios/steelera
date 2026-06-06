/** Stop Steelera dev servers (ports 3000 + 8000). */
import { execSync } from "node:child_process";

const ports = [3000, 8000];

if (process.platform === "win32") {
  for (const port of ports) {
    try {
      const out = execSync(`netstat -ano | findstr ":${port}" | findstr LISTENING`, {
        encoding: "utf8",
      });
      const pids = [
        ...new Set(
          out
            .split(/\r?\n/)
            .map((line) => line.trim().split(/\s+/).pop())
            .filter((pid) => pid && /^\d+$/.test(pid)),
        ),
      ];
      for (const pid of pids) {
        execSync(`taskkill /F /PID ${pid}`, { stdio: "ignore" });
        console.log(`Stopped PID ${pid} (port ${port})`);
      }
    } catch {
      // Nothing listening on this port.
    }
  }
} else {
  for (const port of ports) {
    try {
      execSync(`lsof -ti :${port} | xargs kill -9`, { stdio: "ignore", shell: true });
      console.log(`Stopped port ${port}`);
    } catch {
      // Nothing listening.
    }
  }
}

console.log("Dev servers stopped.");
