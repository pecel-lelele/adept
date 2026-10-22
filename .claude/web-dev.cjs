// Starts the Next.js dev server from src/web (used by .claude/launch.json).
const path = require("path");
const web = path.resolve(__dirname, "..", "src", "web");
process.chdir(web);
process.argv = [process.argv[0], "next", "dev", "--port", process.env.PORT || "3000"];
require(path.join(web, "node_modules", "next", "dist", "bin", "next"));
