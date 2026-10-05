// A small, read-only table projection. Content is rendered through Vue text bindings.
const cells = (line) =>
  line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
const divider = (line) =>
  cells(line).length > 1 &&
  cells(line).every((cell) => /^:?-{3,}:?$/.test(cell));

export function proseBlocks(value) {
  const lines = String(value || "").split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  const flush = () => {
    if (paragraph.length)
      blocks.push({ type: "text", text: paragraph.join("\n") });
    paragraph = [];
  };
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    if (
      line.includes("|") &&
      lines[index + 1] &&
      divider(lines[index + 1]) &&
      cells(line).length === cells(lines[index + 1]).length
    ) {
      flush();
      const headers = cells(line);
      const rows = [];
      index++;
      while (
        lines[index + 1]?.includes("|") &&
        cells(lines[index + 1]).length === headers.length
      )
        rows.push(cells(lines[++index]));
      blocks.push({ type: "table", headers, rows });
    } else if (!line.trim()) flush();
    else paragraph.push(line);
  }
  flush();
  return blocks;
}
