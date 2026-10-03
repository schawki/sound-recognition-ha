// Bundles src/panel.ts into one file that Home Assistant loads (committed, because HACS does not run builds).
import { build } from "esbuild";

const out = "../custom_components/sound_recognition/frontend/sound-recognition-panel.js";
await build({
  entryPoints: ["src/panel.ts"], bundle: true, format: "esm", target: "es2022", minify: true, outfile: out,
  legalComments: "none", logLevel: "info",
  tsconfigRaw: { compilerOptions: { experimentalDecorators: true, useDefineForClassFields: false } },
});
