// Run: node tests/community.test.js
// Extracts the label-propagation core from visualization/index.html and checks that two runs on the
// real graph.json give identical community count and membership.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'visualization', 'index.html'), 'utf8');
const m = html.match(/\/\/ BEGIN community-core[^\n]*\n([\s\S]*?)\/\/ END community-core/);
assert(m, 'community-core markers not found in index.html');
const { mulberry32, labelPropagation, COMMUNITY_SEED } =
  new Function(m[1] + '\nreturn { mulberry32, labelPropagation, COMMUNITY_SEED };')();

const graph = JSON.parse(fs.readFileSync(path.join(root, 'visualization', 'graph.json'), 'utf8'));
function adjacencyOf(nodes, links) {
  const adj = new Map(nodes.map(n => [n.id, new Set()]));
  links.forEach(l => { adj.get(l.source).add(l.target); adj.get(l.target).add(l.source); });
  return adj;
}
const ids = graph.nodes.map(n => n.id);
const adj = adjacencyOf(graph.nodes, graph.links);

const run = (order) => labelPropagation(order, adj, mulberry32(COMMUNITY_SEED));
const a = run(ids);
const b = run(ids);
const reversed = run([...ids].reverse()); // input order must not matter either
const count = r => new Set(r.values()).size;
assert.strictEqual(count(a), count(b), 'community count differs between runs');
assert.deepStrictEqual([...a.entries()].sort(), [...b.entries()].sort(), 'membership differs between runs');
assert.deepStrictEqual([...a.entries()].sort(), [...reversed.entries()].sort(), 'membership depends on input order');
assert.strictEqual(a.size, ids.length);

// Link order in graph.json must not matter either (neighbour sets are built in link order).
const shuffledLinks = [...graph.links];
const shuf = mulberry32(7);
for (let i = shuffledLinks.length - 1; i > 0; i--) {
  const j = Math.floor(shuf() * (i + 1));
  [shuffledLinks[i], shuffledLinks[j]] = [shuffledLinks[j], shuffledLinks[i]];
}
const relinked = labelPropagation(ids, adjacencyOf(graph.nodes, shuffledLinks), mulberry32(COMMUNITY_SEED));
assert.deepStrictEqual([...a.entries()].sort(), [...relinked.entries()].sort(), 'membership depends on link order');

// PRNG sanity: same seed, same stream; values in [0, 1)
const r1 = mulberry32(42), r2 = mulberry32(42);
for (let i = 0; i < 100; i++) { const x = r1(); assert.strictEqual(x, r2()); assert(x >= 0 && x < 1); }

console.log(`OK: ${ids.length} nodes, ${count(a)} communities, identical across runs and input orders ` +
  `(one seed; other seeds give other partitions, see CLAUDE.md)`);
