// Ground truth for rule set A: the OFFICIAL MCP TypeScript SDK's own parser.
// client.listTools() does ListToolsResultSchema.parse(response) -> one bad tool
// fails the whole z.array(ToolSchema) -> the entire server yields zero tools.
import { ListToolsResultSchema, ToolSchema } from '@modelcontextprotocol/sdk/types.js';
import fs from 'node:fs';
const [src, out] = process.argv.slice(2);
const rows = [];
for (const line of fs.readFileSync(src, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const r = JSON.parse(line);
  if (r.status !== 'ok') continue;
  const tools = r.tools || [];
  const whole = ListToolsResultSchema.safeParse({ tools });
  const bad = [];
  for (const t of tools) {
    const p = ToolSchema.safeParse(t);
    if (!p.success) bad.push({ tool: t && t.name, issues: p.error.issues.slice(0, 3).map(i => `${i.path.join('.')}: ${i.message}`) });
  }
  rows.push({ server_name: r.server_name, pkg: r.pkg, repository: r.repository,
    n_tools: tools.length, listTools_throws: !whole.success, bad_tools: bad });
}
fs.writeFileSync(out, rows.map(x => JSON.stringify(x)).join('\n') + '\n');
const n = rows.length, f = rows.filter(x => x.listTools_throws).length;
console.log(`ORACLE A (official MCP TS SDK ListToolsResultSchema): ${f}/${n} = ${(100 * f / n).toFixed(1)}% of servers where client.listTools() THROWS -> whole server unusable`);
