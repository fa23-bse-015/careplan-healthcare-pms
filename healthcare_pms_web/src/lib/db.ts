import { createClient, type Client, type InStatement } from "@libsql/client";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import seedData from "../../database/seed-data.json";

type SeedRow = Record<string, string | number | null>;
type SeedTable = Record<string, SeedRow[]>;

const seedOrder = ["project", "team_members", "change_requests", "requirements", "wbs", "change_items", "activities", "dependencies", "expenditures", "defects", "quality_checks", "risks", "milestones", "closure_records"];
const bundledSeed = seedData as SeedTable;
let clientPromise: Promise<Client> | undefined;

function createDatabaseClient() {
  const remoteUrl = process.env.TURSO_DATABASE_URL || process.env.DATABASE_URL;
  if (process.env.VERCEL && !remoteUrl) {
    throw new Error("Attach a persistent Turso database to this Vercel project and set TURSO_DATABASE_URL.");
  }
  const url = remoteUrl || "file:./data/smart_healthcare.sqlite3";
  const authToken = process.env.TURSO_AUTH_TOKEN || undefined;
  return createClient({ url, ...(authToken ? { authToken } : {}) });
}

async function initialize(client: Client) {
  const schema = await readFile(path.resolve(process.cwd(), "database/schema.sql"), "utf8");
  for (const statement of schema.split(";").map((part) => part.trim()).filter(Boolean)) {
    await client.execute(statement);
  }
  const countResult = await client.execute("SELECT COUNT(*) AS count FROM project");
  if (Number(countResult.rows[0]?.count ?? 0) !== 0) return;

  const inserts: InStatement[] = [];
  for (const table of seedOrder) {
    for (const row of bundledSeed[table] ?? []) {
      const columns = Object.keys(row);
      const placeholders = columns.map(() => "?").join(", ");
      inserts.push({
        sql: `INSERT INTO ${table} (${columns.join(", ")}) VALUES (${placeholders})`,
        args: columns.map((column) => row[column] ?? null),
      });
    }
  }
  if (inserts.length) await client.batch(inserts, "write");
}

export async function getDb() {
  if (!clientPromise) {
    clientPromise = (async () => {
      const isRemote = Boolean(process.env.TURSO_DATABASE_URL || process.env.DATABASE_URL);
      if (!isRemote) await mkdir(path.resolve(process.cwd(), "data"), { recursive: true });
      const client = createDatabaseClient();
      try {
        await initialize(client);
        return client;
      } catch (error) {
        client.close();
        throw error;
      }
    })().catch((error) => {
      clientPromise = undefined;
      throw error;
    });
  }
  return clientPromise;
}

type Executor = Pick<Client, "execute">;

export async function queryRows<T extends Record<string, unknown>>(client: Executor, sql: string, args: unknown[] = []) {
  const result = await client.execute({ sql, args: args as never[] });
  return result.rows.map((row) => Object.fromEntries(Object.entries(row))) as T[];
}

export async function execute(client: Executor, sql: string, args: unknown[] = []) {
  return client.execute({ sql, args: args as never[] });
}
