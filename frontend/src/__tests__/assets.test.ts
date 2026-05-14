/**
 * Build-time regression test for required map icon assets.
 *
 * The substation symbol layer falls back to a coalesce chain:
 *   ['coalesce', ['image', 'bolt-png'], ['image', 'bolt-icon']]
 *
 * `bolt-icon` is generated programmatically inside VectorOverlay and always
 * available. `bolt-png` is loaded async from `/icons/bolt.png` via MapLibre's
 * loadImage. If the PNG goes missing (e.g. accidental `git rm`, build script
 * misconfiguration), the fallback handles it visually — but losing the high-
 * resolution PNG silently degrades every substation marker on the map.
 *
 * This test catches an accidental removal at CI / pre-commit time, paired
 * with the #60 store regression tests above to keep the substation layer
 * trustworthy.
 *
 * NOTE: this is a file-existence check, not a content check. We don't care
 * about the PNG's bytes — only that something is shipped at the URL the
 * dashboard tries to fetch.
 */

import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const PUBLIC_DIR = resolve(__dirname, '../../public');

const REQUIRED_ASSETS = [
  // Substation high-res bolt — loaded via /icons/bolt.png in VectorOverlay
  'icons/bolt.png',
];

describe('static map assets', () => {
  for (const relPath of REQUIRED_ASSETS) {
    it(`public/${relPath} exists`, () => {
      const absPath = resolve(PUBLIC_DIR, relPath);
      expect(
        existsSync(absPath),
        `Missing required asset: public/${relPath}\n` +
          `If this was an intentional removal, also remove the bolt-png reference\n` +
          `from frontend/src/components/map/VectorOverlay.tsx (the coalesce expression\n` +
          `in the substation symbol layer) and update this test.`,
      ).toBe(true);
    });
  }
});
