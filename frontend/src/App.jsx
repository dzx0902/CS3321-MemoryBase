export default function App() {
  return (
    <main
      style={{
        maxWidth: "960px",
        margin: "0 auto",
        padding: "48px 24px",
        fontFamily: "system-ui, sans-serif",
        lineHeight: 1.6,
      }}
    >
      <h1>MemoryBase</h1>
      <p>面向 AI Agent 协作研发的文件—数据库双态长期记忆系统。</p>
      <ul>
        <li>SourceDocument / SourceChunk</li>
        <li>MemoryItem / MemoryEvidence</li>
        <li>MemoryRevision / AuditLog</li>
        <li>RecallLog / AccessPolicy / WikiPage</li>
      </ul>
    </main>
  );
}
