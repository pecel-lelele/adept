/** Equivalent of the Next.js default 404 page. */
export default function NotFound() {
  return (
    <div style={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center" }}>
        <h1 style={{ margin: "0 20px 0 0", padding: "0 23px 0 0", fontSize: 24, fontWeight: 500, borderRight: "1px solid rgba(0,0,0,.3)", lineHeight: "49px" }}>404</h1>
        <h2 style={{ fontSize: 14, fontWeight: 400, lineHeight: "49px", margin: 0 }}>This page could not be found.</h2>
      </div>
    </div>
  );
}
