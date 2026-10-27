import { createClient } from "@libsql/client";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
try {
  process.loadEnvFile(path.join(root, ".env.local"));
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}

const remoteUrl = process.env.TURSO_DATABASE_URL || process.env.DATABASE_URL;
if (process.env.VERCEL && !remoteUrl) {
  throw new Error("Set TURSO_DATABASE_URL before preparing a Vercel database.");
}
if (!remoteUrl) await mkdir(path.join(root, "data"), { recursive: true });

const client = createClient({
  url: remoteUrl || "file:./data/smart_healthcare.sqlite3",
  ...((process.env.TURSO_AUTH_TOKEN && remoteUrl) ? { authToken: process.env.TURSO_AUTH_TOKEN } : {}),
});

const seedOrder = [
  "project", "team_members", "change_requests", "requirements", "wbs", "change_items",
  "activities", "dependencies", "expenditures", "defects", "quality_checks", "risks",
  "milestones", "closure_records",
];

try {
  const schema = await readFile(path.join(root, "database", "schema.sql"), "utf8");
  for (const statement of schema.split(";").map((part) => part.trim()).filter(Boolean)) {
    await client.execute(statement);
  }

  const count = Number((await client.execute("SELECT COUNT(*) AS count FROM project")).rows[0]?.count ?? 0);
  if (count === 0) {
    const seed = JSON.parse(await readFile(path.join(root, "database", "seed-data.json"), "utf8"));
    const statements = [];
    for (const table of seedOrder) {
      for (const row of seed[table] ?? []) {
        const columns = Object.keys(row);
        statements.push({
          sql: `INSERT INTO ${table} (${columns.join(", ")}) VALUES (${columns.map(() => "?").join(", ")})`,
          args: columns.map((column) => row[column] ?? null),
        });
      }
    }
    if (statements.length) await client.batch(statements, "write");
    process.stdout.write("Schema installed and sample project loaded.\n");
  } else {
    process.stdout.write("Schema checked. Existing project data was preserved.\n");
  }
} finally {
  client.close();
}
