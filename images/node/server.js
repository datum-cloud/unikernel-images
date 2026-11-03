// Default entrypoint: an HTTP server on port 8080.
// Replace /usr/src/server.js (or override the command) to run your own app.
// Bundle real applications to a single file (e.g. esbuild) instead of
// shipping node_modules; the rootfs is RAM-resident and must stay small.
const http = require("http");

const port = Number(process.env.PORT || 8080);
http
  .createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        service: "node",
        message: "Hello from Node.js on a Datum unikernel",
        node: process.version,
        path: req.url,
      })
    );
  })
  // No host: Node binds :: (dual-stack) when IPv6 is available. Datum compute
  // networks are IPv6-only, so an IPv4-only bind is unreachable.
  .listen(port, () => console.log(`listening on :${port}`));
